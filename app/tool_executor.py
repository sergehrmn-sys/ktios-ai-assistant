"""
Tool Executor - Gère l'exécution des tools demandés par le LLM
Boucle complète: LLM → tool call → execution → résultat → LLM → réponse finale
"""

import os
import json
import requests
from typing import Dict, Any, List
from openai import OpenAI
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session

CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# Base URL de tes endpoints internes (local dev ou production)
INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://localhost:8000")


class ToolExecutor:
    """
    Exécute les tools demandés par le LLM et renvoie les résultats.
    """
    
    def __init__(self, db: Session, tenant_id: str, conversation_id: str, customer_phone: str):
        self.db = db
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.customer_phone = customer_phone
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route et exécute le tool approprié.
        Retourne le résultat sous forme de dict.
        """
        if tool_name == "check_availability":
            return self._check_availability(arguments)
        
        elif tool_name == "create_reservation":
            return self._create_reservation(arguments)
        
        elif tool_name == "modify_reservation":
            return self._modify_reservation(arguments)
        
        elif tool_name == "cancel_reservation":
            return self._cancel_reservation(arguments)
        
        elif tool_name == "handoff_to_human":
            return self._handoff_to_human(arguments)
        
        else:
            return {"error": f"Tool '{tool_name}' non reconnu"}
    
    def _check_availability(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vérifie la disponibilité pour une réservation.
        Pour MVP: logique simple (heures d'ouverture + capacité max).
        """
        try:
            start_time_str = args.get("start_time")
            party_size = args.get("party_size")
            
            # Parse datetime
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            
            # 1) Vérifier heures d'ouverture (simplifié - à adapter selon tenant_settings)
            hour = start_time.hour
            day_of_week = start_time.strftime("%A").lower()
            
            # Pour MVP: ouvert 11h-02h tous les jours (adapter selon ta KB)
            if hour < 11 or hour > 23:
                return {
                    "available": False,
                    "reason": "en_dehors_heures",
                    "suggestions": [
                        (start_time.replace(hour=18, minute=0)).isoformat(),
                        (start_time.replace(hour=19, minute=0)).isoformat(),
                        (start_time.replace(hour=20, minute=0)).isoformat(),
                    ]
                }
            
            # 2) Vérifier capacité (simplifié - checker réservations existantes)
            existing = self.db.execute(
                text("""
                SELECT COUNT(*) as cnt, COALESCE(SUM(party_size), 0) as total_guests
                FROM reservations
                WHERE tenant_id = :tenant_id
                  AND status IN ('confirmed', 'pending')
                  AND start_time BETWEEN :start - INTERVAL '2 hours' AND :start + INTERVAL '2 hours'
                """),
                {"tenant_id": self.tenant_id, "start": start_time}
            ).mappings().first()
            
            # Capacité max (à mettre dans tenant_settings plus tard)
            MAX_CAPACITY = 80
            MAX_CONCURRENT_RESERVATIONS = 15
            
            total_guests = existing["total_guests"] or 0
            total_reservations = existing["cnt"] or 0
            
            if total_guests + party_size > MAX_CAPACITY:
                return {
                    "available": False,
                    "reason": "capacité_atteinte",
                    "suggestions": [
                        (start_time + timedelta(hours=1)).isoformat(),
                        (start_time + timedelta(hours=2)).isoformat(),
                    ]
                }
            
            if total_reservations >= MAX_CONCURRENT_RESERVATIONS:
                return {
                    "available": False,
                    "reason": "trop_réservations_simultanées",
                    "suggestions": [
                        (start_time + timedelta(minutes=30)).isoformat(),
                        (start_time + timedelta(hours=1)).isoformat(),
                    ]
                }
            
            # Disponible !
            return {
                "available": True,
                "start_time": start_time.isoformat(),
                "party_size": party_size,
                "current_occupancy": total_guests,
            }
        
        except Exception as e:
            return {"error": f"Erreur check_availability: {str(e)}"}
    
    def _create_reservation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée une réservation confirmée.
        """
        try:
            customer_data = args.get("customer", {})
            start_time_str = args.get("start_time")
            party_size = args.get("party_size")
            notes = args.get("notes", "")
            
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            
            # Vérifier dispo une dernière fois
            avail_check = self._check_availability({
                "start_time": start_time_str,
                "party_size": party_size,
            })
            
            if not avail_check.get("available"):
                return {
                    "success": False,
                    "error": "Créneau devenu indisponible",
                    "suggestions": avail_check.get("suggestions", [])
                }
            
            # Upsert customer
            customer_phone = customer_data.get("phone_e164", self.customer_phone)
            customer_name = customer_data.get("full_name")
            customer_email = customer_data.get("email")
            
            customer_id = self.db.execute(
                text("""
                INSERT INTO customers (id, tenant_id, full_name, phone_e164, email, created_at, updated_at)
                VALUES (uuid_generate_v4(), :tenant_id, :name, :phone, :email, now(), now())
                ON CONFLICT (tenant_id, phone_e164) 
                DO UPDATE SET 
                    full_name = COALESCE(EXCLUDED.full_name, customers.full_name),
                    email = COALESCE(EXCLUDED.email, customers.email),
                    updated_at = now()
                RETURNING id
                """),
                {
                    "tenant_id": self.tenant_id,
                    "name": customer_name,
                    "phone": customer_phone,
                    "email": customer_email,
                }
            ).scalar_one()
            
            # Créer réservation
            reservation_id = self.db.execute(
                text("""
                INSERT INTO reservations (
                    id, tenant_id, customer_id, source_conversation_id,
                    party_size, start_time, status, notes, created_at, updated_at
                )
                VALUES (
                    uuid_generate_v4(), :tenant_id, :customer_id, :conversation_id,
                    :party_size, :start_time, 'confirmed', :notes, now(), now()
                )
                RETURNING id
                """),
                {
                    "tenant_id": self.tenant_id,
                    "customer_id": str(customer_id),
                    "conversation_id": self.conversation_id,
                    "party_size": party_size,
                    "start_time": start_time,
                    "notes": notes,
                }
            ).scalar_one()
            
            self.db.commit()
            
            # TODO: Créer événement Google Calendar ici (optionnel MVP)
            
            return {
                "success": True,
                "reservation_id": str(reservation_id),
                "status": "confirmed",
                "start_time": start_time.isoformat(),
                "party_size": party_size,
                "customer_name": customer_name or "Client",
            }
        
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Erreur création: {str(e)}"}
    
    def _modify_reservation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modifie une réservation existante.
        """
        try:
            reservation_id = args.get("reservation_id")
            changes = args.get("changes", {})
            
            # Build UPDATE dynamically
            set_clauses = []
            params = {"reservation_id": reservation_id, "tenant_id": self.tenant_id}
            
            if "start_time" in changes:
                set_clauses.append("start_time = :new_start_time")
                params["new_start_time"] = datetime.fromisoformat(changes["start_time"].replace('Z', '+00:00'))
            
            if "party_size" in changes:
                set_clauses.append("party_size = :new_party_size")
                params["new_party_size"] = changes["party_size"]
            
            if "notes" in changes:
                set_clauses.append("notes = :new_notes")
                params["new_notes"] = changes["notes"]
            
            if "status" in changes:
                set_clauses.append("status = :new_status")
                params["new_status"] = changes["status"]
            
            if not set_clauses:
                return {"success": False, "error": "Aucun changement spécifié"}
            
            set_clauses.append("updated_at = now()")
            
            query = f"""
            UPDATE reservations
            SET {", ".join(set_clauses)}
            WHERE id = :reservation_id AND tenant_id = :tenant_id
            RETURNING id
            """
            
            result = self.db.execute(text(query), params).scalar_one_or_none()
            
            if not result:
                return {"success": False, "error": "Réservation non trouvée"}
            
            self.db.commit()
            
            return {"success": True, "reservation_id": str(result)}
        
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Erreur modification: {str(e)}"}
    
    def _cancel_reservation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Annule une réservation.
        """
        try:
            reservation_id = args.get("reservation_id")
            reason = args.get("reason", "Annulée par le client")
            
            result = self.db.execute(
                text("""
                UPDATE reservations
                SET status = 'cancelled', notes = COALESCE(notes || E'\n', '') || :reason, updated_at = now()
                WHERE id = :reservation_id AND tenant_id = :tenant_id
                RETURNING id
                """),
                {"reservation_id": reservation_id, "tenant_id": self.tenant_id, "reason": f"Annulation: {reason}"}
            ).scalar_one_or_none()
            
            if not result:
                return {"success": False, "error": "Réservation non trouvée"}
            
            self.db.commit()
            
            return {"success": True, "reservation_id": str(result), "status": "cancelled"}
        
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Erreur annulation: {str(e)}"}
    
    def _handoff_to_human(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée une demande de transfert vers un humain.
        """
        try:
            reason = args.get("reason", "Demande du client")
            priority = args.get("priority", "normal")
            
            handoff_id = self.db.execute(
                text("""
                INSERT INTO handoff_requests (
                    id, tenant_id, conversation_id, reason, priority, status, created_at, updated_at
                )
                VALUES (
                    uuid_generate_v4(), :tenant_id, :conversation_id, :reason, :priority, 'open', now(), now()
                )
                RETURNING id
                """),
                {
                    "tenant_id": self.tenant_id,
                    "conversation_id": self.conversation_id,
                    "reason": reason,
                    "priority": priority,
                }
            ).scalar_one()
            
            # Mettre conversation en état handoff
            self.db.execute(
                text("""
                UPDATE conversations
                SET status = 'handoff', updated_at = now()
                WHERE id = :conversation_id
                """),
                {"conversation_id": self.conversation_id}
            )
            
            self.db.commit()
            
            # TODO: Envoyer notification (SMS/email au gérant)
            
            return {
                "success": True,
                "handoff_request_id": str(handoff_id),
                "status": "open",
                "message": "Un membre de l'équipe va vous contacter sous peu."
            }
        
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Erreur handoff: {str(e)}"}


