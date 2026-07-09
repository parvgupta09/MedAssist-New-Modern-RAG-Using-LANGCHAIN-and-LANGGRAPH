# This file contains the core nodes of the whole triage process.
# Each node is a function that takes in the current state of the triage session and returns the next action to take, along with any messages to send to the user or any specific prompt to add to the LLM and also binds the strict schemas to the LLMs to ensure the correct structured output.
# The nodes are executed in a loop until the triage session is complete.


import os
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import get_light_llm, get_moderate_llm, get_heavy_llm
from src.agents.state import TriageState
from src.agents.schemas import GuardrailOutput, IntakeOutput, DiagnosisOutput, DoctorInquiryOutput
from src.agents.prompts import(
    INTAKE_NURSE_PROMPT,
    DIFFERENTIAL_DIAGNOSIS_PROMPT,
    FINAL_REPORT_PROMPT,
    SMART_SUMMARY_PROMPT,
    MEDICAL_SAFETY_GUARDRAIL,
    DOCTOR_RECOMMENDATION_PROMPT,
    DOCTOR_ROUTING_PROMPT
)
from src.agents.tools import search_local_doctors

DB_DIR = "chroma_db"
embeddings = HuggingFaceEmbeddings(model_name = "all-MiniLM-L6-v2")
vector_store = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)

light_llm = get_light_llm()
moderate_llm = get_moderate_llm()
heavy_llm = get_heavy_llm()


def guardrail_node(state: TriageState):
    """Checks is the user's message indicates a severe medical emergency. If so, it instructs the user to call emergency services and ends the chat."""

    recent_messages = state["messages"][0:]
    context_text = "\n".join(f"{type(m).__name__}: {m.content}" for m in recent_messages)

    # Bind the schema to force a true/false guardrail output
    structured_llm = light_llm.with_structured_output(GuardrailOutput)

    prompt = f"""Here is the recent conversation:
            {context_text}

            Based on the LATEST message only:
            1. Is it a severe, life-threatening medical emergency (like a heart attack or severe bleeding)?
            2. Is the overall conversation still related to health, symptoms, or medical concerns? (A short reply answering a medical follow-up question, like "no" or "not really", still counts as medical if it responds to the previous medical question shown above.)
    """
    
    response = structured_llm.invoke(prompt)
    
    if response.is_emergency:
        emergency_msg = AIMessage(content="This sounds like a severe medical emergency.Please stop chatting and call 112 or your local emergency number immediately.")
        return {"messages":[emergency_msg], "next_action":"end"}
    
    if not response.is_medical_topic:
        decline_msg = AIMessage(content="I'm a medical triage assistant, so I can only help with health and symptom-related questions. Could you tell me what symptoms you're experiencing?")
        return {"messages":[decline_msg], "next_action":"end"}

    return {"next_action":"continue"}

 
def intake_node(state: TriageState):
    """Asks questions to the user to gather symptoms info before searching the database."""

    patient_info = f"Patient Info: Age: {state.get('user_age', 'Unknown')}, Gender: {state.get('user_gender', 'Unspecified')}"

    system_message = SystemMessage(content=INTAKE_NURSE_PROMPT + '\n' + MEDICAL_SAFETY_GUARDRAIL + '\n\n' + patient_info)
    messages_to_send = [system_message] + state["messages"]

    # Bind the schemas for intake
    structured_llm = moderate_llm.with_structured_output(IntakeOutput)
    response = structured_llm.invoke(messages_to_send)

    # Convert the text into an AIMessage to save it to the chat history.
    ai_message = AIMessage(content=response.reply_to_user)

    update = {"messages":[ai_message]}

    if response.extracted_age > 0:
        update["user_age"] = response.extracted_age
    if response.extracted_gender:
        update["user_gender"] = response.extracted_gender

    update["next_action"] = "retrieve" if response.is_ready_for_search else "ask_more"
    
    return update


def retrieve_node(state: TriageState):
    """Semantic searches the vector databases for top 10 matching diseases based on the user symptoms."""

    user_symptoms = " ".join(m.content for m in state['messages'] if isinstance(m, HumanMessage))

    results = vector_store.similarity_search(user_symptoms, k=8)

    retrieved_diseases = [doc.metadata.get("disease","Unknown") for doc in results]

    disease_details = {doc.metadata.get("disease","Unknown"): doc.page_content for doc in results}

    db_notice = SystemMessage(content=f"DATABASE RESULTS: The following 10 diseases match the symptoms : {', '.join(retrieved_diseases)}")

    return {
        "retrieved_diseases": retrieved_diseases,
        "retrieve_disease_details": disease_details,
        "messages": [db_notice],
        "next_action": "diagnose"
    }


