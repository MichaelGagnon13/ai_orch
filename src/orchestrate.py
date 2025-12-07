"""
MODIFICATIONS POUR src/orchestrate.py - Fallback LLM (TASK-11)

Ajouter ce code AU DÉBUT du fichier, après les imports:
"""

import logging
import os
from typing import Optional

# Configuration du logger
logger = logging.getLogger(__name__)

# ============================================================================
# FALLBACK LLM - Mode Stub Offline
# ============================================================================


class StubLLMConfig:
    """Configuration pour le mode stub (sans clés API)"""

    def __init__(self):
        self.mode = "stub"
        self.openai_key = None
        self.anthropic_key = None
        self.model_id = "stub-model"

    def is_stub_mode(self) -> bool:
        return True


class LiveLLMConfig:
    """Configuration pour le mode live (avec clés API)"""

    def __init__(self, openai_key: Optional[str], anthropic_key: Optional[str], model_id: str):
        self.mode = "live"
        self.openai_key = openai_key
        self.anthropic_key = anthropic_key
        self.model_id = model_id

    def is_stub_mode(self) -> bool:
        return False


def detect_llm_config() -> tuple[StubLLMConfig | LiveLLMConfig, bool]:
    """
    Détecte si les clés LLM sont disponibles et retourne la config appropriée.

    Returns:
        tuple[Config, is_stub]: Configuration et flag indiquant si en mode stub
    """
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    model_id = os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-20250514").strip()

    # Vérifier si au moins une clé est présente et non vide
    has_keys = bool(openai_key or anthropic_key)

    if not has_keys:
        logger.warning("=" * 60)
        logger.warning("⚠️  MODE STUB ACTIVÉ")
        logger.warning("Aucune clé LLM détectée (OPENAI_API_KEY, ANTHROPIC_API_KEY vides)")
        logger.warning("L'orchestrateur fonctionnera avec des réponses fixes")
        logger.warning("Pour utiliser de vrais LLMs, configurez .env avec vos clés")
        logger.warning("=" * 60)
        return StubLLMConfig(), True
    else:
        logger.info("✓ Clés LLM détectées, mode live activé")
        logger.info(f"  - OpenAI: {'✓' if openai_key else '✗'}")
        logger.info(f"  - Anthropic: {'✓' if anthropic_key else '✗'}")
        logger.info(f"  - Model: {model_id}")
        return LiveLLMConfig(openai_key, anthropic_key, model_id), False


def create_stub_agent(name: str, role: str):
    """
    Crée un agent stub qui retourne des réponses fixes.
    Utilisé quand les clés LLM ne sont pas disponibles.
    """

    class StubAgent:
        def __init__(self, name: str, role: str):
            self.name = name
            self.role = role

        def __call__(self, message: dict) -> dict:
            """Retourne une réponse stub basée sur le rôle"""
            logger.debug(f"[STUB] {self.name} reçoit: {message.get('content', '')[:100]}...")

            if self.role == "planner":
                response = {
                    "content": "Plan stub: TASK-STUB créée pour démonstration",
                    "role": "assistant",
                    "name": self.name,
                }
            elif self.role == "coder":
                response = {
                    "content": "Code stub: print('Mode stub actif')",
                    "role": "assistant",
                    "name": self.name,
                }
            elif self.role == "reviewer":
                response = {
                    "content": "Review stub: Code accepté en mode stub",
                    "role": "assistant",
                    "name": self.name,
                }
            else:
                response = {
                    "content": f"Réponse stub de {self.name} ({self.role})",
                    "role": "assistant",
                    "name": self.name,
                }

            logger.debug(f"[STUB] {self.name} répond: {response['content'][:100]}...")
            return response

    return StubAgent(name, role)


# ============================================================================
# MODIFICATION DE LA FONCTION PRINCIPALE
# ============================================================================

"""
Dans la fonction principale de orchestrate.py (là où vous initialisez les agents),
remplacer:

    # Ancien code (exemple):
    planner = AnthropicAgent(name="planner", model="claude-sonnet-4", ...)
    coder = AnthropicAgent(name="coder", model="claude-sonnet-4", ...)

Par:

    # Nouveau code avec fallback:
    llm_config, is_stub = detect_llm_config()

    if is_stub:
        # Mode stub - agents factices
        planner = create_stub_agent("planner", "planner")
        coder = create_stub_agent("coder", "coder")
        reviewer = create_stub_agent("reviewer", "reviewer")
    else:
        # Mode live - vrais agents LLM
        planner = AnthropicAgent(
            name="planner",
            model=llm_config.model_id,
            api_key=llm_config.anthropic_key,
            ...
        )
        coder = AnthropicAgent(
            name="coder",
            model=llm_config.model_id,
            api_key=llm_config.anthropic_key,
            ...
        )
        reviewer = AnthropicAgent(
            name="reviewer",
            model=llm_config.model_id,
            api_key=llm_config.anthropic_key,
            ...
        )
"""

