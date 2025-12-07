#!/usr/bin/env python3
"""
TaskBot - Mini-outil CLI pour déléguer des tâches à Claude ou GPT
Usage: python taskbot.py "ta tâche ici"
"""

import os
import re
import subprocess
from pathlib import Path

try:
    import typer
    from anthropic import Anthropic
    from openai import OpenAI
except ImportError:
    print("❌ Dépendances manquantes. Installe avec:")
    print("   pip install anthropic openai typer")
    exit(1)

app = typer.Typer(help="🤖 TaskBot - Ton assistant CLI piloté par Claude & GPT")

# Configuration
CONTEXT_FILE = ".taskbot_context.txt"
MAX_CONTEXT_TASKS = 5

# Initialisation des clients API
claude_client = None
gpt_client = None


def init_clients():
    """Initialise les clients API si les clés existent"""
    global claude_client, gpt_client

    claude_key = os.getenv("ANTHROPIC_API_KEY")
    gpt_key = os.getenv("OPENAI_API_KEY")

    if claude_key:
        claude_client = Anthropic(api_key=claude_key)
    if gpt_key:
        gpt_client = OpenAI(api_key=gpt_key)


def load_context() -> str:
    """Charge le contexte des dernières tâches"""
    if not Path(CONTEXT_FILE).exists():
        return ""

    context = Path(CONTEXT_FILE).read_text(encoding="utf-8")

    # Garde seulement les N dernières tâches
    tasks = context.split("\n--- TASK ---\n")
    recent_tasks = tasks[-MAX_CONTEXT_TASKS:]

    return "\n--- TASK ---\n".join(recent_tasks)


def save_context(task: str, result: str):
    """Sauvegarde la tâche et le résultat pour le contexte futur"""
    context = load_context()

    new_entry = f"\n--- TASK ---\n{task}\n--- RESULT ---\n{result[:500]}...\n"

    Path(CONTEXT_FILE).write_text(context + new_entry, encoding="utf-8")


def build_prompt(task: str, agent: str, context: str) -> str:
    """Construit le prompt selon l'agent"""

    base_context = f"""Projet: ai_orch - Orchestration multi-agents avec AgentScope
Stack: Python 3.11+, AgentScope, APIs Claude/GPT

Contexte des tâches récentes:
{context if context else "Aucune tâche précédente"}

---"""

    if agent == "claude":
        return f"""{base_context}

Tu es l'expert Python/API du projet ai_orch.

Tâche à accomplir: {task}

Réponds en suivant EXACTEMENT ce format:

FILE: chemin/exact/du/fichier.py
```python
# Contenu complet et fonctionnel du fichier
# Avec commentaires clairs
```

VALIDATE: commande pour valider (pytest, python -m, etc.)

Règles:
- Code Python avec type hints
- Gestion d'erreurs propre
- Logs structurés
- Tests si pertinent
- JAMAIS de placeholders ou TODO
"""

    else:  # gpt
        return f"""{base_context}

Tu es l'expert DevOps/Config du projet ai_orch.

Tâche à accomplir: {task}

Réponds en suivant EXACTEMENT ce format:

FILE: chemin/exact/du/fichier
```bash
# Contenu complet et fonctionnel
```

VALIDATE: commande pour valider (docker build, etc.)

Règles:
- Scripts bash robustes avec error handling
- Configuration YAML/JSON bien structurée
- Dockerfiles optimisés
- JAMAIS de placeholders
"""


def ask_claude(task: str, context: str) -> str:
    """Appelle l'API Claude"""
    if not claude_client:
        return "❌ ANTHROPIC_API_KEY non configurée"

    prompt = build_prompt(task, "claude", context)

    try:
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        return f"❌ Erreur Claude API: {str(e)}"


def ask_gpt(task: str, context: str) -> str:
    """Appelle l'API GPT"""
    if not gpt_client:
        return "❌ OPENAI_API_KEY non configurée"

    prompt = build_prompt(task, "gpt", context)

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=8000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Erreur GPT API: {str(e)}"


def parse_files(response: str) -> list[tuple[str, str]]:
    """Extrait les fichiers à créer depuis la réponse"""
    # Pattern: FILE: path puis bloc de code
    pattern = r"FILE:\s*(\S+)\s*```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)

    files = []
    for filepath, content in matches:
        files.append((filepath.strip(), content.strip()))

    return files


def parse_validation(response: str) -> list[str]:
    """Extrait les commandes de validation"""
    pattern = r"VALIDATE:\s*(.+?)(?:\n|$)"
    commands = re.findall(pattern, response)
    return [cmd.strip() for cmd in commands if cmd.strip()]


def create_files(files: list[tuple[str, str]]):
    """Crée les fichiers sur le disque"""
    for filepath, content in files:
        path = Path(filepath)

        # Crée les dossiers parents si nécessaire
        path.parent.mkdir(parents=True, exist_ok=True)

        # Écrit le fichier
        path.write_text(content, encoding="utf-8")

        typer.echo(f"  ✓ Créé: {filepath}")


