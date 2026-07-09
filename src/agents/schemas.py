# This file defines the strict data structures the LLMs must output for each node in the triage process.
# The nodes themselves are defined in nodes.py and the schemas are used to validate the LLM output.


from pydantic import BaseModel, Field
from typing import List


class GuardrailOutput(BaseModel):
    """Schema for the Guardrail Node to check for emergencies"""

    is_emergency: bool = Field(
        description = "Set to true ONLY if the user's message indicates a severe, life-threatning medical emergency(like a heart attack or severe bleeding). Otherwise, false."
    )
    is_medical_topic: bool = Field(
        description = "Set to true if the message relates to health, symptoms, or medical concerns in any way. Set to False id the message is completelyunrelated to medical assistance (e.g. general chit-chat, coding questions, random topics)."
    )


class IntakeOutput(BaseModel):
    """Schema for the Intake Node to manage the initial questioning and when to stop asking questions and search the database"""

    reply_to_user: str = Field(
        description = "Your conversational response to the patient."
    )
    is_ready_for_search: bool = Field(
        description="Set to true ONLY if you have gathered enough symptoms, duration, and context to search a medical database. Otherwise, set to false."
    )
    extracted_age: int = Field(default=-1, description="The patient's age in years if they mentioned it in their latest message. Use -1 if not mentioned.")
    extracted_gender: str = Field(default="", description="The patient's gender if they mentioned it in their latest message (e.g. 'male', 'female'). Use empty string if not mentioned.")


class DiagnosisOutput(BaseModel):
    """Schema for the Diagnosis Node to narrow down the diseases"""

    reply_to_user: str = Field(
        description = "Your conversational follow-up question to the patient."
    )
    has_finished: bool = Field(
        description="Set to true ONLY if you are confident you have narrowed the list down to exactly 3 diseases. Otherwise, set to false."
    )
    top_diseases: List[str] = Field(
        description="A list of the 3 final diseases. Leave this list empty if has_finished is false."
    )


class DoctorInquiryOutput(BaseModel):
    """Schema for the Doctor Recommendation Node to provide top-rated doctors or clinics based on the user's location and top 3 diseases"""
    
    wants_doctor: bool = Field(
        description="Set to true if the user replied affirmatively to wanting a doctor recommendation. Set to false if they declined or answered negatively."
    )
    has_new_symptoms: bool = Field(
        description="Set to True if the user mentions brand new medical symptoms."
    )
    wants_to_end: bool = Field(
        description="Set tp True ONLY if the user explicitly declines the doctor recommendation (e.g. 'no', 'not needed', 'I'm okay', 'no thanks' or any negative reply). Set to False if they are asking a follow-up question, still deciding, or haven't addressed this question yet."
    )