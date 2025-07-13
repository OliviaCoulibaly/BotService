"""Configuration centrale du backend Smart Support."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base  # Base = declarative_base() dans models.py

# --------------------------------------------------------------------------- #
# Base de données
# --------------------------------------------------------------------------- #
DEFAULT_SQLITE_PATH = Path(__file__).parent.parent / "smart_support.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

engine = create_engine(
    DATABASE_URL,
    future=True,
    echo=os.getenv("DEBUG_SQL", "false").lower() == "true",
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def create_tables() -> None:
    """Crée toutes les tables SQL (noop si déjà créées)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    """Session DB utilisable avec Depends() dans FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# FastAPI / CORS
# --------------------------------------------------------------------------- #
API_CONFIG = {
    "title": "Smart Support – Backend API",
    "version": "1.0.0",
    "description": "API backend pour le système Smart Support",
}

CORS_CONFIG = {
    "allow_origins": [
        "http://localhost:8501",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
SECRET_KEY = os.getenv("SMART_SUPPORT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
if SECRET_KEY == "CHANGE_ME_IN_PRODUCTION":
    print("[⚠️ AVERTISSEMENT] La clé secrète SMART_SUPPORT_SECRET_KEY n’a pas été définie !")

JWT_CONFIG = {
    "secret_key": SECRET_KEY,
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
}


# --------------------------------------------------------------------------- #
# Service LLM
# --------------------------------------------------------------------------- #
LLM_API_CONFIG = {
    "base_url": os.getenv("LLM_API_URL", "http://localhost:8001"),
    "timeout": 30,
}
