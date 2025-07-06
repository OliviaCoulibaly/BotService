"""
Dashboard Streamlit pour les agents Smart Support.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import List

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Smart Support – Dashboard", page_icon="📊", layout="wide")

# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def authenticate_admin() -> bool:
    if "admin_token" not in st.session_state:
        st.session_state.admin_token = None

    if st.session_state.admin_token:
        return True

    with st.sidebar:
        st.header("🔐 Connexion Agent")
        with st.form("admin_login"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter"):
                try:
                    resp = requests.post(f"{API_BASE_URL}/auth/login", json={"username": username, "password": password}, timeout=5)
                    if resp.status_code == 200:
                        st.session_state.admin_token = resp.json()["access_token"]
                        st.session_state.admin_username = username
                        st.success("Connexion réussie !")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Identifiants incorrects")
                except requests.RequestException as exc:
                    st.error(f"Erreur de connexion : {exc}")
    return False


def api_get(endpoint: str, token: str, **kwargs) -> requests.Response:  # pragma: no cover
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, **kwargs)


# --------------------------------------------------------------------------- #
# Data loaders
# --------------------------------------------------------------------------- #
def get_classifications(token: str) -> List[dict]:
    try:
        resp = api_get("/classifications", token, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 401:
            st.error("Session expirée")
            st.session_state.admin_token = None
            st.rerun()
    except requests.RequestException as exc:
        st.error(f"Erreur API : {exc}")
    return []


# --------------------------------------------------------------------------- #
# Charts & metrics helpers
# --------------------------------------------------------------------------- #
def apply_period_filter(data: list[dict], period: str) -> list[dict]:
    if period == "Tout" or not data:
        return data
    df = pd.DataFrame(data)
    df["created_at"] = pd.to_datetime(df["created_at"])
    now = datetime.now()
    if period == "Aujourd'hui":
        df = df[df["created_at"].dt.date == now.date()]
    elif period == "7 derniers jours":
        df = df[df["created_at"] >= now - timedelta(days=7)]
    elif period == "30 derniers jours":
        df = df[df["created_at"] >= now - timedelta(days=30)]
    return df.to_dict("records")


def metric_cards(df: pd.DataFrame):
    total = len(df)
    urgent = len(df[df["urgency"] == "Urgent"])
    today = len(df[df["created_at"].dt.date == datetime.now().date()])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total demandes", total, delta=f"+{today} aujourd'hui")
    col2.metric("Urgentes", urgent)
    col3.metric("Catégories", df["category"].nunique())


def pie_categories(df: pd.DataFrame):
    counts = df["category"].value_counts().reset_index(name="count")
    fig = px.pie(counts, names="index", values="count", hole=0.3, title="Répartition par catégorie")
    st.plotly_chart(fig, use_container_width=True)


def bar_urgency(df: pd.DataFrame):
    order = ["Urgent", "Moyen", "Faible"]
    counts = df["urgency"].value_counts().reindex(order).fillna(0).reset_index(name="count")
    fig = px.bar(counts, x="index", y="count", title="Niveau d'urgence", color="index", color_discrete_map={"Urgent": "#FF6B6B", "Moyen": "#FFD93D", "Faible": "#6BCF7F"})
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Demandes")
    st.plotly_chart(fig, use_container_width=True)


def timeline(df: pd.DataFrame):
    df["date"] = df["created_at"].dt.date
    counts = df.groupby("date").size().reset_index(name="count")
    fig = px.line(counts, x="date", y="count", markers=True, title="Demandes par jour")
    st.plotly_chart(fig, use_container_width=True)


def recent_table(df: pd.DataFrame):
    st.subheader("📋 Demandes récentes")
    display_df = df.sort_values("created_at", ascending=False).head(10)
    st.dataframe(display_df[["session_id", "category", "urgency", "created_at"]], use_container_width=True)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    st.title("📊 Smart Support – Dashboard")

    if not authenticate_admin():
        st.info("Connectez‑vous pour accéder au tableau de bord.")
        return

    st.sidebar.write(f"Connecté : **{st.session_state.admin_username}**")
    if st.sidebar.button("🚪 Déconnexion"):
        for key in ("admin_token", "admin_username"):
            st.session_state.pop(key, None)
        st.experimental_rerun()

    period = st.sidebar.selectbox("Période", ["Aujourd'hui", "7 derniers jours", "30 derniers jours", "Tout"])
    if st.sidebar.button("🔄 Actualiser"):
        st.rerun()

    with st.spinner("Chargement…"):
        raw_data = get_classifications(st.session_state.admin_token)

    if not raw_data:
        st.warning("Aucune donnée")
        return

    filtered = apply_period_filter(raw_data, period)
    df = pd.DataFrame(filtered)
    df["created_at"] = pd.to_datetime(df["created_at"])

    metric_cards(df)
    col1, col2 = st.columns(2)
    with col1:
        pie_categories(df)
    with col2:
        bar_urgency(df)

    timeline(df)
    recent_table(df)


if __name__ == "__main__":
    main()
