# This is the main API file that handles all the chat realated endpoints in the backend. It is responsible for managing chat sessions, processing user messages, and interacting with the triage graph to generate AI responses.

from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import Depends, HTTPException, APIRouter
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID

from src.database.connection import get_db
from src.database.models import User, TriageSession, GeneratedReport, ChatMessage
from src.database.schemas import (
    ChatMessageRequest, 
    ChatMessageResponse,
    SessionCreateResponse,
    SessionListResponse,
)
from src.agents.graph import build_triage_graph
from src.agents.state import TriageState
from langchain_core.messages import HumanMessage, AIMessage
from src.utils.pdf_generator import create_medical_report

router = APIRouter(prefix="/chat", tags=["Triage Chat"])
app_graph = build_triage_graph()


def _run_graph_on_new_session(user: User, forwarded_message: str, user_location: str, db: Session) -> ChatMessageResponse:
    """Created the brand new session for the user"""

    now = datetime.now(timezone.utc)
    new_session = TriageSession(user_id=user.id, start_time=now, updated_at=now)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    greeting = ChatMessage(
        session_id = new_session.session_id,
        sender = "AI",
        content = "Hello! I am your medical triage assistant. Please describe your symptoms you are experiencing today."

    )
    db.add(greeting)

    user_message = ChatMessage(session_id = new_session.session_id, sender="user", content=forwarded_message)
    db.add(user_message)
    db.commit()

    current_state: TriageState = {
        "messages" : [HumanMessage(content=forwarded_message)],
        "user_id" : str(user.user_id),
        "historical_summary": user.medical_summary or "",
        "current_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "current_symptoms": [],
        "retrieved_diseases": [],
        "final_diagnoses": [],
        "user_age": user.age,
        "user_gender": user.gender or "Unspecified",
        "user_location": user_location or "Unknown Location",
        "recommended_doctors": [],
        "redirect_to_new_chat": False,
        "forward_message": "",
        "next_action": "continue"
    }

    output_state = app_graph.invoke(current_state)
    ai_reply = output_state["messages"][-1].content

    ai_msg_db = ChatMessage(session_id=new_session.session_id, sender="assistant", content=ai_reply)
    db.add(ai_msg_db)

    new_session.retrieved_diseases = output_state.get("retrieved_diseases", [])
    new_session.final_diagnoses = output_state.get("final_diagnoses", [])
    new_session.next_action = output_state.get("next_action", "continue")
    new_session.updated_at = now

    if output_state.get("historical_summary") and output_state["historical_summary"] != user.medical_summary:
        user.medical_summary = output_state["historical_summary"]

    db.commit()

    return ChatMessageResponse(
        session_id = new_session.session_id,
        bot_reply = ai_reply,
        current_diagnoses = output_state.get("final_diagnoses"),
        report_url = None,
        redirect_to_new_chat = True,
        forward_message = forwarded_message
    )


@router.post("/init", response_model=SessionCreateResponse)
def initialize_chat(user_id: UUID, db: Session = Depends(get_db)):
    """Initializes the new chat session for the user."""

    now = datetime.now(timezone.utc)
    new_session = TriageSession(user_id=user_id, start_time=now, updated_at=now)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    greeting = ChatMessage(
        session_id = new_session.session_id,
        sender = "assistant",
        content = "Hello! I am your medical triage assistant. Please describe the symptoms you are experiencing today."
    )
    db.add(greeting)
    db.commit()

    return new_session


@router.get("/sessions/{user_id}", response_model=List[SessionListResponse])
def list_sessions(user_id: UUID, db: Session = Depends(get_db)):
    """Returns all the sessions for a user with the most recent session first."""

    sessions = db.query(TriageSession).filter(
        TriageSession.user_id == user_id
    ).order_by(TriageSession.updated_at.desc()).all()
    return sessions


