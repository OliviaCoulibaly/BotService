# sessions.py corrigé – Appels au micro-service LLM sur http://localhost:8001

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from .models import (
    Session as SessionModel,
    Message,
    Classification,
    RoleEnum,
)
from .schemas import (
    SessionCreate,
    MessageCreate,
)
from .utils import generate_session_title, keywords_to_json

# URL du micro-service LLM
LLM_API_URL = "http://localhost:8001"

class SessionManager:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: int, session_data: SessionCreate) -> SessionModel:
        new_session = SessionModel(user_id=user_id, title=session_data.title)
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        return new_session

    def get_user_sessions(self, user_id: int) -> List[SessionModel]:
        return (
            self.db.query(SessionModel)
            .filter(SessionModel.user_id == user_id)
            .order_by(SessionModel.created_at.desc())
            .all()
        )

    def get_session_with_messages(self, session_id: int, user_id: int) -> Optional[SessionModel]:
        return (
            self.db.query(SessionModel)
            .filter(SessionModel.id == session_id, SessionModel.user_id == user_id)
            .first()
        )

    def add_message(self, session_id: int, message_data: MessageCreate) -> Message:
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session or not session.is_active:
            raise ValueError("Session non trouvée ou inactive")

        user_message = Message(
            session_id=session_id,
            role=RoleEnum(message_data.role),
            content=message_data.content,
        )
        self.db.add(user_message)

        if message_data.role == "user":
            history = self._get_conversation_history(session_id)
            assistant_content = self._call_llm_api(message_data.content, history)
            assistant_message = Message(
                session_id=session_id,
                role=RoleEnum.ASSISTANT,
                content=assistant_content,
            )
            self.db.add(assistant_message)

            if not session.title or session.title == "Nouvelle conversation":
                session.title = generate_session_title(message_data.content)

        self.db.commit()
        self.db.refresh(user_message)
        return user_message

    def end_session(self, session_id: int, user_id: int) -> bool:
        session = (
            self.db.query(SessionModel)
            .filter(SessionModel.id == session_id, SessionModel.user_id == user_id)
            .first()
        )
        if not session:
            return False

        session.is_active = False
        session.ended_at = datetime.now(timezone.utc)
        self._classify_session(session_id)
        self.db.commit()
        return True

    def classify_session(self, session_id: int) -> Optional[Classification]:
        return self._classify_session(session_id)

    def get_all_classifications(self) -> List[Dict]:
        classifications = self.db.query(Classification).all()
        return [
            {
                "id": c.id,
                "session_id": c.session_id,
                "category": c.category,
                "urgency": c.urgency,
                "summary": c.summary,
                "keywords": c.keywords,
                "classified_at": c.classified_at,
                "created_at": c.session.created_at,
            }
            for c in classifications
        ]

    def get_active_sessions_count(self) -> int:
        return self.db.query(SessionModel).filter(SessionModel.is_active.is_(True)).count()

    def search_sessions(self, user_id: int, query: str) -> List[SessionModel]:
        return (
            self.db.query(SessionModel)
            .join(Message)
            .filter(SessionModel.user_id == user_id, Message.content.ilike(f"%{query}%"))
            .distinct()
            .all()
        )

    def _get_conversation_history(self, session_id: int) -> List[Dict]:
        messages = (
            self.db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.timestamp)
            .all()
        )
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ]

    def _call_llm_api(self, prompt: str, history: List[Dict]) -> str:
        try:
            resp = requests.post(
                f"{LLM_API_URL}/chats",
                json={"message": prompt, "conversation_history": history},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
            return "Je rencontre une difficulté technique. Pouvez-vous reformuler ?"
        except Exception as exc:
            return f"Erreur de connexion au service IA : {exc}"

    def _classify_session(self, session_id: int) -> Optional[Classification]:
        history = self._get_conversation_history(session_id)
        if not history:
            return None

        try:
            resp = requests.post(
                f"{LLM_API_URL}/classify",
                json={"conversation_history": history},
                timeout=30,
            )
            if resp.status_code != 200:
                return None

            data = resp.json().get("classification", {})
            classification = Classification(
                session_id=session_id,
                category=data.get("category", "Support général"),
                urgency=data.get("urgency", "Moyen"),
                summary=data.get("summary", ""),
                keywords=keywords_to_json(data.get("keywords", [])),
            )
            self.db.add(classification)
            self.db.commit()
            self.db.refresh(classification)
            return classification
        except Exception as exc:
            print(f"[Classification] {exc}")
            return None
