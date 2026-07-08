# This defines the schema for the data validation and formatting when the data moves between the Frontend API and NeonDB Database

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    """The data validation schema at the time of user is trying to signup or login"""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    age: Optional[int] = None
    gender: Optional[str] = None


class UserResponse(BaseModel):
    """The data validation schema that forces to hide the Password hash and only sends back the safe details to the user's screen."""
    
    user_id: UUID
    username: str
    age: Optional[int]
    gender: Optional[str]
    medical_summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionCreateResponse(BaseModel):
    """The data validation schema when a user clicks "New Chat", the database creates a new row."""
    """This schema takes the session_id and formats it into clean JSON so that React knows the ID of the chat it is currently in."""

    session_id: UUID
    status: str
    start_time: datetime

    model_config = ConfigDict(from_attributes = True)


class ChatMessageRequest(BaseModel):
    """The strict rule for the data validation that says to the frontend "I will not accept the message nless you give me the session ID"""
    """As without that ID, langgraph has no idea which history to look at, and it will not be able to get the previous state of the chat."""

    session_id: UUID
    message: str
    user_location: Optional[str] = "Unknown Location"


class ChatMessageResponse(BaseModel):
    """After langgrpah finishes thinking, it outputs a lot of cmplex python data."""
    """This schema takes only what the user needs to see,i.e., the bot's reply, the top 3 diseases(if found), and a PDF link(if generated) and formats it properly for the React to display."""

    session_id: UUID
    bot_reply: str
    current_diagonses: Optional[List[str]] = None
    report_url: Optional[str] = None
    redirect_to_new_chat: bool = False
    forward_message: Optional[str] = None


class ReportResponse(BaseModel):
    """It simply formats the database record of a saved PDF into JSON so that the frontend can display a download link."""

    report_id: UUID
    session_id: UUID
    file_path: str
    top_diagonses: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SessionListResponse(BaseModel):
    """This schema is used for presenting user his/her previous history of past chats"""
    
    session_id: UUID
    status: str
    start_time: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)