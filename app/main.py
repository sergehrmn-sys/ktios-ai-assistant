# ========================================
# AJOUTE CES IMPORTS EN HAUT DE app/main.py
# ========================================

from .agent_llm import agent_reply  # Remplace l'ancien import si présent
import json

# ========================================
# REMPLACE TES WEBHOOKS PAR CECI
# ========================================

@app.post("/webhooks/twilio/messages")
async def twilio_messages(request: Request, db: Session = Depends(get_db)):
    """
    Webhook Twilio Messages (SMS/WhatsApp) - VERSION AVEC TOOLS
    """
    form = await request.form()
    from_addr = normalize_twilio_from(form.get("From"))
    to_addr   = normalize_twilio_to(form.get("To"))
    body      = (form.get("Body") or "").strip()
    msg_sid   = form.get("MessageSid")

    # 1) Résoudre tenant via channel
    channel = find_tenant_channel(db, to_addr)
    tenant_id = channel.tenant_id

    # 2) Upsert customer
    customer = upsert_customer(db, tenant_id, from_addr)
    
    # 3) Get/create conversation
    convo = get_or_create_conversation(db, tenant_id, channel.id, customer.id)

    # 4) Sauvegarder message inbound
    add_message(
        db, tenant_id, convo.id,
        direction="in",
        role="user",
        content=body,
        provider_message_id=msg_sid
    )

    # 5) ✅ AGENT AVEC TOOLS
    agent_result = agent_reply(
        db=db,
        tenant_id=str(tenant_id),
        conversation_id=str(convo.id),
        user_text=body,
        customer_phone=from_addr
    )
    
    reply_text = agent_result["reply_text"]
    tool_calls = agent_result.get("tool_calls_made", [])

    # 6) Sauvegarder réponse outbound
    add_message(
        db, tenant_id, convo.id,
        direction="out",
        role="assistant",
        content=reply_text,
        meta={
            "tool_calls": tool_calls,
            "finish_reason": agent_result.get("finish_reason")
        }
    )

    # 7) Si handoff → mettre conversation en handoff
    if any(t["name"] == "handoff_to_human" for t in tool_calls):
        convo.status = "handoff"
        db.add(convo)
        db.commit()

    # 8) Répondre via TwiML
    from twilio.twiml.messaging_response import MessagingResponse
    resp = MessagingResponse()
    resp.message(reply_text)
    return Response(content=str(resp), media_type="application/xml")


@app.post("/webhooks/twilio/voice/turn")
async def twilio_voice_turn(request: Request, db: Session = Depends(get_db)):
    """
    Webhook Twilio Voice Turn (speech) - VERSION AVEC TOOLS
    """
    form = await request.form()
    to_addr = normalize_twilio_to(form.get("To"))
    from_addr = normalize_twilio_from(form.get("From"))
    call_sid = form.get("CallSid")
    speech = (form.get("SpeechResult") or "").strip()
    confidence = form.get("Confidence")

    # 1) Résoudre tenant
    channel = find_tenant_channel(db, to_addr)
    tenant_id = channel.tenant_id
    
    # 2) Customer + conversation
    customer = upsert_customer(db, tenant_id, from_addr)
    convo = get_or_create_conversation(db, tenant_id, channel.id, customer.id)

    # 3) Message inbound
    add_message(
        db, tenant_id, convo.id,
        direction="in",
        role="user",
        content=speech,
        provider_message_id=call_sid,
        meta={"confidence": confidence}
    )

    # 4) ✅ AGENT AVEC TOOLS
    agent_result = agent_reply(
        db=db,
        tenant_id=str(tenant_id),
        conversation_id=str(convo.id),
        user_text=speech,
        customer_phone=from_addr
    )
    
    reply_text = agent_result["reply_text"]
    tool_calls = agent_result.get("tool_calls_made", [])

    # 5) Sauvegarder réponse
    add_message(
        db, tenant_id, convo.id,
        direction="out",
        role="assistant",
        content=reply_text,
        meta={
            "tool_calls": tool_calls,
            "finish_reason": agent_result.get("finish_reason")
        }
    )

    # 6) Si handoff → Dial vers humain
    if any(t["name"] == "handoff_to_human" for t in tool_calls):
        convo.status = "handoff"
        db.add(convo)
        db.commit()
        
        # TODO: Récupérer numéro de handoff depuis tenant_settings
        handoff_number = "+14185551234"  # Remplacer par vraie config
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="fr-CA" voice="Polly.Celine">{reply_text}</Say>
  <Dial timeout="20" answerOnBridge="true">{handoff_number}</Dial>
  <Say language="fr-CA" voice="Polly.Celine">Personne n'est disponible. Laissez un message, on vous rappelle.</Say>
  <Record maxLength="60" playBeep="true" />
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # 7) Sinon → continue conversation
    twiml = twiml_say_and_gather(reply=reply_text, action_url="/webhooks/twilio/voice/turn")
    return Response(content=twiml, media_type="application/xml")


# ========================================
# ENDPOINT DE TEST (très utile en dev)
# ========================================

from pydantic import BaseModel

class TestAgentPayload(BaseModel):
    tenant_id: str
    conversation_id: str
    customer_phone: str
    user_text: str

@app.post("/api/test/agent")
def test_agent(payload: TestAgentPayload, db: Session = Depends(get_db)):
    """
    Endpoint de test pour tester l'agent sans Twilio.
    Pratique pour dev et debug.
    
    Exemple:
    {
      "tenant_id": "xxx",
      "conversation_id": "yyy",
      "customer_phone": "+14185551234",
      "user_text": "Je veux réserver pour 4 personnes ce soir à 19h"
    }
    """
    result = agent_reply(
        db=db,
        tenant_id=payload.tenant_id,
        conversation_id=payload.conversation_id,
        user_text=payload.user_text,
        customer_phone=payload.customer_phone
    )
    
    return {
        "ok": True,
        "reply": result["reply_text"],
        "tools_executed": result.get("tool_calls_made", []),
        "debug": result.get("debug", {})
    }