@router.get("/history/{session_id}")
def get_history(session_id: UUID, db: Session = Depends(get_db)):
    """This returns all the history of the chat for a given session for a particular user."""

    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()

    return [{"sender": m.sender, "content": m.content, "timestamp": m.created_at} for m in messages]


@router.get("/reports/{report_id}")
def get_report(report_id : UUID, db: Session = Depends(get_db)):
    """Fetches the generated PDF report for a given report ID."""

    report = db.query(GeneratedReport).filter(GeneratedReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(report.file_path, media_type='application/pdf', filename=f"triage_report.pdf")


@router.post("/message", response_model=ChatMessageResponse)
def handle_message(payload: ChatMessageRequest, db: Session = Depends(get_db)):
    """Handles the incoming user message, processes it through the triage graph, and returns the AI's response."""

    session = db.query(TriageSession).filter(TriageSession.session_id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user = db.query(User).filter(User.user_id == session.user_id).first()
    now = datetime.now(timezone.utc)
    time_diff = now - session.updated_at.replace(tzinfo=timezone.utc)

    if time_diff > timedelta(hours=24):
        session.status = "expired"
        session.end_time = now
        db.commit()
        return _run_graph_on_new_session(user, payload.message, payload.user_location, db)
    
    user_msg = ChatMessage(session_id = payload.session_id, sender="user", content = payload.message)
    db.add(user_msg)
    db.commit()

    db_messages = db.query(ChatMessage).filter(ChatMessage.session_id == payload.session_id).order_by(ChatMessage.created_at.asc()).all()

    langchian_messages = []
    for m in db_messages:
        if m.sender == "user":
            langchian_messages.append(HumanMessage(content=m.content))
        else:
            langchian_messages.append(AIMessage(content=m.content))

    current_state: TriageState = {
        "messages" : langchian_messages,
        "user_id" : str(user.user_id),
        "historical_summary": user.medical_summary or "",
        "current_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "current_symptoms": [],
        "retrieved_diseases": [],
        "final_diagnoses": [],
        "user_location": payload.user_location or "Unknown Location",
        "user_age": user.age,
        "user_gender": user.gender or "Unspecified",
        "recommended_doctors": [],
        "redirect_to_new_chat": False,
        "forward_message": "",
        "next_action": "continue"
    }

    output_state = app_graph.invoke(current_state)

    if output_state.get("redirect_to_new_chat") and output_state.get("forward_message"):
        session.status = "completed"
        session.end_time = now
        session.updated_at = now
        db.commit()
        return _run_graph_on_new_session(user, output_state["forward_message"], payload.user_location, db)
    
    ai_reply = output_state["messages"][-1].content
    ai_msg_db = ChatMessage(session_id=payload.session_id, sender="assistant", content=ai_reply)
    db.add(ai_msg_db)

    session.updated_at = now
    session.retrieved_diseases = output_state.get("retrieved_diseases", [])
    session.final_diagnoses = output_state.get("final_diagnoses", [])
    session.next_action = output_state.get("next_action", "continue")

    if output_state.get("historical_summary") and output_state["historical_summary"] != user.medical_summary:
        user.medical_summary = output_state["historical_summary"]

    report_url = None
    if output_state.get("next_action") == "end" and output_state.get("final_diagnoses"):
        session.status = "completed"
        session.end_time = now
        pdf_path = create_medical_report(
            user.username,
            output_state["final_diagnoses"],
            output_state.get("historical_summary", ""),
        )
        new_report = GeneratedReport(
            session_id=session.session_id,
            file_path=pdf_path,
            top_diagnoses=output_state["final_diagnoses"]
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        report_url = f"/chat/reports/{new_report.report_id}"
    db.commit()

    return ChatMessageResponse(
        session_id = payload.session_id,
        bot_reply = ai_reply,
        current_diagnoses = output_state.get("final_diagnoses"),
        report_url = report_url,
        redirect_to_new_chat = False,
        forward_message = ""
    )