# api_llm/src/chain.py

"""Configuration OpenAI pour Smart Support"""

import os
import json
from typing import Dict, List
from openai import OpenAI
from .prompts import SYSTEM_PROMPT, CLASSIFICATION_PROMPT, EXTRACTION_PROMPT

class SmartSupportChain:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-3.5-turbo"
    
    def _call_api(self, messages: List[Dict], temp: float = 0.7) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=temp
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[ERROR] Appel API échoué: {e}")
            return f"Erreur API: {str(e)}"
    
    def generate_response(self, user_message: str, history: List[Dict] = None) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history[-5:])
        messages.append({"role": "user", "content": user_message})
        return self._call_api(messages)

    def classify_request(self, conversation: List[Dict]) -> Dict:
        conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in conversation])
        prompt = CLASSIFICATION_PROMPT.format(conversation_history=conv_text)

        messages = [
            {"role": "system", "content": "Vous classifiez les demandes clients."},
            {"role": "user", "content": prompt}
        ]

        response = self._call_api(messages, temp=0.3)
        try:
            return json.loads(response)
        except Exception as e:
            print(f"[WARNING] Erreur JSON classification: {e}")
            return {
                "category": "autre",
                "urgency": "moyen", 
                "summary": "Classification automatique",
                "keywords": ["support"]
            }

    def extract_client_info(self, conversation: List[Dict]) -> Dict:
        conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in conversation])
        prompt = EXTRACTION_PROMPT.format(conversation_history=conv_text)

        messages = [
            {"role": "system", "content": "Vous extrayez les informations clients."},
            {"role": "user", "content": prompt}
        ]

        response = self._call_api(messages, temp=0.2)
        try:
            return json.loads(response)
        except Exception as e:
            print(f"[WARNING] Erreur JSON extraction: {e}")
            return {}
