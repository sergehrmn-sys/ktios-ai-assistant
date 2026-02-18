import os
import requests
from dotenv import load_dotenv

load_dotenv('.env.production')

API_URL = "https://hghvipyvtwizxebuwbcp.supabase.co"
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"Connexion a Supabase...")
print(f"Database URL: {DATABASE_URL[:50]}...")

import psycopg2
import json

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

TENANT_ID = "11111111-1111-1111-1111-111111111111"

with open('ktios_complete_real.json', 'r', encoding='utf-8') as f:
    documents = json.load(f)

for doc in documents:
    print(f"Upload: {doc['title']}")
    
    # Ingest via API locale d'abord pour avoir le code qui marche
    response = requests.post("http://localhost:8000/api/kb/quick_ingest", json={
        "tenant_id": TENANT_ID,
        "title": doc['title'],
        "raw_text": doc['raw_text'],
        "source": "manual"
    })
    
    if response.status_code == 200:
        print(f"  OK!")
    else:
        print(f"  ERREUR: {response.text}")

conn.close()
print("\nTermine!")