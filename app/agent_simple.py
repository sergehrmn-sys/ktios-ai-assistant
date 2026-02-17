import os
from openai import OpenAI
from sqlalchemy.orm import Session
from .rag import rag_search

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Tu es l'assistant virtuel du KTIOS Lounge, un bar haut de gamme a Quebec.
Reponds toujours en francais, de maniere concise (2-3 phrases max).
Utilise les informations du contexte fourni pour repondre precisement.
Si tu ne trouves pas l'information, suggere de contacter le 367-382-0451."""

def agent_reply(db: Session, tenant_id: str, user_message: str, conversation_history: list = None) -> str:
    if conversation_history is None:
        conversation_history = []

    kb_results = rag_search(db, tenant_id, user_message, top_k=3)

    if kb_results and len(kb_results) > 0:
        context = "\n\n".join([r['chunk_text'] for r in kb_results])
        system_with_context = f"{SYSTEM_PROMPT}\n\nContexte KTIOS:\n{context}"
    else:
        system_with_context = SYSTEM_PROMPT

    messages = [{"role": "system", "content": system_with_context}]

    for msg in conversation_history[-6:]:
        messages.append(msg)

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"ERROR OpenAI: {e}")
        if kb_results:
            return kb_results[0]['chunk_text'][:300]
        return "Erreur technique. Contactez-nous au 367-382-0451."