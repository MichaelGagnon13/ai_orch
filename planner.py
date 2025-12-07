#!/usr/bin/env python3
"""
Planner Agent - Décompose une mission en tâches exécutables
Utilise GPT-5.1 (économique) pour la planification
"""

import json
import os
import subprocess
from pathlib import Path

try:
    import typer
    from openai import OpenAI
except ImportError:
    print("❌ pip install openai typer")
    exit(1)

app = typer.Typer(help="🧠 Planner - Décompose missions en tâches")

# Client GPT
gpt_client = None


def init_client():
    global gpt_client
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        gpt_client = OpenAI(api_key=api_key)


PLANNER_PROMPT = """Tu es un architecte logiciel expert. Ton rôle est de décomposer une mission en tâches concrètes et exécutables.

MISSION: {mission}

Analyse cette mission et retourne un plan JSON avec ce format EXACT:
```json
{{
  "mission": "résumé court de la mission",
  "tasks": [
    {{
      "id": 1,
      "name": "nom_court_tache",
      "description": "Ce que TaskBot doit faire exactement",
      "prompt": "Prompt complet pour TaskBot avec FILE: et code attendu",
      "depends_on": [],
      "validation": "commande pour valider (pytest, python, etc.)"
    }}
  ],
  "estimated_files": ["liste", "des", "fichiers", "créés"],
  "risks": ["risques potentiels"]
}}
```

RÈGLES:
1. Chaque tâche doit être autonome et testable
2. Le "prompt" doit contenir les instructions COMPLÈTES pour TaskBot
3. Ordre logique: dépendances d'abord
4. Maximum 5 tâches pour une mission simple
5. Sois CONCRET: noms de fichiers, fonctions, etc.

Retourne UNIQUEMENT le JSON, rien d'autre."""


def plan_mission(mission: str) -> dict:
    """Génère un plan de tâches pour une mission"""
    if not gpt_client:
        return {"error": "OPENAI_API_KEY non configurée"}

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": PLANNER_PROMPT.format(mission=mission)}],
            max_completion_tokens=4000,
        )

        content = response.choices[0].message.content

        # Extraire le JSON
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content

        return json.loads(json_str.strip())

    except json.JSONDecodeError as e:
        return {"error": f"JSON invalide: {e}", "raw": content}
    except Exception as e:
        return {"error": str(e)}


@app.command()
def plan(
    mission: str = typer.Argument(..., help="La mission à planifier"),
    execute: bool = typer.Option(
        False, "--execute", "-x", help="Exécuter les tâches après planification"
    ),
    save: bool = typer.Option(True, "--save/--no-save", help="Sauvegarder le plan"),
):
    """
    🧠 Planifie une mission en tâches exécutables

    Exemples:
      python planner.py plan "Crée une API Flask avec endpoint /status"
      python planner.py plan --execute "Ajoute un système de cache Redis"
    """
    init_client()

    typer.echo(f"\n🎯 Mission: {mission}")
    typer.echo("⏳ Planification en cours (GPT-5.1)...\n")

    result = plan_mission(mission)

    if "error" in result:
        typer.echo(f"❌ Erreur: {result['error']}", err=True)
        if "raw" in result:
            typer.echo(f"Réponse brute:\n{result['raw'][:500]}")
        raise typer.Exit(1)

    # Affiche le plan
    typer.echo("=" * 60)
    typer.echo(f"📋 PLAN: {result.get('mission', 'N/A')}")
    typer.echo("=" * 60)

    tasks = result.get("tasks", [])
    for task in tasks:
        deps = f" (après: {task.get('depends_on', [])})" if task.get("depends_on") else ""
        typer.echo(f"\n📌 Tâche {task['id']}: {task['name']}{deps}")
        typer.echo(f"   {task['description']}")
        typer.echo(f"   ✅ Validation: {task.get('validation', 'N/A')}")

    typer.echo(f"\n📁 Fichiers prévus: {result.get('estimated_files', [])}")

    if result.get("risks"):
        typer.echo(f"⚠️  Risques: {result.get('risks', [])}")

    # Sauvegarde
    if save:
        plan_file = Path("plans") / f"plan_{mission[:30].replace(' ', '_')}.json"
        plan_file.parent.mkdir(exist_ok=True)
        plan_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        typer.echo(f"\n💾 Plan sauvé: {plan_file}")

    # Exécution
    if execute:
        typer.echo("\n" + "=" * 60)
        typer.echo("🚀 EXÉCUTION DES TÂCHES")
        typer.echo("=" * 60)

        for task in tasks:
            typer.echo(f"\n--- Tâche {task['id']}: {task['name']} ---")

            if typer.confirm("Exécuter cette tâche?"):
                prompt = task.get("prompt", task["description"])

                # Appelle TaskBot
                cmd = ["python3", "taskbot.py", "run", "--auto", prompt]
                subprocess.run(cmd)
            else:
                typer.echo("⏭️  Ignorée")

    typer.echo("\n✨ Planification terminée!\n")


@app.command()
def show(plan_file: str = typer.Argument(..., help="Fichier plan JSON")):
    """📄 Affiche un plan sauvegardé"""
    path = Path(plan_file)
    if not path.exists():
        path = Path("plans") / plan_file

    if not path.exists():
        typer.echo(f"❌ Plan non trouvé: {plan_file}")
        raise typer.Exit(1)

    plan = json.loads(path.read_text())
    typer.echo(json.dumps(plan, indent=2, ensure_ascii=False))


@app.command()
def execute(plan_file: str = typer.Argument(..., help="Fichier plan JSON à exécuter")):
    """🚀 Exécute un plan sauvegardé"""
    path = Path(plan_file)
    if not path.exists():
        path = Path("plans") / plan_file

    if not path.exists():
        typer.echo(f"❌ Plan non trouvé: {plan_file}")
        raise typer.Exit(1)

    plan = json.loads(path.read_text())
    tasks = plan.get("tasks", [])

    typer.echo(f"\n🚀 Exécution de {len(tasks)} tâches\n")

    for task in tasks:
        typer.echo(f"--- Tâche {task['id']}: {task['name']} ---")

        if typer.confirm("Exécuter?"):
            prompt = task.get("prompt", task["description"])
            subprocess.run(["python3", "taskbot.py", "run", "--auto", prompt])
        else:
            typer.echo("⏭️  Ignorée")


if __name__ == "__main__":
    app()
