# This file defines the state structure passed between nodes in the Langgraph triage workflow.

from typing import TypedDict, List, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TriageState(TypedDict):
    """This is the central memory state of our AI agent execution loop."""
    """Tracks user input, historical summaries, current time matrices, and classification flags."""

    # add_messages tells Langgraph to append new conversation logs instead of overwriting them
    messages: Annotated[List[BaseMessage], add_messages]

    # User Profile and History
    user_id: str
    user_age: int
    user_gender: str
    historical_summary: str         # Extracted from NeonDB from the start of the session
    current_timestamp: str          # Current system time(e.g., 'July 2026') to manage the 15 day gap check 

    # Internal flow variables
    current_symptoms: List[str]
    retrieved_diseases: List[str]   # The top-10 diseases returned from ChromaDB semantic search
    retrieve_disease_details: dict  # A dictionary mapping each disease to its detailed description from ChromaDB
    final_diagnoses: List[str]      # The top-3 choices determined by the Heavy LLM reasoning

    wants_doctor: bool              # Did the user say in affirmatively to Doctor's recommendations?
    user_location: str           
    recommended_doctors: list       # The final list of local clinics/doctors

    redirect_to_new_chat: bool       # If the user wants to start a new chat, this flag is set to True
    forward_message: str

    # Next action to be taken
    next_action: str                # Used for routing decisions (e.g., 'ask_more', 'retrieve', 'finalize', 'emergency')