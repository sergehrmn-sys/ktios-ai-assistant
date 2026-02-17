import json
import requests

API_URL = "http://localhost:8000/api/kb/quick_ingest"
TENANT_ID = "11111111-1111-1111-1111-111111111111"

with open("ktios_complete_real.json", "r", encoding="utf-8") as f:
    documents = json.load(f)

for doc in documents:
    doc["tenant_id"] = TENANT_ID
    try:
        response = requests.post(API_URL, json=doc)
        if response.status_code == 200:
            print(f"OK: {doc['title']}")
        else:
            print(f"ERREUR: {response.text}")
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")

print(f"\nTermine ! {len(documents)} documents.")