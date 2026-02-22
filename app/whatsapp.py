import os
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session
from .agent_simple import agent_reply

# Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_whatsapp_message(to_number: str, message: str):
    """Envoie un message WhatsApp via Twilio"""
    
    message = client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        body=message,
        to=f"whatsapp:{to_number}"
    )
    
    return message.sid

def process_whatsapp_message(from_number: str, message_body: str, db: Session) -> str:
    """Traite un message WhatsApp et retourne la réponse"""
    
    # Utilise l'agent IA existant
    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    
    response = agent_reply(
        db=db,
        tenant_id=TENANT_ID,
        user_message=message_body,
        conversation_history=[]
    )
    
    return response