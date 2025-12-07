#!/usr/bin/env python3
"""Test SAFE_MODE sanitization avec données problématiques"""

import os

os.environ["AS_STUDIO_SAFE_MODE"] = "1"
os.environ["AS_STUDIO_URL"] = "http://127.0.0.1:3000"

# Import après avoir défini les env vars
import sys

sys.path.insert(0, os.path.dirname(__file__))

import json

from src.orchestrate import SAFE_MODE, _ultra_sanitize

print(f"SAFE_MODE activé: {SAFE_MODE}")

# Données problématiques qui causeraient "Invalid array length"
test_data = {
    "huge_array": list(range(500_000)),  # Array énorme
    "tokens": 2**40,  # Nombre trop grand
    "cost_usd": float("inf"),  # Infinity
    "nan_value": float("nan"),  # NaN
    "negative_inf": float("-inf"),
    "timestamps": [1234567890] * 100_000,  # Array de timestamps
    "long_text": "x" * 10_000,  # Texte très long
    "nested": {"inner_array": list(range(1000)), "inner_cost": 123.456, "inner_tokens": 50_000},
}

print("\n=== DONNÉES AVANT SANITIZATION ===")
for k, v in test_data.items():
    if isinstance(v, list):
        print(f"{k}: array[{len(v)}]")
    elif isinstance(v, dict):
        print(f"{k}: dict{{{', '.join(v.keys())}}}")
    elif isinstance(v, str):
        print(f"{k}: str[{len(v)}]")
    else:
        print(f"{k}: {v}")

sanitized = _ultra_sanitize(test_data)

print("\n=== DONNÉES APRÈS SANITIZATION ===")
print(json.dumps(sanitized, indent=2))

print("\n=== VALIDATION ===")
for k, v in sanitized.items():
    if isinstance(v, list):
        print(f"❌ {k}: encore un array! length={len(v)}")
    elif isinstance(v, (int, float)):
        if v != v:
            print(f"❌ {k}: encore NaN!")
        elif v == float("inf") or v == float("-inf"):
            print(f"❌ {k}: encore Infinity!")
        elif abs(v) > 2**31 - 1:
            print(f"❌ {k}: valeur trop grande ({v})")
        else:
            print(f"✅ {k}: {v} (safe)")
    elif isinstance(v, str):
        if len(v) > 200:
            print(f"❌ {k}: texte trop long ({len(v)} chars)")
        else:
            print(f"✅ {k}: '{v[:50]}...' ({len(v)} chars)")
    elif isinstance(v, dict):
        print(f"✅ {k}: dict (nested)")
    else:
        print(f"✅ {k}: {type(v).__name__}")

print("\n✅ Test terminé - vérifiez http://127.0.0.1:3000")
