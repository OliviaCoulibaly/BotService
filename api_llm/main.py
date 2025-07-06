from fastapi import FastAPI
from pydantic import BaseModel
import openai, os, json, re

# Configuration de la clé API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialisation de l'application FastAPI
app = FastAPI(title="SmartSupport LLM proxy", version="0.1.0")

# Modèle pour les requêtes de chat
class ChatReq(BaseModel):
    message: str
    conversation_history: list[dict]

# Modèle pour les requêtes de classification
class ClassifyReq(BaseModel):
    conversation_history: list[dict]

# Route pour la génération de réponse via LLM
@app.post("/chats")
async def chats(req: ChatReq):
    messages = [
        *[{ "role": m["role"], "content": m["content"] } for m in req.conversation_history],
        { "role": "user", "content": req.message },
    ]
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return { "response": resp.choices[0].message.content.strip() }
    except Exception as e:
        return { "response": f"Erreur OpenAI: {str(e)}" }

# Route pour la classification de session via LLM
@app.post("/classify")
async def classify(req: ClassifyReq):
    prompt = (
        "Classifie la conversation ci-dessous et renvoie un JSON avec les champs : "
        "category, urgency, summary, keywords[]\n\n"
        + "\n".join(f'{m["role"]}: {m["content"]}' for m in req.conversation_history)
    )
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        match = re.search(r"\{.*\}", resp.choices[0].message.content, re.S)
        classification = json.loads(match.group(0)) if match else {}
        return { "classification": classification }
    except Exception as e:
        return { "classification": {}, "error": f"Erreur classification: {str(e)}" }

# Lancement local pour test
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
