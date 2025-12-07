#!/usr/bin/env python3
"""
Mission VRAIMENT Autonome - 2h de travail continu
Les agents découvrent, analysent, créent, testent en boucle
"""

import json
import logging
import random
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/mission_autonomous.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class TrueAutonomousMission:
    """Mission autonome qui tourne vraiment pendant 2h"""

    def __init__(self, duration_hours=2):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=duration_hours)
        self.duration = duration_hours

        # Métriques
        self.discoveries = []
        self.analyses = []
        self.agents_created = []
        self.agents_tested = []
        self.cycle_count = 0

        # Configuration
        self.cycle_duration = 15 * 60  # 15 min par cycle
        self.min_cycle_gap = 60  # 1 min entre cycles

        logger.info("🚀 Mission autonome initialisée")
        logger.info(f"Début: {self.start_time}")
        logger.info(f"Fin prévue: {self.end_time}")
        logger.info(
            f"Cycles prévus: ~{(duration_hours * 60) // (self.cycle_duration/60 + self.min_cycle_gap/60)}"
        )

    def run(self):
        """Lance la mission autonome"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 DÉMARRAGE MISSION AUTONOME")
        logger.info("=" * 80)

        while datetime.now() < self.end_time:
            self.cycle_count += 1
            cycle_start = datetime.now()
            time_left = self.end_time - cycle_start

            logger.info(f"\n{'='*80}")
            logger.info(f"🔄 CYCLE {self.cycle_count}")
            logger.info(f"Temps restant: {time_left}")
            logger.info(f"{'='*80}")

            # Exécute un cycle complet
            self.run_cycle()

            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            logger.info(f"\n✅ Cycle {self.cycle_count} terminé en {cycle_duration:.0f}s")

            # Vérifie s'il reste assez de temps pour un autre cycle
            time_left = (self.end_time - datetime.now()).total_seconds()
            if time_left < (self.cycle_duration + self.min_cycle_gap):
                logger.info(f"⏰ Temps insuffisant pour cycle suivant ({time_left:.0f}s)")
                break

            # Pause entre cycles
            logger.info(f"💤 Pause {self.min_cycle_gap}s avant prochain cycle...")
            time.sleep(self.min_cycle_gap)

        # Rapport final
        logger.info("\n" + "=" * 80)
        logger.info("🏁 FIN DE MISSION")
        logger.info("=" * 80)
        self.generate_final_report()

    def run_cycle(self):
        """Exécute un cycle complet : découverte → analyse → action → test"""

        # Phase 1: DÉCOUVERTE (5 min)
        logger.info("\n--- PHASE 1/4: DÉCOUVERTE ---")
        discoveries = self.phase_discovery()

        # Phase 2: ANALYSE (3 min)
        logger.info("\n--- PHASE 2/4: ANALYSE ---")
        selected = self.phase_analysis(discoveries)

        # Phase 3: ACTION (5 min)
        logger.info("\n--- PHASE 3/4: CRÉATION ---")
        created = self.phase_action(selected)

        # Phase 4: TEST (2 min)
        logger.info("\n--- PHASE 4/4: VALIDATION ---")
        self.phase_validation(created)

    def phase_discovery(self) -> List[Dict]:
        """Phase 1: Découverte de projets et outils"""
        discoveries = []

        # 1. Scrape GitHub trending
        logger.info("🔍 Scan GitHub trending...")
        try:
            result = subprocess.run(
                ["python3", "tech_scout_v2.py"], capture_output=True, text=True, timeout=180
            )

            # Parse les rapports
            reports = sorted(Path("reports/tech_scout").glob("*.json"))
            if reports:
                with open(reports[-1]) as f:
                    data = json.load(f)
                    github_repos = data.get("github_trending", [])[:5]
                    discoveries.extend(github_repos)
                    logger.info(f"✅ GitHub: {len(github_repos)} repos trouvés")
        except Exception as e:
            logger.error(f"❌ Erreur GitHub scan: {e}")

        # 2. Ajoute projets AI agents connus
        known_projects = [
            {
                "name": "crewai",
                "description": "Framework for orchestrating role-playing AI agents",
                "url": "https://github.com/joaomdmoura/crewai",
                "stars": 25000,
                "relevance": "orchestration",
            },
            {
                "name": "autogen",
                "description": "Microsoft multi-agent conversation framework",
                "url": "https://github.com/microsoft/autogen",
                "stars": 32000,
                "relevance": "multi-agent",
            },
            {
                "name": "langchain",
                "description": "Building applications with LLMs through composability",
                "url": "https://github.com/langchain-ai/langchain",
                "stars": 95000,
                "relevance": "framework",
            },
            {
                "name": "semantic-kernel",
                "description": "Microsoft SDK for AI orchestration",
                "url": "https://github.com/microsoft/semantic-kernel",
                "stars": 21000,
                "relevance": "orchestration",
            },
        ]

        # Ajoute quelques projets aléatoires à chaque cycle
        sample = random.sample(known_projects, min(2, len(known_projects)))
        discoveries.extend(sample)

        logger.info(f"📊 Total découvertes: {len(discoveries)}")
        self.discoveries.extend(discoveries)

        return discoveries

    def phase_analysis(self, discoveries: List[Dict]) -> List[Dict]:
        """Phase 2: Analyse des découvertes avec Claude"""
        selected = []

        if not discoveries:
            logger.warning("⚠️ Aucune découverte à analyser")
            return selected

        logger.info(f"🧠 Analyse de {len(discoveries)} projets...")

        for i, project in enumerate(discoveries[:3], 1):  # Max 3 par cycle
            name = project.get("name", "Unknown")
            desc = project.get("description", "N/A")

            logger.info(f"\n[{i}/3] Analyse: {name}")

            # Prompt d'analyse
            prompt = f"""Analyse ce projet GitHub pour ai_orch:

