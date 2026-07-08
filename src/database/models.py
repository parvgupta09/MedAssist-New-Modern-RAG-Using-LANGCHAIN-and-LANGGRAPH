# Defines the whole structure of the database and the exact tables, columns and the relationships in our NeonDB database
# This is where we define the models for the users, triage sessions, and generated reports but the rest other tables will be handled automatically by the langgraph-checkpoint-postgres itself

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.database.connection import Base


class User(Base):
    """This create the table users in the NEON database with the following columns:"""

    __tablename__ = "users"

    # UUID are better for security than sequential integer ids
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable = True)

    # This stores the concatenated summary of the past sessions
    medical_summary = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    sessions = relationship("TriageSession", back_populates="user")


class TriageSession(Base):
    """This create the table triage_sessions in the NEON database with the following columns:"""

    __tablename__ = "triage_sessions"

    # This session_id will act as our langgraph thread_id
    session_id = Column(UUID(as_uuid=True), primary_key=True, default = uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    
    retrieved_diseases = Column(JSONB, default= list)
    final_diagnoses = Column(JSONB, default= list)
    next_action = Column(String, default="continue")

    status = Column(String, default="active")
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships to the user and generated report models
    user = relationship("User", back_populates="sessions")
    reports = relationship("GeneratedReport", back_populates="session")
    messages = relationship("ChatMessage", back_populates="session")

class GeneratedReport(Base):
    """This create the table generated_reports in the NEON database with the following columns:"""

    __tablename__ = "generated_reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("triage_sessions.session_id"), nullable=False)

    file_path = Column(String, nullable=False)

    # JSONB is the highly efficent PostgreSQL data type for storing the json data in the database
    top_diagnoses = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to the the TriageSession model
    session = relationship("TriageSession", back_populates="reports")

class ChatMessage(Base):
    """This create the table chat_messages in the NEON database with the following columns:"""

    __tablename__ = "chat_messages"

    message_id = Column(UUID(as_uuid=True), primary_key= True, default = uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("triage_sessions.session_id"), nullable = False)
    
    sender = Column(String, nullable=False)
    content = Column(Text, nullable = False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("TriageSession", back_populates="messages")