""""Pydantic schemas for Smart Support"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal, Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- User ---------- #
class UserCreate(BaseModel):
    username: Annotated[
        str,
        Field(
            strip_whitespace=True,
            min_length=3,
            max_length=50,
            example="john_doe"
        )
    ]
    email: EmailStr = Field(..., example="john@example.com")
    password: Annotated[
        str,
        Field(min_length=6, max_length=128, example="securePassword123")
    ]

    @field_validator("username", mode="before")
    @classmethod
    def strip_and_validate_username(cls, v: str) -> str:
        return v.strip()


class UserLogin(BaseModel):
    username: str = Field(..., example="john_doe")
    password: str = Field(..., example="securePassword123")


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_agent: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Session ---------- #
class SessionCreate(BaseModel):
    title: Optional[str] = Field(default="Nouvelle conversation", example="Demande de prêt logement")


class SessionResponse(BaseModel):
    id: int
    title: str
    is_active: bool
    created_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------- Message ---------- #
class MessageCreate(BaseModel):
    content: str = Field(..., example="Bonjour, j'aimerais avoir des informations sur un crédit.")
    role: Literal["user", "assistant"] = Field(default="user", example="user")


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    timestamp: datetime

    model_config = {"from_attributes": True}


# ---------- Classification ---------- #
class ClassificationCreate(BaseModel):
    category: str = Field(..., example="Crédit")
    urgency: str = Field(..., example="Haute")
    summary: Optional[str] = Field(default=None, example="Demande urgente de crédit personnel.")
    keywords: Optional[List[str]] = Field(default=None, example=["crédit", "urgent", "prêt"])


class ClassificationResponse(BaseModel):
    id: int
    session_id: int
    category: str
    urgency: str
    summary: Optional[str]
    keywords: Optional[List[str]]
    classified_at: datetime

    model_config = {"from_attributes": True}


# ---------- Nested ---------- #
class SessionWithMessages(SessionResponse):
    messages: List[MessageResponse] = []


class SessionWithClassification(SessionResponse):
    classification: Optional[ClassificationResponse] = None
    messages: List[MessageResponse] = []


# ---------- Auth ---------- #
class Token(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", example="bearer")


# ---------- Stats ---------- #
class SessionStats(BaseModel):
    total_sessions: int
    active_sessions: int
    total_messages: int


class CategoryStats(BaseModel):
    category: str
    count: int


class UrgencyStats(BaseModel):
    urgency: str
    count: int


class DashboardStatsResponse(BaseModel):
    session_stats: SessionStats
    category_stats: List[CategoryStats]
    urgency_stats: List[UrgencyStats]
