# api_llm/src/utils.py

"""Fonctions utilitaires pour l'API LLM"""

import re
import json
from datetime import datetime
from typing import Dict, List

def clean_text(text: str) -> str:
    """Nettoie un texte"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.strip())[:500]

def format_conversation(messages: List[Dict]) -> str:
    """Formate l'historique de conversation"""
    if not messages:
        return "Aucun historique"
    
    return "\n".join([
        f"{msg.get('role', 'user')}: {msg.get('content', '')}"
        for msg in messages
    ])

def extract_keywords(text: str) -> List[str]:
    """Extrait des mots-clés simples"""
    if not text:
        return []
    
    stop_words = {'les', 'des', 'une', 'pour', 'avec', 'dans', 'sur', 'que', 'qui'}
    words = re.findall(r'\b\w{4,}\b', text.lower())
    
    return [w for w in set(words) if w not in stop_words][:10]

def validate_classification(data: Dict) -> Dict:
    """Valide une classification retournée par l'IA"""
    categories = ["Problème technique", "Demande d'information", "Facturation", "Support général", "Réclamation"]
    urgencies = ["Faible", "Moyen", "Urgent"]

    category = data.get("category", "").strip()
    urgency = data.get("urgency", "").strip()

    valid_category = category if category in categories else "Support général"
    valid_urgency = urgency if urgency in urgencies else "Moyen"

    return {
        "category": valid_category,
        "urgency": valid_urgency,
        "summary": clean_text(data.get("summary", "Pas de résumé")),
        "keywords": data.get("keywords", [])[:5]
    }

def safe_json_parse(text: str) -> Dict:
    """Tente de parser du JSON même si la réponse est bruitée"""
    try:
        return json.loads(text)
    except:
        # Tente d'extraire un bloc JSON valide
        match = re.search(r'\{.*?\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {}

def get_timestamp() -> str:
    """Retourne un timestamp ISO"""
    return datetime.now().isoformat()

def conversation_stats(messages: List[Dict]) -> Dict:
    """Retourne des stats simples sur une conversation"""
    if not messages:
        return {"total": 0, "user_msgs": 0, "assistant_msgs": 0, "avg_length": 0}
    
    total = len(messages)
    user_msgs = sum(1 for m in messages if m.get('role') == 'user')
    assistant_msgs = sum(1 for m in messages if m.get('role') == 'assistant')
    avg_length = sum(len(m.get('content', '')) for m in messages) // total if total else 0

    return {
        "total": total,
        "user_msgs": user_msgs,
        "assistant_msgs": assistant_msgs,
        "avg_length": avg_length
    }
