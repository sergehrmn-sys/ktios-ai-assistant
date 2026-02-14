"""
Agent LLM avec RAG + Tool Execution
Version complète avec boucle d'exécution
"""

import os
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from .prompts import SYSTEM_PROMPT
from .rag import rag_search
from .tool_executor import execute_agent_with_tools


def agent_reply(
    db: Session,
    tenant_id: str,
    conversation_id: str,
    user_text: str,
    customer_phone: str
) -> Dict[str, Any]:
    """
    Point d'entrée principal de l'agent.
    
    1. Recherche RAG dans la KB
    2. Exécute l'agent avec tools
    3. Retourne réponse finale + métadonnées
    
    Returns:
        {
            "reply_text": str,              # Réponse à envoyer au client
            "tool_calls_made": List[dict],  # Tools exécutés (pour logs)
            "finish_reason": str,           # stop|tool_calls|max_iterations
            "debug": dict                   # Infos debug
        }
    """
    
    # RAG: chercher dans la KB
    kb_chunks = rag_search(
        db=db,
        tenant_id=tenant_id,
        query=user_text,
        top_k=5
    )
    
    # Exécuter agent avec boucle tools
    result = execute_agent_with_tools(
        db=db,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        customer_phone=customer_phone,
        user_text=user_text,
        kb_chunks=kb_chunks,
        system_prompt=SYSTEM_PROMPT,
        max_iterations=3  # Maximum 3 aller-retours avec tools
    )
    
    # Ajouter les KB chunks au debug
    result["debug"]["kb_chunks"] = kb_chunks
    
    return result