# ============================================================================
# EXEMPLE D'INTÉGRATION COMPLÈTE
# ============================================================================


def main():
    """Fonction principale avec fallback LLM intégré"""

    # Détection de la config LLM
    llm_config, is_stub = detect_llm_config()

    if is_stub:
        print("\n🟡 Démarrage en MODE STUB (développement sans clés API)")
        print("   Les agents retourneront des réponses fixes\n")
    else:
        print("\n🟢 Démarrage en MODE LIVE (avec clés API)")
        print(f"   Model: {llm_config.model_id}\n")

    try:
        # Votre code d'orchestration ici
        # Utilisez is_stub pour décider quel type d'agent créer

        if is_stub:
            # Agents stub
            agents = {
                "planner": create_stub_agent("planner", "planner"),
                "coder": create_stub_agent("coder", "coder"),
                "reviewer": create_stub_agent("reviewer", "reviewer"),
            }
        else:
            # Agents réels (votre code existant)
            # agents = create_real_agents(llm_config)
            pass

        # Reste de votre orchestration...

    except Exception as e:
        logger.error(f"Erreur dans l'orchestrateur: {e}", exc_info=True)
        if is_stub:
            logger.info("En mode stub, certaines erreurs sont attendues")
        raise


if __name__ == "__main__":
    main()
# --- test-compat exports (safe to keep) ---
import math

# expose SAFE_MODE si absent
if "SAFE_MODE" not in globals():
    SAFE_MODE = os.getenv("AS_STUDIO_SAFE_MODE", "1") == "1"


# sanitizer compatible avec les tests
def sanitize_for_studio(obj, max_str_len=200, max_int=2_147_483_647):
    if isinstance(obj, dict):
        return {k: sanitize_for_studio(v, max_str_len, max_int) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return {"_array_length": len(obj)}
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0
        return obj
    elif isinstance(obj, int):
        # borne sur 32 bits signés
        if obj > max_int:
            return max_int
        if obj < -max_int:
            return -max_int
        return obj
    elif isinstance(obj, str):
        return obj[:max_str_len]
    else:
        return obj


# ancien nom attendu par test_safe_mode.py
_ultra_sanitize = sanitize_for_studio

# exposer Msg depuis orchestrate.py (wrapper SAFE_MODE si possible)
try:
    from agentscope.message import Msg as _BaseMsg  # selon versions
except Exception:
    try:
        from agentscope.messages import Msg as _BaseMsg
    except Exception:

        class _BaseMsg:
            def __init__(self, *args, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)


if SAFE_MODE:
    _OrigBase = _BaseMsg

    class Msg(_OrigBase):
        def __init__(self, *args, **kwargs):
            if "content" in kwargs:
                kwargs["content"] = sanitize_for_studio(kwargs["content"])
            super().__init__(*args, **kwargs)

else:
    Msg = _BaseMsg
# --- end test-compat exports ---
# --- normalize content for AgentScope Msg ---
import json as _json


def _to_content_blocks_or_str(x):
    # 1) si déjà une chaîne -> OK
    if isinstance(x, str):
        return x
    # 2) si déjà des "content blocks" (liste de dicts avec 'type')
    if isinstance(x, list) and all(isinstance(i, dict) and "type" in i for i in x):
        return x
    # 3) fallback: on sérialise en texte compact
    try:
        txt = _json.dumps(x, ensure_ascii=False)
    except Exception:
        txt = str(x)
    return [{"type": "text", "text": txt}]


# (ré)expose Msg en normalisant toujours le content après sanitize
try:
    from agentscope.message import Msg as _ASMsg
except Exception:
    try:
        from agentscope.messages import Msg as _ASMsg
    except Exception:

        class _ASMsg:
            def __init__(self, *args, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)


_OrigASMsg = _ASMsg


class Msg(_OrigASMsg):
    def __init__(self, *args, **kwargs):
        if "content" in kwargs:
            c = kwargs["content"]
            # sanitize si dispo
            try:
                c = sanitize_for_studio(c)
            except Exception:
                pass
            # normaliser pour AgentScope
            kwargs["content"] = _to_content_blocks_or_str(c)
        super().__init__(*args, **kwargs)


# --- end normalize patch ---
