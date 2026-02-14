import os
from urllib.parse import urlencode
from fastapi import FastAPI, Request, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from pydantic import BaseModel
import json

from .db import get_db
from .models import Channel, Customer, Conversation, Message
from .twilio_utils import twiml_gather_speech, twiml_say_and_gather
from .agent_llm import agent_reply
from .rag import ingest_kb_document, rag_search

app = FastAPI(title="AI Front Desk MVP")

PROVIDER = "twilio"

def normalize_twilio_to(value: str) -> str:
    return (value or "").strip()

def normalize_twilio_from(value: str) -> str:
    return (value or "").strip()

def find_tenant_channel(db: Session, to_address: str) -> Channel:
    stmt = select(Channel).where(
        and_(
            Channel.provider == PROVIDER,
            Channel.address == to_address,
            Channel.is_active == True
        )
    )
    ch = db.execute(stmt).scalars().first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not configured")
    return ch

def upsert_customer(db: Session, tenant_id, from_address: str) -> Customer:
    stmt = select(Customer).where(
        and_(
            Customer.tenant_id == tenant_id,
            Customer.phone_e164 == from_address
        )
    )
    cust = db.execute(stmt).scalars().first()
    if cust:
        return cust
    cust = Customer(tenant_id=tenant_id, phone_e164=from_address)
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust

def get_or_create_conversation(db: Session, tenant_id, channel_id, customer_id) -> Conversation:
    stmt = (
        select(Conversation)
        .where(and_(
            Conversation.tenant_id == tenant_id,
            Conversation.channel_id == channel_id,
            Conversation.customer_id == customer_id,
            Conversation.status == "open"
        ))
        .order_by(desc(Conversation.created_at))
        .limit(1)
    )
    convo = db.execute(stmt).scalars().first()
    if convo:
        return convo
    convo = Conversation(
        tenant_id=tenant_id,
        channel_id=channel_id,
        customer_id=customer_id,
        status="open",
        context={"state": "INTENT"}
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo

def add_message(db: Session, tenant_id, conversation_id, direction, role, content, provider_message_id=None, meta=None):
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        direction=direction,
        role=role,
        content=content,
        content_type="text",
        provider_message_id=provider_message_id,
        meta=meta
    )
    db.add(msg)
    db.commit()
    return msg