Nom: {name}
Description: {desc}

Évalue:
1. Est-ce pertinent pour orchestration multi-agents?
2. Peut-on s'en inspirer pour créer un agent AgentScope?
3. Quel type d'agent créer?

Réponds UNIQUEMENT en JSON strict:
{{
    "pertinent": true ou false,
    "raison": "explication courte",
    "agent_type": "monitoring/orchestration/analysis/null",
    "agent_name": "nom_agent_a_creer",
    "priorite": 1-10
}}
"""

            try:
                # Analyse avec Claude via taskbot
                result = subprocess.run(
                    ["python3", "taskbot.py", "run", prompt],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                output = result.stdout.lower()

                # Parse simple (cherche "pertinent": true)
                if '"pertinent": true' in output or '"pertinent":true' in output:
                    project["analyzed"] = True
                    project["selected"] = True
                    selected.append(project)
                    logger.info(f"✅ SÉLECTIONNÉ: {name}")

                    # Extrait agent_name et type si possible
                    try:
                        # Cherche agent_name dans output
                        if '"agent_name"' in output:
                            import re

                            match = re.search(r'"agent_name"\s*:\s*"([^"]+)"', output)
                            if match:
                                project["agent_name"] = match.group(1)

                        if '"agent_type"' in output:
                            match = re.search(r'"agent_type"\s*:\s*"([^"]+)"', output)
                            if match:
                                project["agent_type"] = match.group(1)
                    except Exception:
                        pass
                else:
                    logger.info(f"⏭️ Ignoré: {name}")

                self.analyses.append(
                    {
                        "project": name,
                        "selected": project.get("selected", False),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except subprocess.TimeoutExpired:
                logger.warning(f"⏱️ Timeout analyse {name}")
            except Exception as e:
                logger.error(f"❌ Erreur analyse {name}: {e}")

        logger.info(f"\n🎯 {len(selected)} projet(s) sélectionné(s)")
        return selected

    def phase_action(self, selected: List[Dict]) -> List[Dict]:
        """Phase 3: Création d'agents basés sur sélection"""
        created = []

        if not selected:
            logger.info("⚠️ Aucun projet sélectionné, création agents génériques...")
            # Crée agents génériques si rien sélectionné
            selected = [
                {"name": f"agent_cycle_{self.cycle_count}", "agent_type": "monitoring"},
                {"name": f"tracker_cycle_{self.cycle_count}", "agent_type": "monitoring"},
            ]

        logger.info(f"⚡ Création de {len(selected)} agent(s)...")

        for i, project in enumerate(selected[:2], 1):  # Max 2 par cycle
            name = project.get("agent_name", project.get("name", f"agent_{self.cycle_count}_{i}"))
            agent_type = project.get("agent_type", "monitoring")

            # Nettoie le nom
            name = name.lower().replace("-", "_").replace(" ", "_")
            name = "".join(c for c in name if c.isalnum() or c == "_")

            logger.info(f"\n[{i}/{len(selected)}] Création: {name}")

            success = self.create_agent_file(name, agent_type, project)

            if success:
                created.append(
                    {
                        "name": name,
                        "type": agent_type,
                        "based_on": project.get("name"),
                        "status": "created",
                        "cycle": self.cycle_count,
                    }
                )
                self.agents_created.append(created[-1])
                logger.info(f"✅ Agent {name} créé")
            else:
                logger.error(f"❌ Échec création {name}")

            time.sleep(2)

        return created

    def create_agent_file(self, name: str, agent_type: str, project: Dict) -> bool:
        """Crée le fichier Python de l'agent"""

        class_name = "".join(word.capitalize() for word in name.split("_"))
        description = project.get("description", f"Agent {name}")

        # Template de code selon type
        if agent_type == "monitoring":
            code = f'''"""
Agent de monitoring: {name}
Basé sur: {project.get('name', 'N/A')}
Description: {description}
"""

from agentscope.agents import AgentBase
from datetime import datetime
import json

class {class_name}(AgentBase):
    """
    {description}
    """

    def __init__(self, name="{name}", **kwargs):
        super().__init__(name=name, **kwargs)
        self.metrics = {{}}
        self.history = []

    def reply(self, x=None):
        """Collecte et retourne métriques"""
        response = {{
            'agent': self.name,
            'type': '{agent_type}',
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics,
            'history_count': len(self.history),
            'status': 'active'
        }}

        self.history.append(response)
        return response

    def collect(self, metric_name: str, value):
        """Collecte une métrique"""
        self.metrics[metric_name] = {{
            'value': value,
            'timestamp': datetime.now().isoformat()
        }}
        logger.info(f"{{self.name}}: Metric {{metric_name}} = {{value}}")
        return {{'success': True, 'metric': metric_name}}

    def get_metrics(self) -> dict:
        """Retourne toutes les métriques"""
        return self.metrics

    def reset(self):
        """Réinitialise les métriques"""
        self.metrics = {{}}
        return {{'success': True}}

if __name__ == "__main__":
    # Test
    agent = {class_name}()
    print(f"✅ Agent {{agent.name}} initialisé")
    print(json.dumps(agent.reply(), indent=2))

    agent.collect('test_metric', 42)
    print(f"Métriques: {{agent.get_metrics()}}")
'''

        elif agent_type == "orchestration":
            code = f'''"""
Agent d'orchestration: {name}
Basé sur: {project.get('name', 'N/A')}
Description: {description}
"""

from agentscope.agents import AgentBase
from datetime import datetime
import json

class {class_name}(AgentBase):
    """
    {description}
    """

    def __init__(self, name="{name}", **kwargs):
        super().__init__(name=name, **kwargs)
        self.delegations = []
        self.optimizations = []

    def reply(self, x=None):
        """Orchestre et coordonne"""
        return {{
            'agent': self.name,
            'type': '{agent_type}',
            'timestamp': datetime.now().isoformat(),
            'delegations': len(self.delegations),
            'optimizations': len(self.optimizations),
            'status': 'active'
        }}

    def delegate(self, task: str, agents: list):
        """Délègue tâche aux agents"""
        delegation = {{
            'task': task,
            'agents': agents,
            'timestamp': datetime.now().isoformat(),
            'assigned_to': agents[0] if agents else None
        }}

        self.delegations.append(delegation)
        return delegation

    def optimize(self, task: str, options: list):
        """Optimise le choix parmi options"""
        # Logique simple: score basique
        scores = {{opt: len(str(opt)) for opt in options}}
        best = max(options, key=lambda x: scores.get(x, 0)) if options else None

        optimization = {{
            'task': task,
            'options': options,
            'selected': best,
            'timestamp': datetime.now().isoformat()
        }}

        self.optimizations.append(optimization)
        return best

if __name__ == "__main__":
    # Test
    agent = {class_name}()
    print(f"✅ Agent {{agent.name}} initialisé")
    print(json.dumps(agent.reply(), indent=2))

    result = agent.optimize('test_task', ['option1', 'option2', 'option3'])
    print(f"Optimisation: {{result}}")
'''

        else:  # analysis ou autre
            code = f'''"""
Agent d'analyse: {name}
Basé sur: {project.get('name', 'N/A')}
Description: {description}
"""

from agentscope.agents import AgentBase
from datetime import datetime

class {class_name}(AgentBase):
    """
    {description}
    """

    def __init__(self, name="{name}", **kwargs):
        super().__init__(name=name, **kwargs)
        self.analyses = []

    def reply(self, x=None):
        """Analyse et retourne résultat"""
        return {{
            'agent': self.name,
            'type': '{agent_type}',
            'timestamp': datetime.now().isoformat(),
            'analyses_count': len(self.analyses),
            'status': 'active'
        }}

    def analyze(self, data):
        """Analyse des données"""
        analysis = {{
            'data': str(data)[:100],
            'length': len(str(data)),
            'timestamp': datetime.now().isoformat(),
            'result': 'analyzed'
        }}

        self.analyses.append(analysis)
        return analysis

if __name__ == "__main__":
    # Test
    agent = {class_name}()
    print(f"✅ Agent {{agent.name}} initialisé")
    print(agent.reply())
'''

        # Crée le fichier
        try:
            agent_dir = Path("agentscope_agents")
            agent_dir.mkdir(exist_ok=True)

            agent_file = agent_dir / f"{name}.py"

            with open(agent_file, "w", encoding="utf-8") as f:
                f.write(code)

            if agent_file.exists():
                size = agent_file.stat().st_size
                logger.info(f"📝 Fichier créé: {agent_file} ({size} octets)")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"❌ Erreur création fichier: {e}")
            return False

    def phase_validation(self, created: List[Dict]):
        """Phase 4: Validation des agents créés"""

        if not created:
            logger.info("⚠️ Aucun agent à valider")
            return

        logger.info(f"🧪 Validation de {len(created)} agent(s)...")

        validated = 0

        for agent in created:
            name = agent["name"]
            agent_file = Path(f"agentscope_agents/{name}.py")

            if not agent_file.exists():
                logger.warning(f"⚠️ {name}: fichier non trouvé")
                continue

            logger.info(f"🧪 Test: {name}")

            try:
                # Test 1: Syntaxe Python
                with open(agent_file) as f:
                    code = f.read()
                    compile(code, agent_file, "exec")

                # Test 2: Import
                result = subprocess.run(
                    ["python3", str(agent_file)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=Path.cwd(),
                )

                if result.returncode == 0 and "✅" in result.stdout:
                    agent["status"] = "validated"
                    validated += 1
                    self.agents_tested.append(agent)
                    logger.info(f"✅ {name}: VALIDÉ")
                else:
                    logger.warning(f"⚠️ {name}: Test échoué")
                    if result.stderr:
                        logger.debug(f"Stderr: {result.stderr[:200]}")

            except SyntaxError as e:
                logger.error(f"❌ {name}: Erreur syntaxe - {e}")
            except subprocess.TimeoutExpired:
                logger.warning(f"⏱️ {name}: Timeout")
            except Exception as e:
                logger.error(f"❌ {name}: Erreur - {e}")

        logger.info(f"\n✅ {validated}/{len(created)} agent(s) validé(s) ce cycle")

    def generate_final_report(self):
        """Génère rapport final détaillé"""

        duration = datetime.now() - self.start_time
        total_created = len(self.agents_created)
        total_validated = len([a for a in self.agents_created if a.get("status") == "validated"])

        logger.info("\n" + "=" * 80)
        logger.info("📊 STATISTIQUES FINALES")
        logger.info("=" * 80)
        logger.info(f"Durée totale: {duration}")
        logger.info(f"Cycles exécutés: {self.cycle_count}")
        logger.info(f"Projets découverts: {len(self.discoveries)}")
        logger.info(f"Analyses effectuées: {len(self.analyses)}")
        logger.info(f"Agents créés: {total_created}")
        logger.info(f"Agents validés: {total_validated}")
        logger.info(f"Taux de succès: {total_validated/max(total_created,1)*100:.1f}%")

        # Génère README complet
        readme = f"""# 🚀 MISSION AUTONOME COMPLÈTE - RAPPORT DÉTAILLÉ

## 📅 Informations Mission

- **Début:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **Fin:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Durée totale:** {duration}
- **Durée prévue:** {self.duration}h

---

## 📊 STATISTIQUES GLOBALES

| Métrique | Résultat |
|----------|----------|
| Cycles exécutés | {self.cycle_count} |
| Projets découverts | {len(self.discoveries)} |
| Analyses effectuées | {len(self.analyses)} |
| Agents créés | {total_created} |
| Agents validés | {total_validated} |
| **Taux de succès** | **{total_validated/max(total_created,1)*100:.1f}%** |

---

## 🔄 DÉROULEMENT PAR CYCLE

"""

        # Groupe agents par cycle
        by_cycle = {}
        for agent in self.agents_created:
            cycle = agent.get("cycle", 0)
            if cycle not in by_cycle:
                by_cycle[cycle] = []
            by_cycle[cycle].append(agent)

        for cycle_num in sorted(by_cycle.keys()):
            agents = by_cycle[cycle_num]
            validated_count = len([a for a in agents if a.get("status") == "validated"])

            readme += f"""
### Cycle {cycle_num}

- **Agents créés:** {len(agents)}
- **Agents validés:** {validated_count}
- **Taux succès:** {validated_count/len(agents)*100:.1f}%

"""
            for agent in agents:
                status_icon = "✅" if agent.get("status") == "validated" else "❌"
                readme += f"  {status_icon} `{agent['name']}` ({agent['type']})\n"

        readme += f"""
---

## ✅ AGENTS VALIDÉS ET FONCTIONNELS

**Total: {total_validated} agents**

"""

        for agent in self.agents_created:
            if agent.get("status") == "validated":
                readme += f"""
### {agent['name']}

- **Type:** {agent['type']}
- **Basé sur:** {agent.get('based_on', 'N/A')}
- **Fichier:** `agentscope_agents/{agent['name']}.py`
- **Cycle de création:** {agent.get('cycle', 'N/A')}
"""

        readme += f"""
---

## 🎯 CONCLUSION

{"🎉 **MISSION RÉUSSIE !**" if total_validated > 0 else "❌ **MISSION ÉCHOUÉE**"}

**Résumé:**
- {self.cycle_count} cycles complets exécutés
- {total_validated} agent(s) AgentScope fonctionnel(s) créé(s)
- Système a travaillé de façon autonome pendant {duration}
- Agents prêts à être utilisés dans ai_orch

**Prochaines étapes:**
1. Examiner les agents créés dans `agentscope_agents/`
2. Intégrer les meilleurs dans workflows existants
3. Tester en conditions réelles
4. Relancer mission pour améliorer davantage

---

*Rapport généré automatiquement le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Mission autonome - ai_orch project*
"""

        # Sauvegarde README
        readme_file = Path(
            f'reports/MISSION_TRUE_AUTO_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        )
        readme_file.parent.mkdir(parents=True, exist_ok=True)
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme)

        # Sauvegarde JSON
        report_json = {
            "mission_info": {
                "start": self.start_time.isoformat(),
                "end": datetime.now().isoformat(),
                "duration": str(duration),
                "cycles": self.cycle_count,
            },
            "statistics": {
                "discoveries": len(self.discoveries),
                "analyses": len(self.analyses),
                "agents_created": total_created,
                "agents_validated": total_validated,
                "success_rate": total_validated / max(total_created, 1) * 100,
            },
            "agents": self.agents_created,
        }

        json_file = Path(
            f'reports/mission_true_auto_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        with open(json_file, "w") as f:
            json.dump(report_json, f, indent=2)

        logger.info(f"\n📄 Rapport détaillé: {readme_file}")
        logger.info(f"📄 Données JSON: {json_file}")
        logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    # Crée dossier logs
    Path("logs").mkdir(exist_ok=True)

    # Lance mission
    mission = TrueAutonomousMission(duration_hours=2)
    mission.run()
