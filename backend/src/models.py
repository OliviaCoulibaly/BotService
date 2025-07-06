"""SQLAlchemy models for Smart Support"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ---------- Enums ---------- #
class RoleEnum(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


# ---------- Models ---------- #
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_agent = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations
    sessions = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Debug
    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username}>"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), default="Nouvelle conversation")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Relations
    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.timestamp",
    )
    classification = relationship(
        "Classification",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Session {self.id} user={self.user_id}>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(RoleEnum), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations
    session = relationship("Session", back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message {self.id} role={self.role}>"


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    category = Column(String(50), nullable=False)
    urgency = Column(String(20), nullable=False)
    summary = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # JSON type => requêtes faciles si PG/MySQL 8+
    classified_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations
    session = relationship("Session", back_populates="classification")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Classification {self.id} {self.category}/{self.urgency}>"
