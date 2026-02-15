import os
from openai import OpenAI
from sqlalchemy.orm import Session
from .rag import rag_search

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Tu es l'assistant virtuel de KTIOS Lounge, un bar et lounge africain à Québec.

Tu es professionnel, chaleureux et serviable. Tu réponds aux questions sur les horaires, le menu, les réservations, l'ambiance et le contact.

Si tu ne connais pas une information, tu l'admets honnêtement et tu suggères de contacter le restaurant.

Reste concis (2-3 phrases maximum) sauf si on te demande plus de détails."""

def agent_reply(db: Session, tenant_id: str, user_message: str) -> str:
    kb_results = rag_search(db, tenant_id, user_message, top_k=3)
    
    context = ""
    if kb_results:
        context = "Informations de la base de connaissance:\n\n"
        for idx, result in enumerate(kb_results, 1):
            context += f"{idx}. {result['chunk_text']}\n\n"
    
    if context:
        user_prompt = f"""Contexte disponible:
{context}

Question du client: {user_message}

Réponds à la question en utilisant les informations du contexte ci-dessus."""
    else:
        user_prompt = f"""Question du client: {user_message}

Aucune information spécifique trouvée. Réponds poliment et suggère de contacter le restaurant."""
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("CHAT_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"ERROR in agent_reply: {str(e)}")
        return "Désolé, je rencontre un problème technique."