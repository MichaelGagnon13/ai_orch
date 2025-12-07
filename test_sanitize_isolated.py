#!/usr/bin/env python3
"""Test isolé de la fonction sanitize_for_studio"""

import math


def sanitize_for_studio(obj, max_str_len=200, max_int=2_147_483_647):
    """
    Nettoie récursivement les objets pour éviter 'Invalid array length' dans Studio.
    - Arrays → {"_array_length": N}
    - NaN/Inf → 0
    - Entiers > max_int → max_int
    - Chaînes > max_str_len → tronquées
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_studio(v, max_str_len, max_int) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return {"_array_length": len(obj)}
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0
        return obj
    elif isinstance(obj, int):
        return min(abs(obj), max_int) * (1 if obj >= 0 else -1)
    elif isinstance(obj, str):
        return obj[:max_str_len]
    else:
        return obj


print("=== TEST SANITIZE_FOR_STUDIO ===\n")

# Test 1: Arrays
print("✓ Test Arrays:")
result = sanitize_for_studio([1, 2, 3, 4, 5])
print("  Input: [1,2,3,4,5]")
print(f"  Output: {result}")
assert result == {"_array_length": 5}, "Array test failed"

# Test 2: Nested arrays
result = sanitize_for_studio({"data": [1, 2, 3], "items": ["a", "b"]})
print("  Input: dict with arrays")
print(f"  Output: {result}")
assert result == {
    "data": {"_array_length": 3},
    "items": {"_array_length": 2},
}, "Nested array test failed"

# Test 3: NaN
print("\n✓ Test NaN/Inf:")
result = sanitize_for_studio(float("nan"))
print("  Input: NaN")
print(f"  Output: {result}")
assert result == 0, "NaN test failed"

# Test 4: Inf
result = sanitize_for_studio(float("inf"))
print("  Input: Inf")
print(f"  Output: {result}")
assert result == 0, "Inf test failed"

# Test 5: -Inf
result = sanitize_for_studio(float("-inf"))
print("  Input: -Inf")
print(f"  Output: {result}")
assert result == 0, "-Inf test failed"

# Test 6: Big integers
print("\n✓ Test Big Integers:")
result = sanitize_for_studio(999_999_999_999)
print("  Input: 999_999_999_999")
print(f"  Output: {result}")
assert result == 2_147_483_647, "Big int test failed"

# Test 7: Negative big integers
result = sanitize_for_studio(-999_999_999_999)
print("  Input: -999_999_999_999")
print(f"  Output: {result}")
assert result == -2_147_483_647, "Negative big int test failed"

# Test 8: Long strings
print("\n✓ Test Long Strings:")
long_str = "x" * 300
result = sanitize_for_studio(long_str)
print("  Input: string with 300 chars")
print(f"  Output length: {len(result)} chars")
assert len(result) == 200, "Long string test failed"

# Test 9: Complex nested structure
print("\n✓ Test Complex Structure:")
complex_obj = {
    "array": [1, 2, 3, 4, 5],
    "nan_value": float("nan"),
    "big_int": 5_000_000_000,
    "long_text": "a" * 250,
    "nested": {"items": ["x", "y", "z"], "inf": float("inf")},
}
result = sanitize_for_studio(complex_obj)
print("  Input: complex nested structure")
print(f"  Output keys: {list(result.keys())}")

# Verify structure
assert result["array"] == {"_array_length": 5}, f"Array failed: {result['array']}"
assert result["nan_value"] == 0, f"NaN failed: {result['nan_value']}"
assert result["big_int"] == 2_147_483_647, f"Big int failed: {result['big_int']}"
assert len(result["long_text"]) == 200, f"Long text failed: {len(result['long_text'])}"
assert result["nested"]["items"] == {
    "_array_length": 3
}, f"Nested items failed: {result['nested']['items']}"
assert result["nested"]["inf"] == 0, f"Nested inf failed: {result['nested']['inf']}"

print("\n=== ✅ TOUS LES TESTS PASSÉS ===")
print("\n💡 La fonction sanitize_for_studio est prête pour SAFE_MODE!")
