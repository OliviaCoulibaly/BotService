"""Utility functions for Smart Support backend"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .models import User

# ---------- Security settings ---------- #
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SMART_SUPPORT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ---------- Password helpers ---------- #
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------- JWT helpers ---------- #
def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------- Misc helpers ---------- #
def keywords_to_json(keywords: Union[List[str], None]) -> str:
    """Convertit une liste de mots-clés en JSON (texte)."""
    return json.dumps(keywords or [])


def json_to_keywords(json_str: Union[str, None]) -> List[str]:
    try:
        return json.loads(json_str or "[]")
    except json.JSONDecodeError:
        return []


def generate_session_title(first_message: str) -> str:
    if not first_message:
        return "Nouvelle conversation"
    words = first_message.strip().split()[:8]
    title = " ".join(words)
    return (title[:50] + "...") if len(title) > 50 else title


def format_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M")


def calculate_response_time(messages: List[Dict]) -> float:
    """
    Calcule le temps moyen de réponse (en minutes) de l'assistant
    dans un historique de conversation.
    """
    if len(messages) < 2:
        return 0.0
    response_times = []
    for i in range(1, len(messages)):
        if (
            messages[i - 1].get("role") == "user"
            and messages[i].get("role") == "assistant"
        ):
            try:
                t1 = datetime.fromisoformat(messages[i - 1]["timestamp"])
                t2 = datetime.fromisoformat(messages[i]["timestamp"])
                response_times.append((t2 - t1).total_seconds() / 60)
            except Exception:
                continue
    return sum(response_times) / len(response_times) if response_times else 0.0


def get_stats_by_category(classifications: List[Dict]) -> Dict[str, int]:
    stats: Dict[str, int] = {}
    for c in classifications:
        cat = c.get("category", "Non classifié")
        stats[cat] = stats.get(cat, 0) + 1
    return stats


def get_stats_by_urgency(classifications: List[Dict]) -> Dict[str, int]:
    stats: Dict[str, int] = {}
    for c in classifications:
        urg = c.get("urgency", "Non défini")
        stats[urg] = stats.get(urg, 0) + 1
    return stats


def is_agent(token: str, db: Session) -> bool:
    """
    Vérifie si le token appartient à un utilisateur agent.
    Retourne False si invalide ou utilisateur non trouvé.
    """
    data = verify_token(token)
    if not data:
        return False
    user_id = data.get("user_id")
    if not user_id:
        return False
    user = db.query(User).filter(User.id == user_id).first()
    return bool(user and user.is_agent)
