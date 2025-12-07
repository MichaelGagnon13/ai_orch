#!/usr/bin/env python3
"""Crée un run propre sans données problématiques"""

import os

os.environ["AS_STUDIO_SAFE_MODE"] = "1"  # ACTIVER AVANT import

import sys

sys.path.insert(0, os.path.dirname(__file__))

# Maintenant importer orchestrate qui va activer les patches
print("🔧 Activation SAFE_MODE...")
exec(open("src/orchestrate.py").read().split("# === logger:")[0])

print("\n✅ SAFE_MODE activé!")
print("✅ Tous les arrays/NaN/Inf seront filtrés")
print("\n🌐 Ouvrez cette URL dans Chrome:")
print("   http://127.0.0.1:3000/dashboard/projects/ai_orch")
print("\n⚠️  NE PAS ouvrir le run 5C4BAErUd7yWUeivkXQ4dZ (il est corrompu)")
print("   Utilisez uniquement les NOUVEAUX runs créés après maintenant\n")

# Créer un message de test propre
import time

from agentscope.message import Msg

msg = Msg(
    name="system",
    role="assistant",
    content="✅ Run propre créé avec SAFE_MODE. Aucune donnée problématique.",
    metadata={"test": True, "safe_mode": True},
)

print(f"📝 Message créé: {msg.id}")
print(f"   Content: {msg.content}")

# Attendre que le Studio reçoive les données
time.sleep(2)

print("\n✅ TERMINÉ - Le Studio devrait maintenant fonctionner sans erreur!")
