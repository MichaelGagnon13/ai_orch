#!/usr/bin/env python3
"""Test d'envoi de données au Studio avec SAFE_MODE"""

import os

os.environ["AS_STUDIO_SAFE_MODE"] = "1"
os.environ["AS_STUDIO_URL"] = "http://127.0.0.1:3000"
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-dummy")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "sk-ant-dummy")
os.environ["ANTHROPIC_MODEL_ID"] = "claude-3-5-sonnet-20241022"

# Import sanitizer
import sys

from agentscope.message import Msg

sys.path.insert(0, os.path.dirname(__file__))

# Initialiser AgentScope avec SAFE_MODE
from src.studio_sanitizer import safe_agentscope_init

safe_agentscope_init(project="ai_orch", name="test_safe", studio_url="http://127.0.0.1:3000")

print("✅ Studio connecté avec SAFE_MODE=1")
print("🌐 Ouvrez http://127.0.0.1:3000/dashboard/projects/ai_orch")

# Créer un message simple (pas besoin d'appeler de vrais modèles)
msg = Msg(
    name="test", role="assistant", content="Test SAFE_MODE - aucun array ne doit causer d'erreur JS"
)

print(f"\n✅ Message créé: {msg.content[:50]}...")
print("\n⏸️  Attendez 3 secondes puis vérifiez le Studio...")

import time

time.sleep(3)

print("✅ Test terminé. Le Studio devrait afficher le run sans erreur 'Invalid array length'")
