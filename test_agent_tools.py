#!/usr/bin/env python3
"""
Script de test complet - Agent avec Tools
Teste le workflow complet sans Twilio
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
API_BASE = "http://localhost:8000"
TENANT_ID = "YOUR-TENANT-UUID-HERE"  # Remplacer par ton UUID
CONVERSATION_ID = "YOUR-CONVERSATION-UUID-HERE"  # Remplacer
CUSTOMER_PHONE = "+14185551234"

def test_agent(user_message: str):
    """Envoie un message à l'agent et affiche la réponse + tools"""
    print(f"\n{'='*60}")
    print(f"👤 CLIENT: {user_message}")
    print(f"{'='*60}")
    
    response = requests.post(
        f"{API_BASE}/api/test/agent",
        json={
            "tenant_id": TENANT_ID,
            "conversation_id": CONVERSATION_ID,
            "customer_phone": CUSTOMER_PHONE,
            "user_text": user_message
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Erreur: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    
    print(f"\n🤖 AGENT: {result['reply']}")
    
    if result.get('tools_executed'):
        print(f"\n🔧 TOOLS EXÉCUTÉS:")
        for tool in result['tools_executed']:
            print(f"  - {tool['name']}")
            print(f"    Args: {json.dumps(tool['arguments'], indent=6, ensure_ascii=False)}")
            print(f"    Résultat: {json.dumps(tool['result'], indent=6, ensure_ascii=False)}")
    
    debug = result.get('debug', {})
    if debug:
        print(f"\n📊 DEBUG:")
        print(f"  - Itérations: {debug.get('iterations', 'N/A')}")
        print(f"  - KB chunks utilisés: {debug.get('kb_chunks_used', 0)}")


def run_scenario_complete():
    """
    Scénario complet: réservation de A à Z
    """
    print("\n" + "="*70)
    print("🧪 TEST SCÉNARIO COMPLET - RÉSERVATION")
    print("="*70)
    
    # Calculer une date/heure future (demain 19h)
    tomorrow_7pm = datetime.now() + timedelta(days=1)
    tomorrow_7pm = tomorrow_7pm.replace(hour=19, minute=0, second=0, microsecond=0)
    
    # 1. Intention
    test_agent("Bonjour, je veux réserver une table")
    input("\n⏸️  Appuie sur ENTER pour continuer...")
    
    # 2. Date/heure
    test_agent(f"Demain soir à 19h")
    input("\n⏸️  Appuie sur ENTER pour continuer...")
    
    # 3. Nombre de personnes
    test_agent("Pour 4 personnes")
    input("\n⏸️  Appuie sur ENTER pour continuer...")
    
    # 4. Nom
    test_agent("Au nom de Serge")
    input("\n⏸️  Appuie sur ENTER pour continuer...")
    
    # 5. Confirmation
    test_agent("Oui, c'est bon")
    input("\n⏸️  Appuie sur ENTER pour continuer...")
    
    print("\n✅ SCÉNARIO TERMINÉ")


def run_scenario_handoff():
    """
    Scénario handoff: client demande un humain
    """
    print("\n" + "="*70)
    print("🧪 TEST SCÉNARIO HANDOFF")
    print("="*70)
    
    test_agent("Je veux parler au gérant")
    
    print("\n✅ SCÉNARIO TERMINÉ")


def run_scenario_unavailable():
    """
    Scénario indisponibilité: créer conflit
    """
    print("\n" + "="*70)
    print("🧪 TEST SCÉNARIO INDISPONIBILITÉ")
    print("="*70)
    
    # Demander un horaire hors limites (3h du matin)
    test_agent("Je veux réserver pour demain à 3h du matin, 2 personnes")
    
    print("\n✅ SCÉNARIO TERMINÉ")


def run_scenario_faq():
    """
    Scénario FAQ: questions simples
    """
    print("\n" + "="*70)
    print("🧪 TEST SCÉNARIO FAQ")
    print("="*70)
    
    test_agent("Quels sont vos horaires?")
    input("\n⏸️  Appuie sur ENTER pour continuer...")
    
    test_agent("Quelle est votre adresse?")
    input("\n⏸️  Appuie sur ENTER pour continuer...")
    
    test_agent("Avez-vous un menu végétarien?")
    
    print("\n✅ SCÉNARIO TERMINÉ")


if __name__ == "__main__":
    import sys
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                   🧪 TEST AGENT AVEC TOOLS                    ║
╚═══════════════════════════════════════════════════════════════╝

⚠️  AVANT DE LANCER:
1. Assure-toi que ton API tourne: uvicorn app.main:app --reload
2. Remplace TENANT_ID et CONVERSATION_ID dans ce script
3. Ajoute du contenu KB via /api/kb/quick_ingest

Scénarios disponibles:
1. Réservation complète (A→Z)
2. Handoff vers humain
3. Indisponibilité (hors heures)
4. FAQ simple
5. Message unique personnalisé

""")
    
    choice = input("Choisis un scénario (1-5): ").strip()
    
    if choice == "1":
        run_scenario_complete()
    elif choice == "2":
        run_scenario_handoff()
    elif choice == "3":
        run_scenario_unavailable()
    elif choice == "4":
        run_scenario_faq()
    elif choice == "5":
        msg = input("Ton message: ")
        test_agent(msg)
    else:
        print("❌ Choix invalide")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("✅ TESTS TERMINÉS")
    print("="*70)
