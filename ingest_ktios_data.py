import os
from sqlalchemy.orm import Session
from .rag import rag_search

def agent_reply(db: Session, tenant_id: str, user_message: str) -> str:
    kb_results = rag_search(db, tenant_id, user_message, top_k=3)
    
    if kb_results and len(kb_results) > 0:
        response = "Voici les informations trouvées:\n\n"
        for idx, result in enumerate(kb_results, 1):
            response += f"{result['chunk_text']}\n\n"
        return response.strip()
    else:
        return "Désolé, je n'ai pas trouvé d'information sur ce sujet. Contactez-nous au 367-382-0451 pour plus de détails."