def run_validation(commands: list[str]):
    """Exécute les commandes de validation"""
    for cmd in commands:
        typer.echo(f"\n  $ {cmd}")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                typer.echo("    ✅ Validation OK")
                if result.stdout:
                    typer.echo(f"    {result.stdout.strip()}")
            else:
                typer.echo("    ❌ Validation échouée")
                if result.stderr:
                    typer.echo(f"    {result.stderr.strip()}")

        except subprocess.TimeoutExpired:
            typer.echo("    ⏱️  Timeout (>30s)")
        except Exception as e:
            typer.echo(f"    ❌ Erreur: {str(e)}")


@app.command()
def run(
    task: str = typer.Argument(..., help="La tâche à accomplir"),
    agent: str = typer.Option("claude", "--agent", "-a", help="Agent à utiliser: claude ou gpt"),
    auto: bool = typer.Option(False, "--auto", "-y", help="Exécute sans demander confirmation"),
    no_validate: bool = typer.Option(False, "--no-validate", help="Saute la validation"),
):
    """
    🤖 Exécute une tâche via Claude ou GPT

    Exemples:
      python taskbot.py "Crée config/agents.yaml"
      python taskbot.py -a gpt "Génère un Dockerfile"
      python taskbot.py --auto "Ajoute requirements.txt"
    """

    init_clients()

    # Vérifie que l'agent est disponible
    if agent == "claude" and not claude_client:
        typer.echo("❌ Claude non disponible. Configure ANTHROPIC_API_KEY", err=True)
        raise typer.Exit(1)

    if agent == "gpt" and not gpt_client:
        typer.echo("❌ GPT non disponible. Configure OPENAI_API_KEY", err=True)
        raise typer.Exit(1)

    # Affiche la configuration
    typer.echo(f"\n🤖 Agent: {agent.upper()}")
    typer.echo(f"📋 Tâche: {task}\n")

    # Charge le contexte
    context = load_context()

    # Appelle l'agent
    typer.echo("⏳ Génération en cours...\n")

    if agent == "claude":
        result = ask_claude(task, context)
    else:
        result = ask_gpt(task, context)

    # Affiche le résultat
    typer.echo("=" * 70)
    typer.echo(result)
    typer.echo("=" * 70 + "\n")

    # Parse les fichiers et commandes
    files = parse_files(result)
    validation_cmds = parse_validation(result)

    if not files:
        typer.echo("⚠️  Aucun fichier à créer détecté dans la réponse")
        save_context(task, result)
        return

    # Création des fichiers
    if auto or typer.confirm(f"\n📁 Créer {len(files)} fichier(s)?"):
        typer.echo("\n🚀 Création des fichiers...")
        create_files(files)
        typer.echo()
    else:
        typer.echo("⏭️  Création annulée")
        save_context(task, result)
        return

    # Validation
    if validation_cmds and not no_validate:
        if auto or typer.confirm(
            f"\n✅ Lancer la validation ({len(validation_cmds)} commande(s))?"
        ):
            run_validation(validation_cmds)
        else:
            typer.echo("⏭️  Validation ignorée")

    # Sauvegarde le contexte
    save_context(task, result)

    typer.echo("\n✨ Terminé!\n")


@app.command()
def clear():
    """🗑️  Efface le contexte sauvegardé"""
    if Path(CONTEXT_FILE).exists():
        Path(CONTEXT_FILE).unlink()
        typer.echo("✅ Contexte effacé")
    else:
        typer.echo("ℹ️  Aucun contexte à effacer")


@app.command()
def context():
    """📜 Affiche le contexte actuel"""
    ctx = load_context()
    if ctx:
        typer.echo("\n=== CONTEXTE ACTUEL ===\n")
        typer.echo(ctx)
    else:
        typer.echo("ℹ️  Pas de contexte sauvegardé")


@app.command()
def status():
    """🔍 Vérifie la configuration des APIs"""
    init_clients()

    typer.echo("\n=== STATUS TASKBOT ===\n")

    if claude_client:
        typer.echo("✅ Claude API: Configurée")
    else:
        typer.echo("❌ Claude API: ANTHROPIC_API_KEY manquante")

    if gpt_client:
        typer.echo("✅ GPT API: Configurée")
    else:
        typer.echo("❌ GPT API: OPENAI_API_KEY manquante")

    if Path(CONTEXT_FILE).exists():
        tasks_count = load_context().count("--- TASK ---")
        typer.echo(f"\n📜 Contexte: {tasks_count} tâche(s) sauvegardée(s)")
    else:
        typer.echo("\n📜 Contexte: Vide")

    typer.echo()


if __name__ == "__main__":
    app()
