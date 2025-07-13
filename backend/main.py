"""Smart Support – Backend API"""

from __future__ import annotations

from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from configs import API_CONFIG, CORS_CONFIG, create_tables, get_db
from src.models import Message, Session as SessionModel, User
from src.schemas import (
    ClassificationResponse,
    DashboardStatsResponse,
    MessageCreate,
    MessageResponse,
    SessionCreate,
    SessionResponse,
    SessionWithMessages,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from src.sessions import SessionManager
from src.utils import (
    create_access_token,
    get_stats_by_category,
    get_stats_by_urgency,
    hash_password,
    verify_password,
    verify_token,
)

# --------------------------------------------------------------------------- #
# Initialisation FastAPI
# --------------------------------------------------------------------------- #
app = FastAPI(**API_CONFIG)
app.add_middleware(CORSMiddleware, **CORS_CONFIG)
security = HTTPBearer()
create_tables()


# --------------------------------------------------------------------------- #
# Auth & sécurité
# --------------------------------------------------------------------------- #
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    user = db.query(User).filter(User.id == token_data.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur non trouvé")
    return user


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà pris")
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = User(
        username=user_data.username.strip(),
        email=user_data.email.strip(),
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
@app.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = SessionManager(db)
    return manager.create_session(current_user.id, session_data)


@app.get("/sessions", response_model=List[SessionResponse])
def list_user_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    manager = SessionManager(db)
    return manager.get_user_sessions(current_user.id)


@app.get("/sessions/{session_id}", response_model=SessionWithMessages)
def retrieve_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    return session


@app.post("/sessions/{session_id}/end")
def end_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = SessionManager(db)
    if not manager.end_session(session_id, current_user.id):
        raise HTTPException(status_code=404, detail="Session non trouvée ou déjà terminée")
    return {"message": "Session terminée"}


@app.post("/sessions/{session_id}/classify")
def classify_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    manager = SessionManager(db)
    classification = manager.classify_session(session_id)
    if not classification:
        raise HTTPException(status_code=500, detail="Erreur de classification")
    return {"message": "Classification effectuée", "classification": classification}


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #
@app.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    session_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    manager = SessionManager(db)
    try:
        return manager.add_message(session_id, message_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def list_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.timestamp)
        .all()
    )


# --------------------------------------------------------------------------- #
# Dashboard / Agents
# --------------------------------------------------------------------------- #
@app.get("/classifications", response_model=List[ClassificationResponse])
def list_classifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_agent:
        raise HTTPException(status_code=403, detail="Accès réservé aux agents")
    manager = SessionManager(db)
    return manager.get_all_classifications()


@app.get("/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_agent:
        raise HTTPException(status_code=403, detail="Accès réservé aux agents")

    manager = SessionManager(db)

    total_sessions = db.query(SessionModel).count()
    active_sessions = manager.get_active_sessions_count()
    total_messages = db.query(Message).count()
    classifications = manager.get_all_classifications()

    return {
        "session_stats": {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_messages": total_messages,
        },
        "category_stats": [
            {"category": cat, "count": cnt}
            for cat, cnt in get_stats_by_category(classifications).items()
        ],
        "urgency_stats": [
            {"urgency": urg, "count": cnt}
            for urg, cnt in get_stats_by_urgency(classifications).items()
        ],
    }


# --------------------------------------------------------------------------- #
# Root – Healthcheck
# --------------------------------------------------------------------------- #
@app.get("/")
def root():
    return {"message": "Smart Support Backend API", "status": "running"}


# --------------------------------------------------------------------------- #
# Dev server
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