def diagnosis_node(state: TriageState):
    """This function asks the follow up questions to narrow down the top 10 diseases to top 3 most probable diseases based on the details of the top 10 retrived diseases."""

    patient_info = f"Patient Info: Age: {state.get('user_age', 'Unknown')}, Gender: {state.get('user_gender', 'Unspecified')}"

    retrieved_diseases = state.get("retrieved_diseases", [])
    disease_details = state.get("retrieve_disease_details", {})

    context_parts = []
    for disease in retrieved_diseases:
        detail = disease_details.get(disease, "No additional details available.")
        context_parts.append(f"--- {disease} ---\n{detail}")

    reference_data = "\n\n".join(context_parts)

    system_message = SystemMessage(
        content=DIFFERENTIAL_DIAGNOSIS_PROMPT +
        '\n' + MEDICAL_SAFETY_GUARDRAIL
        + f"\n\nREFERENCE DATA the following is the ONLY source of truth about these 10 candidate diseases."
          f"Base all your reasoning, questions, and final narrowing STRICTLY on this data, not on any outside knowledge:\n\n{reference_data}"
        + '\n\n' + patient_info
    )
    messages_to_send = [system_message] + state["messages"]

    # Bind the schema for the diagnosis
    structured_llm = heavy_llm.with_structured_output(DiagnosisOutput)
    response = structured_llm.invoke(messages_to_send)

    ai_message = AIMessage(content=response.reply_to_user)

    if response.has_finished:
        return {
            "messages" : [ai_message],
            "final_diagnoses" : response.top_diseases,
            "next_action" : "explain"
        }

    return {"messages":[ai_message], "next_action":"ask_more"}


def explaination_node(state: TriageState):
    """Translates the top 3 possible medical diagnosed diseases into the simple english language for the user to read and understand."""

    final_diagnoses = state.get("final_diagnoses", [])
    disease_details = state.get("retrieve_disease_details", {})

    context_parts = []
    for disease in final_diagnoses:
        detail = disease_details.get(disease, "No additional details available.")
        context_parts.append(f"--- {disease} ---\n{detail}")
    reference_data = "\n\n".join(context_parts)

    system_message = SystemMessage(content=FINAL_REPORT_PROMPT + '\n' + MEDICAL_SAFETY_GUARDRAIL + f"\n\nREFERENCE DATA (use this to round your explanation): \n{reference_data}")
    messages_to_send = [system_message] + state["messages"]

    response = moderate_llm.invoke(messages_to_send)

    raw_content = response.content
    if isinstance(raw_content, list):
        raw_content = '\n'.join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in raw_content
        ).strip()

    clean_message = AIMessage(content=raw_content)

    return {"messages":[clean_message], "next_action":"doctor_route"}


def summarize_node(state: TriageState):
    """Updates the user's cronological timeline with the latest chat summary in the background."""

    # Converts the whole text into single text script for the LLM to summarize and update the historical timeline.
    transcript = "\n".join([f"{type(m).__name__}: {m.content}" for m in state["messages"]])

    # Inject the actua time and old history into the prompt
    formatted_prompt = SMART_SUMMARY_PROMPT.format(
        current_timestamp=state["current_timestamp"],
        historical_summary = state["historical_summary"],
        new_chat_transcript = transcript
    )

    new_summary = moderate_llm.invoke([SystemMessage(content=formatted_prompt)])

    # Overwrite the old summary with this updated summary in the user info database.
    return {"historical_summary": new_summary.content, "next_action": "end"}


def doctor_routing_node(state: TriageState):
    """Checks if the user said yes to the doctor recommendation. If yes, calls the Google API."""
    
    system_message = SystemMessage(content=DOCTOR_ROUTING_PROMPT)
    messages_to_send = [system_message] + state["messages"]

    structured_llm = moderate_llm.with_structured_output(DoctorInquiryOutput)
    decision = structured_llm.invoke(messages_to_send)

    if decision.has_new_symptoms:
        user_text = state["messages"][-1].content
        reply_message = AIMessage(content="I see you are experiencing new symptoms. Let me open a new triage chart for you.")
        return {
            "messages": [reply_message],
            "next_action": "summarize",
            "redirect_to_new_chat": True,
            "forward_message": user_text
        }
    
    if decision.wants_to_end:
        closing_msg = AIMessage(content="Understood. Your final report is ready. Please take care, and don't hesitate to consult a doctor if your symptoms are worsening.")
        return {
            "messages": [closing_msg],
            "next_action": "end",
            "wants_doctor": False
        }

    if decision.wants_doctor:
        location = state.get("user_location", "Unknown Location")
        diagnoses = state.get("final_diagnoses", [])

        api_results = search_local_doctors(diagnoses, location)

        # Use the second prompt here to format the Google Data properly
        sys_msg_format = SystemMessage(content=DOCTOR_RECOMMENDATION_PROMPT + '\n' + MEDICAL_SAFETY_GUARDRAIL)
        data_message = SystemMessage(content=f"GOOGLE API RESULTS: {api_results}")

        format_messages = [sys_msg_format, data_message] + state["messages"]
        response = moderate_llm.invoke(format_messages)

        return {
            "messages": [response],
            "next_action": "summarize",
            "wants_doctor": True,
            "recommended_doctors": api_results
        }

    normal_reply = moderate_llm.invoke(messages_to_send)
    return {"messages": [normal_reply], "next_action": "doctor_route"}