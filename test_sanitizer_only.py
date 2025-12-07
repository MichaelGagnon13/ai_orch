#!/usr/bin/env python3
"""Test de la fonction _ultra_sanitize isolée"""

import json


def _ultra_sanitize(data):
    """Converts all arrays to scalars, caps values, truncates text"""
    if not isinstance(data, dict):
        return data

    result = {}
    for k, v in data.items():
        # Recursively sanitize nested dicts
        if isinstance(v, dict):
            result[k] = _ultra_sanitize(v)

        # Convert arrays to count/length scalar
        elif isinstance(v, list):
            result[f"{k}_count"] = min(len(v), 1_000_000)

        # Handle numbers
        elif isinstance(v, (int, float)):
            # Detect NaN/Inf
            if v != v or v == float("inf") or v == float("-inf"):
                result[k] = 0
            # Cost fields -> cents (int)
            elif "cost" in k.lower():
                result[k] = int(min(abs(v * 100), 999_999_999))
            # Token fields -> capped int
            elif "token" in k.lower():
                result[k] = int(min(abs(v), 1_000_000))
            # Timestamps -> int
            elif any(x in k.lower() for x in ["time", "ts", "timestamp"]):
                result[k] = int(min(abs(v), 2**31 - 1))
            else:
                result[k] = int(min(abs(v), 2**31 - 1))

        # Truncate strings
        elif isinstance(v, str):
            result[k] = v[:200]

        else:
            result[k] = v

    return result


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

print("=== DONNÉES AVANT SANITIZATION ===")
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
errors = []
for k, v in sanitized.items():
    if isinstance(v, list):
        errors.append(f"❌ {k}: encore un array! length={len(v)}")
    elif isinstance(v, (int, float)):
        if v != v:
            errors.append(f"❌ {k}: encore NaN!")
        elif v == float("inf") or v == float("-inf"):
            errors.append(f"❌ {k}: encore Infinity!")
        elif abs(v) > 2**31 - 1:
            errors.append(f"❌ {k}: valeur trop grande ({v})")
        else:
            print(f"✅ {k}: {v} (safe)")
    elif isinstance(v, str):
        if len(v) > 200:
            errors.append(f"❌ {k}: texte trop long ({len(v)} chars)")
        else:
            print(f"✅ {k}: '{v[:50]}...' ({len(v)} chars)")
    elif isinstance(v, dict):
        print(f"✅ {k}: dict (nested)")
    else:
        print(f"✅ {k}: {type(v).__name__}")

if errors:
    print("\n❌ ERREURS TROUVÉES:")
    for err in errors:
        print(f"  {err}")
else:
    print("\n✅ TOUTES LES DONNÉES SONT SAFE!")
