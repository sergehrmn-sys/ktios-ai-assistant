import os
from typing import List, Dict, Any
from openai import OpenAI
import tiktoken
from sqlalchemy import text
from sqlalchemy.orm import Session

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

client = OpenAI(api_key=OPENAI_API_KEY)

def chunk_text(text_in: str, max_tokens: int = 350, overlap: int = 60) -> List[str]:
    text_in = (text_in or "").strip()
    if not text_in:
        return []
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text_in)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk = enc.decode(chunk_tokens).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(tokens):
            break
        start = max(0, end - overlap)
    return chunks

def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [d.embedding for d in resp.data]

def ingest_kb_document(db: Session, tenant_id: str, title: str, raw_text: str, source: str = "manual", metadata: Dict[str, Any] | None = None) -> str:
    metadata = metadata or {}
    doc_id = db.execute(
        text("""
        INSERT INTO kb_documents (id, tenant_id, title, source, raw_text, metadata, created_at, updated_at)
        VALUES (uuid_generate_v4(), :tenant_id, :title, :source, :raw_text, :metadata::jsonb, now(), now())
        RETURNING id
        """),
        {"tenant_id": tenant_id, "title": title, "source": source, "raw_text": raw_text, "metadata": metadata}
    ).scalar_one()
    chunks = chunk_text(raw_text)
    embeddings = embed_texts(chunks)
    for idx, (content, emb) in enumerate(zip(chunks, embeddings)):
        db.execute(
            text("""
            INSERT INTO kb_chunks (id, tenant_id, document_id, chunk_index, content, embedding, metadata, created_at)
            VALUES (uuid_generate_v4(), :tenant_id, :document_id, :chunk_index, :content, :embedding, :metadata::jsonb, now())
            """),
            {"tenant_id": tenant_id, "document_id": str(doc_id), "chunk_index": idx, "content": content, "embedding": emb, "metadata": {"title": title, "source": source}}
        )
    db.commit()
    return str(doc_id)

def rag_search(db: Session, tenant_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []
    q_emb = embed_texts([query])[0]
    rows = db.execute(
        text("""
        SELECT c.id, c.content, c.metadata, (c.embedding <=> :q_emb) AS distance
        FROM kb_chunks c
        WHERE c.tenant_id = :tenant_id
        ORDER BY c.embedding <=> :q_emb
        LIMIT :top_k
        """),
        {"tenant_id": tenant_id, "q_emb": q_emb, "top_k": top_k}
    ).mappings().all()
    return [{"chunk_id": str(r["id"]), "content": r["content"], "metadata": r["metadata"], "distance": float(r["distance"])} for r in rows]