import os
from openai import OpenAI
from sqlalchemy.orm import Session
from .rag import rag_search

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Tu es l'assistant virtuel du KTIOS Lounge, un bar haut de gamme à Québec.

Réponds toujours en français, de manière concise (2-3 phrases max).

Utilise les informations du contexte fourni pour répondre précisément.

IMPORTANT :
- Si tu ne trouves pas EXACTEMENT ce que le client demande MAIS que tu vois quelque chose de similaire dans le contexte, propose-le.
- Par exemple, si le client demande "Hennes" et que tu vois "Hennessy" dans le contexte, propose "Hennessy".
- Ne dis JAMAIS "nous ne proposons pas" si tu n'es pas certain. Dans le doute, suggère de contacter le 367-382-0451.
- Si l'information n'est pas dans le contexte, dis "Je n'ai pas cette information précise" et suggère de contacter le 367-382-0451.
"""

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