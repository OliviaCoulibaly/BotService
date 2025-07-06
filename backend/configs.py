"""Configuration centrale du backend Smart Support."""

from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base  # Base est défini dans backend/src/models.py

# --------------------------------------------------------------------------- #
# Base de données
# --------------------------------------------------------------------------- #
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smart_support.db")

engine = create_engine(
    DATABASE_URL,
    future=True,
    echo=False,  # passe à True si tu veux voir les requêtes SQL
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def create_tables() -> None:
    """Crée toutes les tables (noop si elles existent déjà)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield‑based DB session (FastAPI dépendance)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# FastAPI / CORS
# --------------------------------------------------------------------------- #
API_CONFIG = {
    "title": "Smart Support – Backend API",
    "version": "1.0.0",
    "description": "API backend pour le système Smart Support",
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
JWT_CONFIG = {
    "secret_key": os.getenv("SMART_SUPPORT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION"),
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
}

# --------------------------------------------------------------------------- #
# Service LLM (si tu veux centraliser l’URL ici)
# --------------------------------------------------------------------------- #
LLM_API_CONFIG = {
    "base_url": os.getenv("LLM_API_URL", "http://localhost:8001"),
    "timeout": 30,
}
