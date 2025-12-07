import json


def _payload(content):
    if (
        isinstance(content, list)
        and content
        and isinstance(content[0], dict)
        and content[0].get("type") == "text"
    ):
        try:
            return json.loads(content[0]["text"])
        except Exception:
            return content[0]["text"]
    return content


#!/usr/bin/env python3
"""Test du wrapper Msg avec SAFE_MODE activé"""

import os
import sys

# Activer SAFE_MODE AVANT d'importer
os.environ["AS_STUDIO_SAFE_MODE"] = "1"


# Mock minimal d'AgentScope pour éviter les dépendances
class MockMsg:
    def __init__(self, name=None, role=None, content=None, **kwargs):
        self.name = name
        self.role = role
        self.content = content
        self.kwargs = kwargs

    def __repr__(self):
        return f"MockMsg(name={self.name}, role={self.role}, content_type={type(self.content).__name__})"


# Remplacer agentscope par le mock
sys.modules["agentscope"] = type(
    "MockModule",
    (),
    {
        "init": lambda *args, **kwargs: None,
        "message": type("MessageModule", (), {"Msg": MockMsg})(),
    },
)()
sys.modules["agentscope.message"] = sys.modules["agentscope"].message
sys.modules["agentscope.agent"] = type("AgentModule", (), {"ReActAgent": type})()
sys.modules["agentscope.model"] = type(
    "ModelModule", (), {"OpenAIChatModel": type, "AnthropicChatModel": type}
)()
sys.modules["agentscope.formatter"] = type(
    "FormatterModule", (), {"OpenAIChatFormatter": type, "AnthropicChatFormatter": type}
)()

# Maintenant on peut importer
from src.orchestrate import SAFE_MODE, Msg

print("=== TEST SAFE_MODE WRAPPER ===\n")
print(f"SAFE_MODE activé: {SAFE_MODE}")
assert SAFE_MODE == True, "SAFE_MODE should be True"

# Test 1: Msg avec array dans content
print("\n✓ Test 1: Msg avec array")
msg = Msg(name="test", role="user", content=[1, 2, 3, 4, 5])
print("  Input content: [1,2,3,4,5]")
print(f"  Sanitized content: {msg.content}")
assert _payload(msg.content) == {
    "_array_length": 5
}, f'Expected {{"_array_length": 5}}, got {msg.content}'

# Test 2: Msg avec dict contenant arrays
print("\n✓ Test 2: Msg avec dict + arrays")
msg = Msg(name="test", role="user", content={"data": [1, 2, 3], "text": "hello"})
print("  Input: dict with array")
print(f"  Sanitized: {msg.content}")
assert _payload(msg.content) == {"data": {"_array_length": 3}, "text": "hello"}

# Test 3: Msg avec string longue
print("\n✓ Test 3: Msg avec string longue")
long_text = "x" * 300
msg = Msg(name="test", role="user", content=long_text)
print("  Input: 300 chars")
print(f"  Output: {len(msg.content)} chars")
assert len(msg.content) == 200

# Test 4: Msg avec NaN/Inf
print("\n✓ Test 4: Msg avec NaN/Inf")
msg = Msg(name="test", role="user", content={"nan": float("nan"), "inf": float("inf")})
print("  Input: NaN and Inf")
print(f"  Sanitized: {msg.content}")
assert _payload(msg.content) == {"nan": 0, "inf": 0}

# Test 5: Msg avec gros entier
print("\n✓ Test 5: Msg avec gros entier")
msg = Msg(name="test", role="user", content=999_999_999_999)
print("  Input: 999_999_999_999")
print(f"  Sanitized: {msg.content}")
assert _payload(msg.content) == 2_147_483_647

# Test 6: Structure complexe réaliste
print("\n✓ Test 6: Structure complexe (cas réel)")
complex_content = {
    "prompt": "x" * 500,  # Long prompt
    "history": [  # Array d'historique
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ],
    "metadata": {
        "tokens": 999_999_999,  # Gros nombre
        "temperature": float("nan"),  # NaN
        "items": ["a", "b", "c"] * 100,  # Long array
    },
}
msg = Msg(name="test", role="user", content=complex_content)
print("  Input: complex nested structure")
print(f'  Sanitized prompt length: {len(_payload(msg.content)["prompt"])} chars')
print(f'  Sanitized history: {_payload(msg.content)["history"]}')
print(f'  Sanitized tokens: {_payload(msg.content)["metadata"]["tokens"]}')
print(f'  Sanitized temperature: {_payload(msg.content)["metadata"]["temperature"]}')
print(f'  Sanitized items: {_payload(msg.content)["metadata"]["items"]}')

assert len(_payload(msg.content)["prompt"]) == 200
assert _payload(msg.content)["history"] == {"_array_length": 2}
assert _payload(msg.content)["metadata"]["tokens"] == 999999999
assert _payload(msg.content)["metadata"]["temperature"] == 0
assert _payload(msg.content)["metadata"]["items"] == {"_array_length": 300}

print("\n=== ✅ TOUS LES TESTS DU WRAPPER PASSÉS ===")
print("\n💡 Le wrapper Msg sanitize automatiquement avec SAFE_MODE=1!")
print('💡 Plus d\'erreur "Invalid array length" possible!')
