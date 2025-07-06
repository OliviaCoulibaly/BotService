"""
Interface Streamlit « chat » pour Smart Support.
– Inscription et authentification JWT
– Création / utilisation d'une session backend
– Envoi des messages au backend et affichage temps réel
"""

from __future__ import annotations

import time
from typing import List, Optional

import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"  # URL du backend FastAPI


# --------------------------------------------------------------------------- #
# Helpers API
# --------------------------------------------------------------------------- #
def api_post(
    endpoint: str,
    token: Optional[str] = None,
    **kwargs,
) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.post(f"{BACKEND_URL}{endpoint}", headers=headers, **kwargs)


def api_get(
    endpoint: str,
    token: Optional[str] = None,
    **kwargs,
) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.get(f"{BACKEND_URL}{endpoint}", headers=headers, **kwargs)


# --------------------------------------------------------------------------- #
# Auth helpers
# --------------------------------------------------------------------------- #
def register_user(username: str, email: str, password: str) -> bool:
    """Retourne True si inscription OK."""
    try:
        resp = api_post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
            timeout=10,
        )
        return resp.status_code == 201
    except requests.RequestException as exc:
        st.error(f"Erreur de connexion au backend : {exc}")
        return False


def verify_login(username: str, password: str) -> Optional[str]:
    """Retourne le token JWT si OK, sinon None."""
    try:
        resp = api_post(
            "/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
        return None
    except requests.RequestException as exc:
        st.error(f"Erreur de connexion au backend : {exc}")
        return None


# --------------------------------------------------------------------------- #
# UI : Page de connexion / inscription
# --------------------------------------------------------------------------- #
def login_page():
    st.set_page_config(
        page_title="Smart Support – Connexion", page_icon="🔐", layout="centered"
    )

    if "show_register" not in st.session_state:
        st.session_state.show_register = False

    # -------- CSS -------- #
    st.markdown(
        """
        <style>
        .main {background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:2rem;}
        .login-card{background:#fff;padding:2rem;border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,0.2);max-width:420px;margin:2rem auto;}
        .title{color:#2c3e50;text-align:center;font-size:2rem;margin-bottom:1rem;}
        .subtitle{color:#7f8c8d;text-align:center;margin-bottom:2rem;}
        .stButton>button{width:100%;background:linear-gradient(90deg,#667eea 0%,#764ba2 100%);color:#fff;border:none;padding:.7rem;border-radius:8px;font-weight:bold;transition:.3s;}
        .stButton>button:hover{transform:translateY(-2px);box-shadow:0 5px 15px rgba(0,0,0,0.3);}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -------- Carte principale -------- #
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<h1 class="title">🔐 Smart Support</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Assistant Client Intelligent</p>', unsafe_allow_html=True
    )

    # -------- Connexion -------- #
    if not st.session_state.show_register:
        with st.form("login_form"):
            username = st.text_input("👤 Nom d'utilisateur")
            password = st.text_input("🔑 Mot de passe", type="password")
            submit_login = st.form_submit_button("🚀 Se connecter")

            if submit_login:
                if not username or not password:
                    st.error("Veuillez remplir tous les champs")
                else:
                    token = verify_login(username, password)
                    if token:
                        st.session_state.authenticated = True
                        st.session_state.token = token
                        st.session_state.username = username
                        st.success("Connexion réussie !")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Identifiants incorrects")

        if st.button("Créer un compte"):
            st.session_state.show_register = True
            st.rerun()

    # -------- Inscription -------- #
    else:
        with st.form("register_form"):
            new_username = st.text_input("👤 Nom d'utilisateur")
            new_email = st.text_input("📧 Email")
            new_password = st.text_input("🔑 Mot de passe", type="password")
            submit_reg = st.form_submit_button("✅ Créer mon compte")

            if submit_reg:
                if not new_username or not new_email or not new_password:
                    st.error("Tous les champs sont obligatoires")
                else:
                    ok = register_user(new_username, new_email, new_password)
                    if ok:
                        st.success(
                            "Compte créé avec succès ! Connectez‑vous avec vos identifiants."
                        )
                        st.session_state.show_register = False
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erreur lors de la création du compte")

        if st.button("⬅️ Retour à la connexion"):
            st.session_state.show_register = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# UI : Interface Chat
# --------------------------------------------------------------------------- #
def new_or_existing_session(token: str) -> int:
    """Retourne l'ID d'une session active (nouvelle ou déjà créée)."""
    if "session_id" in st.session_state:
        return st.session_state.session_id

    resp = api_post(
        "/sessions",
        token=token,
        json={"title": "Nouvelle conversation"},
        timeout=10,
    )
    resp.raise_for_status()
    session_id = resp.json()["id"]
    st.session_state.session_id = session_id
    return session_id


def fetch_messages(token: str, session_id: int) -> List[dict]:
    resp = api_get(f"/sessions/{session_id}/messages", token=token, timeout=10)
    resp.raise_for_status()
    return resp.json()


def send_message_backend(token: str, session_id: int, content: str) -> None:
    api_post(
        "/messages",
        token=token,
        params={"session_id": session_id},
        json={"role": "user", "content": content},
        timeout=30,
    ).raise_for_status()


def chat_interface():
    st.set_page_config(page_title="Smart Support – Chat", page_icon="🤖", layout="wide")

    # -------- CSS -------- #
    st.markdown(
        """
        <style>
        .chat-header{background:linear-gradient(90deg,#667eea 0%,#764ba2 100%);color:#fff;padding:1rem;border-radius:10px;margin-bottom:1rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -------- Sidebar -------- #
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        if st.button("🚪 Se déconnecter"):
            for key in (
                "authenticated",
                "token",
                "username",
                "messages",
                "session_id",
            ):
                st.session_state.pop(key, None)
            st.rerun()

    # -------- Header -------- #
    st.markdown(
        """
        <div class="chat-header">
            <h1>🤖 Smart Support</h1>
            <p>Assistant virtuel pour vos demandes</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    token = st.session_state.token
    session_id = new_or_existing_session(token)

    # -------- Messages -------- #
    if "messages" not in st.session_state:
        st.session_state.messages = fetch_messages(token, session_id)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # -------- Input -------- #
    prompt = st.chat_input("💬 Tapez votre message ici…")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            send_message_backend(token, session_id, prompt)
            time.sleep(1)  # petite attente
            st.session_state.messages = fetch_messages(token, session_id)
            st.rerun()
        except requests.RequestException as exc:
            st.error(f"Erreur : {exc}")


# --------------------------------------------------------------------------- #
# Main dispatcher
# --------------------------------------------------------------------------- #
def main():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        chat_interface()
    else:
        login_page()


if __name__ == "__main__":
    main()
