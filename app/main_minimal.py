import os
import uuid as uuid_lib
from fastapi import FastAPI, Request, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, text
from pydantic import BaseModel

from .db import get_db
from .models import Channel, Customer, Conversation, Message

app = FastAPI(title="AI Front Desk MVP")

@app.get("/")
def root():
    return {"message": "AI Front Desk API - Fonctionne!", "status": "ok"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

class KBIngestRequest(BaseModel):
    tenant_id: str
    title: str
    raw_text: str
    source: str = "manual"

@app.post("/api/kb/quick_ingest")
def kb_quick_ingest(
    request: KBIngestRequest,
    db: Session = Depends(get_db)
):
    from .rag import ingest_kb_document
    try:
        doc_id = ingest_kb_document(db, request.tenant_id, request.title, request.raw_text, request.source)
        return {"ok": True, "document_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class KBSearchRequest(BaseModel):
    tenant_id: str
    query: str
    top_k: int = 3

@app.post("/api/kb/search")
def kb_search(
    request: KBSearchRequest,
    db: Session = Depends(get_db)
):
    from .rag import rag_search
    try:
        results = rag_search(db, request.tenant_id, request.query, request.top_k)
        return {"ok": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/reservation")
def test_create_reservation(
    tenant_id: str,
    customer_name: str,
    party_size: int,
    start_time: str,
    db: Session = Depends(get_db)
):
    try:
        customer = Customer(
            tenant_id=tenant_id,
            full_name=customer_name,
            phone_e164="+15555551234"
        )
        db.add(customer)
        db.flush()
        
        new_reservation_id = uuid_lib.uuid4()
        
        db.execute(
            text("""
            INSERT INTO reservations (id, tenant_id, customer_id, party_size, start_time, status, created_at, updated_at)
            VALUES (:res_id, :tenant_id, :customer_id, :party_size, :start_time, 'confirmed', now(), now())
            """),
            {
                "res_id": new_reservation_id,
                "tenant_id": uuid_lib.UUID(tenant_id),
                "customer_id": customer.id,
                "party_size": party_size,
                "start_time": start_time
            }
        )
        
        db.commit()
        
        return {
            "ok": True,
            "reservation_id": str(new_reservation_id),
            "customer_name": customer_name,
            "party_size": party_size,
            "start_time": start_time
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reservations")
def list_reservations(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    try:
        rows = db.execute(
            text("""
            SELECT r.id, r.party_size, r.start_time, r.status, r.notes, c.full_name
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            WHERE r.tenant_id = :tenant_id
            ORDER BY r.start_time DESC
            LIMIT 20
            """),
            {"tenant_id": uuid_lib.UUID(tenant_id)}
        ).mappings().all()
        
        return {
            "ok": True,
            "count": len(rows),
            "reservations": [dict(r) for r in rows]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    tenant_id: str
    message: str

@app.post("/api/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    from .agent_simple import agent_reply
    try:
        response = agent_reply(db, request.tenant_id, request.message)
        return {"ok": True, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))