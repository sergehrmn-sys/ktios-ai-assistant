-- Table pour stocker les documents de la base de connaissance
CREATE TABLE IF NOT EXISTS kb_documents (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title text NOT NULL,
    source text,
    raw_text text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Table pour stocker les chunks SANS embeddings (recherche texte simple)
CREATE TABLE IF NOT EXISTS kb_chunks (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id uuid NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    chunk_index int NOT NULL,
    chunk_text text NOT NULL,
    metadata jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Index pour recherche texte en français
CREATE INDEX IF NOT EXISTS kb_chunks_text_idx ON kb_chunks USING gin(to_tsvector('french', chunk_text));

-- Index pour filtrer par tenant
CREATE INDEX IF NOT EXISTS kb_chunks_tenant_idx ON kb_chunks(tenant_id);