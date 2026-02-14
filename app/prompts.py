"""
Prompts système + Tool definitions
"""

SYSTEM_PROMPT = """Tu es un réceptionniste IA professionnel pour un établissement (bar/restaurant/hôtel).

OBJECTIF:
Répondre rapidement et prendre une réservation en 4-6 échanges maximum.

RÈGLES STRICTES (JAMAIS VIOLER):
1. N'invente JAMAIS une information. Si tu ne sais pas → propose un transfert.
2. Utilise UNIQUEMENT la Base de Connaissance fournie.
3. Pour une réservation, tu DOIS collecter:
   - Date et heure précises
   - Nombre de personnes
   - Nom du client (ou confirmer téléphone)
4. Pose UNE SEULE question à la fois.
5. AVANT de créer une réservation, tu DOIS:
   a) Appeler check_availability
   b) Confirmer avec le client
   c) Ensuite appeler create_reservation
6. Si le client demande un humain → appelle handoff_to_human immédiatement.
7. Si tu détectes confusion, frustration, ou cas complexe → propose handoff.

WORKFLOW RÉSERVATION (RESPECTER):
1. Client exprime intention → collecter date/heure
2. Collecter nombre de personnes
3. Appeler check_availability
4. Si disponible → confirmer détails + nom
5. Confirmation client → appeler create_reservation
6. Confirmation finale avec numéro de réservation

STYLE:
- Réponses COURTES (2-3 phrases max)
- Ton professionnel mais chaleureux
- Français canadien (fr-CA)
- Tutoiement acceptable si client tutoie

EXEMPLES RÉPONSES:
❌ MAUVAIS: "Bien sûr! Je vais vérifier la disponibilité pour vous. Notre restaurant propose une ambiance chaleureuse et..."
✅ BON: "À quelle heure ce soir?"

❌ MAUVAIS: "Je comprends que vous souhaitez réserver..."
✅ BON: "Pour combien de personnes?"
"""

# Tool definitions (format OpenAI)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Vérifie la disponibilité pour une réservation à une date/heure précise. TOUJOURS appeler AVANT create_reservation.",
            "parameters": {
                "type": "object",
                "required": ["start_time", "party_size"],
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "UUID du tenant (auto-injecté, ne pas spécifier)"
                    },
                    "location_id": {
                        "type": ["string", "null"],
                        "description": "UUID succursale si multi-sites"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "ISO 8601 avec timezone (ex: 2026-02-20T19:00:00-05:00). TOUJOURS inclure timezone."
                    },
                    "party_size": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Nombre de personnes"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reservation",
            "description": "Crée une réservation confirmée. Appeler UNIQUEMENT après check_availability ET confirmation du client.",
            "parameters": {
                "type": "object",
                "required": ["customer", "start_time", "party_size"],
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "UUID tenant (auto-injecté)"
                    },
                    "location_id": {
                        "type": ["string", "null"]
                    },
                    "customer": {
                        "type": "object",
                        "required": ["phone_e164"],
                        "properties": {
                            "full_name": {
                                "type": ["string", "null"],
                                "description": "Nom complet du client"
                            },
                            "phone_e164": {
                                "type": "string",
                                "description": "Numéro téléphone format E.164 (ex: +14185551234)"
                            },
                            "email": {
                                "type": ["string", "null"]
                            }
                        }
                    },
                    "start_time": {
                        "type": "string",
                        "description": "ISO 8601 avec timezone"
                    },
                    "party_size": {
                        "type": "integer",
                        "minimum": 1
                    },
                    "notes": {
                        "type": ["string", "null"],
                        "description": "Notes spéciales (anniversaire, allergies, etc.)"
                    },
                    "source_conversation_id": {
                        "type": "string",
                        "description": "UUID conversation (auto-injecté)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_reservation",
            "description": "Modifie une réservation existante (heure, nombre, notes, statut).",
            "parameters": {
                "type": "object",
                "required": ["reservation_id", "changes"],
                "properties": {
                    "tenant_id": {"type": "string"},
                    "reservation_id": {
                        "type": "string",
                        "description": "UUID de la réservation à modifier"
                    },
                    "changes": {
                        "type": "object",
                        "description": "Champs à modifier: start_time, party_size, notes, status",
                        "properties": {
                            "start_time": {"type": "string"},
                            "party_size": {"type": "integer"},
                            "notes": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "confirmed", "cancelled", "no_show"]
                            }
                        }
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reservation",
            "description": "Annule une réservation existante.",
            "parameters": {
                "type": "object",
                "required": ["reservation_id"],
                "properties": {
                    "tenant_id": {"type": "string"},
                    "reservation_id": {
                        "type": "string",
                        "description": "UUID réservation à annuler"
                    },
                    "reason": {
                        "type": ["string", "null"],
                        "description": "Raison de l'annulation"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_human",
            "description": "Transfère la conversation à un humain. Utiliser si: client demande explicitement, situation complexe, ou frustration détectée.",
            "parameters": {
                "type": "object",
                "required": ["reason"],
                "properties": {
                    "tenant_id": {"type": "string"},
                    "conversation_id": {"type": "string"},
                    "reason": {
                        "type": "string",
                        "description": "Raison du transfert (ex: 'Client demande le gérant', 'Situation complexe - événement privé')"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "default": "normal",
                        "description": "Urgence: high si client insistant/frustré"
                    }
                }
            }
        }
    }
]
