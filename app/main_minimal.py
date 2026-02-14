import os
from fastapi import FastAPI, Request, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
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