import os
from openai import OpenAI
from sqlalchemy.orm import Session
from .rag import rag_search

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = "Tu es assistant virtuel du KTIOS Lounge. Reponds de maniere concise."

def agent_reply(db: Session, tenant_id: str, user_message: str) -> str:
    kb_results = rag_search(db, tenant_id, user_message, top_k=3)
    
    if kb_results and len(kb_results) > 0:
        context = "\n\n".join([r['chunk_text'] for r in kb_results])
        user_prompt = f"Contexte:\n{context}\n\nQuestion: {user_message}"
    else:
        user_prompt = f"Question: {user_message}\n\nAucune info. Suggere de contacter le 367-382-0451."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ERROR: {e}")
        if kb_results:
            return f"Voici les informations:\n\n{kb_results[0]['chunk_text'][:300]}..."
        return "Erreur technique. Contactez-nous au 367-382-0451."