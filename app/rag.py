import os
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    """Découpe le texte en chunks avec chevauchement"""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks

def ingest_kb_document(db: Session, tenant_id: str, title: str, raw_text: str, source: str = "manual"):
    """Ingère un document dans la base de connaissance"""
    
    try:
        print(f"DEBUG: Starting ingest for tenant {tenant_id}")
        
        doc_id = uuid.uuid4()
        
        print(f"DEBUG: Inserting document with id {doc_id}")
        
        db.execute(
            text("""
            INSERT INTO kb_documents (id, tenant_id, title, source, raw_text, created_at, updated_at)
            VALUES (:id, :tenant_id, :title, :source, :raw_text, now(), now())
            """),
            {
                "id": doc_id,
                "tenant_id": uuid.UUID(tenant_id),
                "title": title,
                "source": source,
                "raw_text": raw_text
            }
        )
        
        print(f"DEBUG: Document inserted successfully")
        
        chunks = chunk_text(raw_text)
        
        print(f"DEBUG: Created {len(chunks)} chunks")
        
        for idx, chunk in enumerate(chunks):
            db.execute(
                text("""
                INSERT INTO kb_chunks (id, document_id, tenant_id, chunk_index, chunk_text, metadata, created_at)
                VALUES (:id, :document_id, :tenant_id, :chunk_index, :chunk_text, :metadata, now())
                """),
                {
                    "id": uuid.uuid4(),
                    "document_id": doc_id,
                    "tenant_id": uuid.UUID(tenant_id),
                    "chunk_index": idx,
                    "chunk_text": chunk,
                    "metadata": None
                }
            )
        
        print(f"DEBUG: All chunks inserted")
        
        db.commit()
        
        print(f"DEBUG: Transaction committed")
        
        return str(doc_id)
        
    except Exception as e:
        print(f"ERROR in ingest_kb_document: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def rag_search(db: Session, tenant_id: str, query: str, top_k: int = 3):
    """Recherche dans la base de connaissance avec extraction de mots-clés"""
    
    print(f"DEBUG RAG_SEARCH: tenant_id={tenant_id}, type={type(tenant_id)}")
    print(f"DEBUG RAG_SEARCH: query={query}")
    
    # Extrait les mots importants (retire les mots vides français)
    stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'd', 'et', 'ou', 'à', 'au', 
              'est', 'sont', 'quel', 'quelle', 'quels', 'quelles', 'comment', 'combien',
              'avez', 'vous', 'je', 'il', 'elle', 'nous', 'ils', 'elles', 'sur', 'dans', 'prix'}