def execute_agent_with_tools(
    db: Session,
    tenant_id: str,
    conversation_id: str,
    customer_phone: str,
    user_text: str,
    kb_chunks: List[Dict[str, Any]],
    system_prompt: str,
    max_iterations: int = 3
) -> Dict[str, Any]:
    """
    Boucle complète d'exécution:
    1. Envoie message au LLM avec KB + tools
    2. Si LLM demande un tool → exécute
    3. Renvoie résultat au LLM
    4. LLM génère réponse finale
    5. Retourne réponse + métadonnées
    
    Args:
        max_iterations: nombre max de boucles tool (évite boucles infinies)
    
    Returns:
        {
            "reply_text": str,
            "tool_calls_made": List[dict],
            "finish_reason": str,
            "debug": dict
        }
    """
    
    from .prompts import TOOLS  # Import depuis ton fichier prompts.py
    
    executor = ToolExecutor(db, tenant_id, conversation_id, customer_phone)
    
    # Build KB context
    kb_context = "\n".join([
        f"[{i+1}] {c.get('content', '')}"
        for i, c in enumerate(kb_chunks[:5])
    ]) if kb_chunks else "Aucune information dans la base de connaissance."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"BASE DE CONNAISSANCE:\n{kb_context}"},
        {"role": "user", "content": user_text}
    ]
    
    tool_calls_made = []
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Appel LLM
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
        
        choice = response.choices[0]
        message = choice.message
        
        # Si pas de tool calls → réponse finale
        if not message.tool_calls:
            return {
                "reply_text": message.content or "",
                "tool_calls_made": tool_calls_made,
                "finish_reason": choice.finish_reason,
                "debug": {
                    "iterations": iteration,
                    "kb_chunks_used": len(kb_chunks),
                }
            }
        
        # Exécuter les tools
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        })
        
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            # Injecter automatiquement tenant_id et conversation_id si manquants
            if "tenant_id" not in tool_args:
                tool_args["tenant_id"] = tenant_id
            if "conversation_id" not in tool_args and tool_name == "handoff_to_human":
                tool_args["conversation_id"] = conversation_id
            if "source_conversation_id" not in tool_args and tool_name == "create_reservation":
                tool_args["source_conversation_id"] = conversation_id
            
            # Exécuter
            result = executor.execute_tool(tool_name, tool_args)
            
            tool_calls_made.append({
                "name": tool_name,
                "arguments": tool_args,
                "result": result,
            })
            
            # Ajouter résultat aux messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": json.dumps(result, ensure_ascii=False)
            })
    
    # Max iterations atteint (safeguard)
    return {
        "reply_text": "Je rencontre une difficulté technique. Un membre de l'équipe va vous contacter.",
        "tool_calls_made": tool_calls_made,
        "finish_reason": "max_iterations",
        "debug": {"iterations": iteration}
    }
