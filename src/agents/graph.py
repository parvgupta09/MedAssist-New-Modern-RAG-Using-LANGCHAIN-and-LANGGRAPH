# The core scripts that form the graph and the whole workflow of the triage session and decides how the workflow shall proceed based on the user and LLM conversations.

from langgraph.graph import StateGraph, END
from src.agents.state import TriageState
from src.agents.nodes import (
    guardrail_node,
    intake_node,
    retrieve_node,
    diagnosis_node,
    explaination_node,
    summarize_node,
    doctor_routing_node
)

def route_after_guardrail(state: TriageState):
    """It is the master switchboard that decideds the next node to go to based on the current state of the workflow and the LLM outputs."""
    
    # 1. If it is emergency then stop
    if state.get("next_action") == "end":
        return "end"
    
    # 2. If we already have the final diagnosis, it means the explanation node just ran and user is now replying yes or no to the doctor query.
    if state.get("final_diagnoses"):
        return "doctor_route"
    
    # 3. If we already have all the 10 diseases then we are in diagnosis phase and we can go to the diagnosis node.
    if state.get("retrieved_diseases"):
        return "diagnose"
    
    # 4. If we have no retrieved diseases yet, it means we are in intake phase and we need to ask the user more questions to gather symptoms info before searching the database.
    return "intake"


def build_triage_graph():
    """This is the core function that forms and created the whole flow of the graph and decided how the workflow should move based on the user responses and the LLM outputs. 
    It is the main routing function that decides the next node to go to based on the current state of the workflow."""

    # 1. Initialize the graph with the inital triage state.
    workflow = StateGraph(TriageState)

    # 2. Add all the nodes in the graph.
    workflow.add_node("guardrail_node", guardrail_node)
    workflow.add_node("intake_node", intake_node)
    workflow.add_node("retrieve_node", retrieve_node)
    workflow.add_node("diagnosis_node", diagnosis_node)
    workflow.add_node("explaination_node", explaination_node)
    workflow.add_node("doctor_routing_node", doctor_routing_node)
    workflow.add_node("summarize_node", summarize_node)

    # 3. Set the entry point of the graph from where the workflow will start. 
    workflow.set_entry_point("guardrail_node")

    # 4. Here we define the conditional edges that decide the next node to go to based on the current state of the workflow and the LLM outputs.
    workflow.add_conditional_edges(
        "guardrail_node",
        route_after_guardrail,
        {
            "end": END,
            "doctor_route": "doctor_routing_node",
            "diagnose": "diagnosis_node",
            "intake": "intake_node"
        }
    )

    # 5. If intake says retrieve, go to DB, If intake says ask_more then pause and wait for the user.
    workflow.add_conditional_edges(
        "intake_node",
        lambda state: state.get("next_action"),
        {
            "retrieve": "retrieve_node",
            "ask_more": END
        }
    )

    # 6. It adds an edge between the retrieve node and the diagnosis node. 
    workflow.add_edge("retrieve_node", "diagnosis_node")

    # 7. If diagnosis says explain, go to explaination node, If diagnosis says ask_more then pause and wait for the user.
    workflow.add_conditional_edges(
        "diagnosis_node",
        lambda state: state.get("next_action"),
        {
            "explain": "explaination_node",
            "ask_more": END
        }
    )

    # 8. After explaning we must wait for the user's yes or no reply
    workflow.add_edge("explaination_node", END)

    # 9. After the doctor node processes the YES/NO reply, it always flow to the summary node.
    workflow.add_edge("doctor_routing_node", "summarize_node")

    # 10. Summarize is the final step and the last node
    workflow.add_edge("summarize_node", END)

    app = workflow.compile()

    return app