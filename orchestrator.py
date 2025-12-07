"""
Orchestrateur minimal qui lance 2-3 agents en parallèle.
Version simplifiée pour démonstration du système multi-agents.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Statuts des agents."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentResult:
    """Résultat d'exécution d'un agent."""

    agent_id: str
    status: AgentStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = ""


class SimpleAgent:
    """Agent simple pour démonstration."""

    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"Agent-{name}")

    async def run(self, task_data: Dict[str, Any]) -> AgentResult:
        """Exécute une tâche."""
        start_time = time.time()
        self.status = AgentStatus.RUNNING

        try:
            self.logger.info(
                f"Agent {self.name} démarré avec tâche: {task_data.get('task', 'N/A')}"
            )

            # Simulation de travail
            await asyncio.sleep(task_data.get("duration", 2.0))

            # Résultat simulé
            result = {
                "agent": self.name,
                "task_completed": task_data.get("task", "default_task"),
                "processed_items": task_data.get("items", 0),
                "success": True,
            }

            self.status = AgentStatus.COMPLETED
            execution_time = time.time() - start_time

            self.logger.info(f"Agent {self.name} terminé avec succès en {execution_time:.2f}s")

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            self.status = AgentStatus.FAILED
            execution_time = time.time() - start_time
            error_msg = f"Erreur dans {self.name}: {str(e)}"

            self.logger.error(error_msg)

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                error=error_msg,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
            )


class MinimalOrchestrator:
    """Orchestrateur minimal pour gérer plusieurs agents en parallèle."""

    def __init__(self):
        self.agents: Dict[str, SimpleAgent] = {}
        self.results: List[AgentResult] = []
        self.logger = logger

        # Créer le dossier de logs
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

    def add_agent(self, name: str) -> str:
        """Ajoute un agent à l'orchestrateur."""
        agent_id = str(uuid.uuid4())
        self.agents[agent_id] = SimpleAgent(agent_id, name)
        self.logger.info(f"Agent {name} ajouté avec ID: {agent_id}")
        return agent_id

    async def run_agent(self, agent_id: str, task_data: Dict[str, Any]) -> AgentResult:
        """Exécute un agent avec une tâche donnée."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} non trouvé")

        agent = self.agents[agent_id]
        result = await agent.run(task_data)
        self.results.append(result)
        return result

    async def run_agents_parallel(
        self, tasks: List[Tuple[str, Dict[str, Any]]]
    ) -> List[AgentResult]:
        """Exécute plusieurs agents en parallèle."""
        self.logger.info(f"Démarrage de {len(tasks)} agents en parallèle")

        # Créer les tâches asynchrones
        agent_tasks = []
        for agent_id, task_data in tasks:
            task = self.run_agent(agent_id, task_data)
            agent_tasks.append(task)

        # Exécuter en parallèle
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)

        # Traiter les résultats
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_id = tasks[i][0] if i < len(tasks) else "unknown"
                error_result = AgentResult(
                    agent_id=agent_id,
                    status=AgentStatus.FAILED,
                    error=str(result),
                    timestamp=datetime.now().isoformat(),
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        self.logger.info(f"Tous les agents terminés. Résultats: {len(processed_results)}")
        return processed_results

    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des exécutions."""
        if not self.results:
            return {"total": 0, "status": "no_results"}

        completed = sum(1 for r in self.results if r.status == AgentStatus.COMPLETED)
        failed = sum(1 for r in self.results if r.status == AgentStatus.FAILED)
        avg_time = sum(r.execution_time for r in self.results) / len(self.results)

        return {
            "total_executions": len(self.results),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / len(self.results) if self.results else 0,
            "average_execution_time": avg_time,
            "last_execution": self.results[-1].timestamp if self.results else None,
        }

    def save_results(self) -> str:
        """Sauvegarde les résultats dans un fichier JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.logs_dir / f"orchestrator_results_{timestamp}.json"

        data = {
            "summary": self.get_summary(),
            "results": [{**asdict(r), "status": r.status.value} for r in self.results],
            "agents": {aid: agent.name for aid, agent in self.agents.items()},
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Résultats sauvegardés dans: {filename}")
        return str(filename)


async def demo_orchestrator():
    """Démonstration de l'orchestrateur avec 3 agents."""
    print("=== Démonstration Orchestrateur Minimal ===\n")

    # Créer l'orchestrateur
    orchestrator = MinimalOrchestrator()

    # Ajouter des agents
    agent1_id = orchestrator.add_agent("DataProcessor")
    agent2_id = orchestrator.add_agent("FileAnalyzer")
    agent3_id = orchestrator.add_agent("ReportGenerator")

    # Définir les tâches
    tasks = [
        (agent1_id, {"task": "process_data", "items": 100, "duration": 2.5}),
        (agent2_id, {"task": "analyze_files", "items": 50, "duration": 1.8}),
        (agent3_id, {"task": "generate_report", "items": 25, "duration": 3.2}),
    ]

    print("Agents créés:")
    for aid, agent in orchestrator.agents.items():
        print(f"  - {agent.name} (ID: {aid[:8]}...)")

    print(f"\nDémarrage de {len(tasks)} agents en parallèle...")
    start_time = time.time()

    # Exécuter les agents
    results = await orchestrator.run_agents_parallel(tasks)

    total_time = time.time() - start_time

    # Afficher les résultats
    print(f"\nExécution terminée en {total_time:.2f}s")
    print("\nRésultats par agent:")
    for result in results:
        status_emoji = "✅" if result.status == AgentStatus.COMPLETED else "❌"
        print(f"  {status_emoji} Agent {result.agent_id[:8]}... - {result.status.value}")
        if result.result:
            print(f"     Tâche: {result.result.get('task_completed', 'N/A')}")
            print(f"     Items: {result.result.get('processed_items', 0)}")
        if result.error:
            print(f"     Erreur: {result.error}")
        print(f"     Durée: {result.execution_time:.2f}s")

    # Résumé global
    summary = orchestrator.get_summary()
    print("\nRésumé global:")
    print(f"  - Exécutions: {summary['total_executions']}")
    print(f"  - Succès: {summary['completed']}")
    print(f"  - Échecs: {summary['failed']}")
    print(f"  - Taux de succès: {summary['success_rate']:.1%}")
    print(f"  - Durée moyenne: {summary['average_execution_time']:.2f}s")

    # Sauvegarder
    filename = orchestrator.save_results()
    print(f"\nRésultats sauvegardés: {filename}")


if __name__ == "__main__":
    try:
        asyncio.run(demo_orchestrator())
    except KeyboardInterrupt:
        print("\nInterruption par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        raise
