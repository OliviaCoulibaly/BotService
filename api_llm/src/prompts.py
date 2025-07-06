"""Prompts pour l'agent conversationnel Smart Support"""

SYSTEM_PROMPT = """
Vous êtes un assistant virtuel de support client.
- Soyez poli, clair et précis dans vos réponses.
- Répondez aux demandes techniques, de facturation ou d'information.
- En cas de doute, orientez poliment le client vers un agent humain.
"""

CLASSIFICATION_PROMPT = """
Classifiez cette conversation en JSON uniquement, sans texte autour.

Conversation :
{conversation_history}

Format attendu :
{{
    "category": "Problème technique|Demande d'information|Facturation|Support général|Réclamation",
    "urgency": "Faible|Moyen|Urgent",
    "summary": "résumé court",
    "keywords": ["mot1", "mot2"]
}}
"""

EXTRACTION_PROMPT = """
Extrayez les informations client de cette conversation et retournez uniquement un JSON brut.

Conversation :
{conversation_history}

Format JSON attendu :
{{
    "client_name": "nom ou null",
    "email": "email ou null",
    "phone": "tel ou null",
    "order_number": "commande ou null",
    "problem_details": "description du problème",
    "product_service": "nom du produit ou service concerné"
}}
"""
