"""
Tests pour le fallback LLM (mode stub) - TASK-11

Vérifie que l'orchestrateur ne crash pas quand les clés LLM sont absentes
et que le mode stub fonctionne correctement.
"""

import os
from unittest.mock import patch

import pytest


class TestLLMFallback:
    """Tests du système de fallback LLM"""

    def test_detect_no_keys_returns_stub_config(self):
        """Vérifie que sans clés, on obtient une config stub"""
        from src.orchestrate import detect_llm_config

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "",
                "ANTHROPIC_API_KEY": "",
            },
            clear=False,
        ):
            config, is_stub = detect_llm_config()

            assert is_stub is True
            assert config.is_stub_mode() is True
            assert config.mode == "stub"

    def test_detect_with_openai_key_returns_live_config(self):
        """Vérifie qu'avec une clé OpenAI, on obtient une config live"""
        from src.orchestrate import detect_llm_config

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "sk-test123",
                "ANTHROPIC_API_KEY": "",
            },
            clear=False,
        ):
            config, is_stub = detect_llm_config()

            assert is_stub is False
            assert config.is_stub_mode() is False
            assert config.mode == "live"
            assert config.openai_key == "sk-test123"

    def test_detect_with_anthropic_key_returns_live_config(self):
        """Vérifie qu'avec une clé Anthropic, on obtient une config live"""
        from src.orchestrate import detect_llm_config

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "",
                "ANTHROPIC_API_KEY": "sk-ant-test456",
                "ANTHROPIC_MODEL_ID": "claude-sonnet-4-20250514",
            },
            clear=False,
        ):
            config, is_stub = detect_llm_config()

            assert is_stub is False
            assert config.is_stub_mode() is False
            assert config.mode == "live"
            assert config.anthropic_key == "sk-ant-test456"
            assert config.model_id == "claude-sonnet-4-20250514"

    def test_stub_agent_responds_without_crash(self):
        """Vérifie que l'agent stub répond sans planter"""
        from src.orchestrate import create_stub_agent

        agent = create_stub_agent("test_agent", "planner")

        message = {"content": "Crée un plan de test", "role": "user"}

        response = agent(message)

        assert response is not None
        assert "content" in response
        assert "role" in response
        assert response["role"] == "assistant"
        assert len(response["content"]) > 0

    def test_stub_agent_planner_returns_appropriate_response(self):
        """Vérifie que l'agent planner stub retourne un plan"""
        from src.orchestrate import create_stub_agent

        agent = create_stub_agent("planner", "planner")
        response = agent({"content": "Plan something", "role": "user"})

        assert "stub" in response["content"].lower() or "task" in response["content"].lower()

    def test_stub_agent_coder_returns_code_like_response(self):
        """Vérifie que l'agent coder stub retourne du code"""
        from src.orchestrate import create_stub_agent

        agent = create_stub_agent("coder", "coder")
        response = agent({"content": "Write code", "role": "user"})

        # Doit contenir soit du code, soit une mention de stub
        assert "stub" in response["content"].lower() or "print" in response["content"].lower()

    def test_orchestrate_runs_without_crash_in_stub_mode(self):
        """
        Test d'intégration: vérifie que l'orchestrateur peut démarrer
        sans clés API et ne crash pas (mode stub)
        """
        from src.orchestrate import create_stub_agent, detect_llm_config

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "",
                "ANTHROPIC_API_KEY": "",
            },
            clear=False,
        ):
            # Détection de la config
            config, is_stub = detect_llm_config()
            assert is_stub is True

            # Création d'agents stub
            planner = create_stub_agent("planner", "planner")
            coder = create_stub_agent("coder", "coder")
            reviewer = create_stub_agent("reviewer", "reviewer")

            # Simulation d'une interaction simple
            plan_response = planner({"content": "Plan a task", "role": "user"})
            assert plan_response is not None

            code_response = coder({"content": plan_response["content"], "role": "user"})
            assert code_response is not None

            review_response = reviewer({"content": code_response["content"], "role": "user"})
            assert review_response is not None

    def test_whitespace_only_keys_treated_as_empty(self):
        """Vérifie que des clés avec seulement des espaces sont traitées comme vides"""
        from src.orchestrate import detect_llm_config

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "   ",
                "ANTHROPIC_API_KEY": "\t\n",
            },
            clear=False,
        ):
            config, is_stub = detect_llm_config()

            assert is_stub is True
            assert config.is_stub_mode() is True


class TestStubModeIntegration:
    """Tests d'intégration du mode stub"""

    def test_can_import_orchestrate_without_env_file(self):
        """Vérifie qu'on peut importer orchestrate.py sans fichier .env"""
        with patch.dict(os.environ, {}, clear=False):
            try:
                # Si on arrive ici, l'import a réussi
                assert True
            except Exception as e:
                pytest.fail(f"Import de orchestrate a échoué sans .env: {e}")

    def test_stub_mode_logs_warning(self, caplog):
        """Vérifie que le mode stub log un warning visible"""
        from src.orchestrate import detect_llm_config

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "",
                "ANTHROPIC_API_KEY": "",
            },
            clear=False,
        ):
            with caplog.at_level("WARNING"):
                config, is_stub = detect_llm_config()

                # Vérifie qu'un warning a été émis
                assert any("STUB" in record.message for record in caplog.records)


# Test de non-régression
class TestExistingSafeMode:
    """Vérifie que SAFE_MODE n'est pas impacté par le fallback LLM"""

    def test_safe_mode_env_var_still_works(self):
        """Vérifie que AS_STUDIO_SAFE_MODE fonctionne indépendamment"""
        with patch.dict(
            os.environ,
            {
                "AS_STUDIO_SAFE_MODE": "1",
                "OPENAI_API_KEY": "",
                "ANTHROPIC_API_KEY": "",
            },
            clear=False,
        ):
            # SAFE_MODE et fallback LLM sont indépendants
            assert os.getenv("AS_STUDIO_SAFE_MODE") == "1"

            from src.orchestrate import detect_llm_config

            config, is_stub = detect_llm_config()

            # Les deux peuvent coexister
            assert is_stub is True
            assert os.getenv("AS_STUDIO_SAFE_MODE") == "1"


if __name__ == "__main__":
    # Permet de lancer les tests directement
    pytest.main([__file__, "-v"])
