from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os
import json
import re
import logging

# Charger les variables d'environnement
load_dotenv()

# Initialisation du client OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("La clé API OpenAI est manquante. Vérifiez le fichier .env.")
client = OpenAI(api_key=api_key)

# Configuration de l'application FastAPI
app = FastAPI(title="SmartSupport LLM Proxy", version="1.0.0")

# Configuration des logs
logging.basicConfig(level=logging.INFO)

# Modèles de requêtes
class ChatReq(BaseModel):
    message: str
    conversation_history: list[dict]

class ClassifyReq(BaseModel):
    conversation_history: list[dict]

@app.post("/chats")
async def chats(req: ChatReq):
    """
    Endpoint pour gérer les conversations avec le chatbot.
    """
    system_prompt = {
        "role": "system",
        "content": (
            "Tu es SmartSupport, un assistant client intelligent, bienveillant et professionnel. "
            "Tu réponds en français de manière claire, utile et concise, même en cas d’erreur. "
            "Tu peux poser des questions pour mieux comprendre les besoins de l’utilisateur."
        )
    }

    messages = [
        system_prompt,
        *[{ "role": m["role"], "content": m["content"] } for m in req.conversation_history],
        { "role": "user", "content": req.message }
    ]

    logging.info(f"Messages envoyés à OpenAI : {messages}")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        logging.info(f"Réponse OpenAI : {response}")
        return {"response": response.choices[0].message.content.strip()}
    except Exception as e:
        logging.error(f"Erreur OpenAI : {str(e)}")
        return {"response": f"Erreur lors de la génération : {str(e)}"}

@app.post("/classify")
async def classify(req: ClassifyReq):
    """
    Endpoint pour classifier une conversation.
    """
    prompt = (
        "Classifie la conversation ci-dessous et renvoie un JSON avec les champs : "
        "category, urgency, summary, keywords[]\n\n"
        + "\n".join(f'{m["role"]}: {m["content"]}' for m in req.conversation_history)
    )

    logging.info(f"Prompt envoyé à OpenAI pour classification : {prompt}")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        logging.info(f"Réponse OpenAI : {response}")

        # Extraire le JSON de la réponse
        content = response.choices[0].message.content
        match = re.search(r"\{.*\}", content, re.S)
        classification = json.loads(match.group(0)) if match else {}
        return {"classification": classification}
    except Exception as e:
        logging.error(f"Erreur OpenAI : {str(e)}")
        return {"classification": {}, "error": f"Erreur lors de la classification : {str(e)}"}
