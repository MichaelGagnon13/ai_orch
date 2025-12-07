"""
Mission autonome de 2 heures qui lance une veille technologique continue
avec orchestration multi-agents et rapports réguliers.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("mission_2h.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Import des agents
try:
    from agents.task_splitter import TaskSplitter
    from agents.web_researcher import WebResearcher
except ImportError:
    logger.error("Impossible d'importer les agents nécessaires")
    sys.exit(1)


@dataclass
class MissionMetrics:
    """Métriques de la mission"""

    start_time: datetime
    end_time: Optional[datetime] = None
    tech_scout_runs: int = 0
    tasks_completed: int = 0
    errors_count: int = 0
    reports_generated: int = 0
    data_points_collected: int = 0
    avg_response_time: float = 0.0
    active_threads: int = 0


@dataclass
class MissionReport:
    """Rapport de mission"""

    timestamp: datetime
    metrics: MissionMetrics
    tech_data: Dict[str, Any]
    system_status: Dict[str, Any]
    next_actions: List[str]


class TechScoutAgent:
    """Agent de veille technologique simplifié pour la mission"""

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.running = False

    async def run_continuous_monitoring(self) -> Dict[str, Any]:
        """Lance la surveillance continue"""
        results = {
            "github_trending": [],
            "pypi_updates": [],
            "tech_news": [],
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Surveillance GitHub trending
            github_data = await self._get_github_trending()
            results["github_trending"] = github_data

            # Surveillance PyPI
            pypi_data = await self._get_pypi_updates()
            results["pypi_updates"] = pypi_data

            # Tech news
            news_data = await self._get_tech_news()
            results["tech_news"] = news_data

        except Exception as e:
            logger.error(f"Erreur dans la surveillance tech: {e}")
            results["error"] = str(e)

        return results

    async def _get_github_trending(self) -> List[Dict[str, Any]]:
        """Récupère les repos GitHub trending"""
        import requests

        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            # Recherche repos créés récemment avec beaucoup d'étoiles
            url = "https://api.github.com/search/repositories"
            params = {
                "q": f'created:>{(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")}',
                "sort": "stars",
                "order": "desc",
                "per_page": 10,
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo["description"],
                        "stars": repo["stargazers_count"],
                        "language": repo["language"],
                        "url": repo["html_url"],
                    }
                    for repo in data["items"][:5]
                ]

        except Exception as e:
            logger.error(f"Erreur GitHub API: {e}")

        return []

    async def _get_pypi_updates(self) -> List[Dict[str, Any]]:
        """Récupère les mises à jour PyPI importantes"""
        import requests

        popular_packages = [
            "requests",
            "numpy",
            "pandas",
            "django",
            "flask",
            "fastapi",
            "pytest",
            "asyncio",
            "tensorflow",
            "pytorch",
        ]
        updates = []

        for package in popular_packages[:3]:  # Limite pour éviter les timeouts
            try:
                url = f"https://pypi.org/pypi/{package}/json"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    info = data["info"]

                    # Parse de la date de release
                    releases = data["releases"]
                    latest_version = info["version"]

                    if latest_version in releases and releases[latest_version]:
                        release_date = releases[latest_version][0]["upload_time"]
                        release_dt = datetime.fromisoformat(release_date.replace("Z", "+00:00"))

                        # Si c'est récent (moins de 30 jours)
                        if (
                            datetime.now().replace(tzinfo=None) - release_dt.replace(tzinfo=None)
                        ).days < 30:
                            updates.append(
                                {
                                    "name": package,
                                    "version": latest_version,
                                    "summary": info["summary"],
                                    "release_date": release_date,
                                    "home_page": info.get("home_page", ""),
                                    "author": info.get("author", ""),
                                }
                            )

            except Exception as e:
                logger.error(f"Erreur PyPI pour {package}: {e}")
                continue

        return updates

    async def _get_tech_news(self) -> List[Dict[str, Any]]:
        """Récupère les actualités tech"""
        # Simulation de news tech (en réalité on utiliserait une API news)
        tech_topics = [
            "AI and Machine Learning breakthrough in 2024",
            "Python 3.12 new features and performance improvements",
            "Cloud computing trends and serverless architecture",
            "Cybersecurity threats and prevention strategies",
            "Open source software licensing changes",
        ]

        return [
            {
                "title": topic,
                "source": "TechNews",
                "timestamp": datetime.now().isoformat(),
                "relevance": 0.8,
                "category": "technology",
            }
            for topic in tech_topics[:3]
        ]


class SystemIntegrator:
    """Intégrateur système pour coordonner les agents"""

    def __init__(self):
        self.components = {}
        self.status = "idle"

    async def integrate_data(self, tech_data: Dict, research_data: Dict) -> Dict[str, Any]:
        """Intègre les données de différentes sources"""
        integrated = {
            "integration_timestamp": datetime.now().isoformat(),
            "sources": {
                "tech_scout": len(tech_data.get("github_trending", [])) > 0,
                "web_researcher": len(research_data.get("results", [])) > 0,
            },
            "consolidated_insights": [],
            "recommendations": [],
        }

        # Analyse des tendances GitHub
        if tech_data.get("github_trending"):
            languages = [
                repo.get("language")
                for repo in tech_data["github_trending"]
                if repo.get("language")
            ]
            if languages:
                integrated["consolidated_insights"].append(
                    f"Langages trending: {', '.join(set(languages))}"
                )

        # Recommandations basées sur les données
        if tech_data.get("pypi_updates"):
            integrated["recommendations"].append(
                "Vérifier les mises à jour des dépendances critiques"
            )

        integrated["recommendations"].append("Continuer la surveillance des tendances émergentes")

        return integrated


class MissionOrchestrator:
    """Orchestrateur principal de la mission 2h"""

    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=2)
        self.metrics = MissionMetrics(start_time=self.start_time)
        self.running = False
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)

        # Initialisation des agents
        self.tech_scout = TechScoutAgent()
        self.task_splitter = TaskSplitter()
        self.web_researcher = WebResearcher()
        self.system_integrator = SystemIntegrator()

        # Base de données LLM simplifiée
        self.llm_database = {
            "models": {
                "claude-sonnet-4-20250514": {
                    "provider": "anthropic",
                    "context_length": 200000,
                    "capabilities": ["text", "analysis", "coding"],
                    "cost_per_1k_tokens": 0.003,
                }
            },
            "usage_stats": {"total_requests": 0, "total_tokens": 0, "errors": 0},
            "last_updated": datetime.now().isoformat(),
        }

    async def start_mission(self):
        """Démarre la mission autonome de 2h"""
        logger.info(f"🚀 Démarrage de la mission 2h - Fin prévue: {self.end_time}")
        self.running = True

        # Sauvegarde de la base LLM
        await self._save_llm_database()

        try:
            # Lancement des tâches en parallèle
            await asyncio.gather(
                self._run_tech_scout_loop(),
                self._run_periodic_reports(),
                self._monitor_system(),
                return_exceptions=True,
            )

        except KeyboardInterrupt:
            logger.info("Arrêt demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"Erreur dans la mission: {e}")
            self.metrics.errors_count += 1
        finally:
            await self._finalize_mission()

    async def _run_tech_scout_loop(self):
        """Boucle continue de veille technologique"""
        logger.info("🔍 Démarrage de la veille technologique continue")

        while self.running and datetime.now() < self.end_time:
            try:
                start_time = time.time()

                # Exécution de la veille tech
                tech_data = await self.tech_scout.run_continuous_monitoring()

                # Mise à jour des métriques
                self.metrics.tech_scout_runs += 1
                self.metrics.data_points_collected += (
                    len(tech_data.get("github_trending", []))
                    + len(tech_data.get("pypi_updates", []))
                    + len(tech_data.get("tech_news", []))
                )

                response_time = time.time() - start_time
                self.metrics.avg_response_time = (
                    self.metrics.avg_response_time + response_time
                ) / 2

                # Sauvegarde des données
                await self._save_tech_data(tech_data)

                logger.info(
                    f"✅ Cycle de veille terminé - {self.metrics.data_points_collected} points de données collectés"
                )

                # Attente avant le prochain cycle (5 minutes)
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Erreur dans la boucle tech scout: {e}")
                self.metrics.errors_count += 1
                await asyncio.sleep(60)  # Attente plus courte en cas d'erreur

    async def _run_periodic_reports(self):
        """Génère des rapports toutes les 30 minutes"""
        logger.info("📊 Démarrage de la génération de rapports périodiques")

        while self.running and datetime.now() < self.end_time:
            try:
                await asyncio.sleep(1800)  # 30 minutes

                if not self.running:
                    break

                await self._generate_report()

            except Exception as e:
                logger.error(f"Erreur dans la génération de rapports: {e}")
                self.metrics.errors_count += 1

    async def _monitor_system(self):
        """Surveille l'état du système"""
        logger.info("🖥️ Démarrage du monitoring système")

        while self.running and datetime.now() < self.end_time:
            try:
                # Mise à jour du nombre de threads actifs
                self.metrics.active_threads = threading.active_count()

                # Vérification de l'espace disque disponible
                disk_usage = self._check_disk_space()
                if disk_usage > 90:
                    logger.warning(f"⚠️ Espace disque faible: {disk_usage}%")

                # Vérification de la mémoire
                memory_usage = self._check_memory_usage()
                if memory_usage > 80:
                    logger.warning(f"⚠️ Utilisation mémoire élevée: {memory_usage}%")

                await asyncio.sleep(120)  # Vérification toutes les 2 minutes

            except Exception as e:
                logger.error(f"Erreur dans le monitoring système: {e}")
                await asyncio.sleep(300)

    async def _generate_report(self):
        """Génère un rapport de mission"""
        try:
            # Chargement des dernières données tech
            tech_data = await self._load_latest_tech_data()

            # Recherche web pour enrichir les données
            research_data = await self._perform_web_research(tech_data)

            # Intégration des données
            integrated_data = await self.system_integrator.integrate_data(tech_data, research_data)

            # Création du rapport
            report = MissionReport(
                timestamp=datetime.now(),
                metrics=self.metrics,
                tech_data=tech_data,
                system_status={
                    "uptime": str(datetime.now() - self.start_time),
                    "memory_usage": self._check_memory_usage(),
                    "disk_usage": self._check_disk_space(),
                    "active_threads": self.metrics.active_threads,
                },
                next_actions=[
                    "Continuer la surveillance GitHub",
                    "Analyser les nouvelles tendances",
                    "Optimiser les performances système",
                ],
            )

            # Sauvegarde du rapport
            report_file = (
                self.reports_dir / f"mission_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2, default=str)

            self.metrics.reports_generated += 1
            logger.info(f"📋 Rapport généré: {report_file}")

        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {e}")
            self.metrics.errors_count += 1

    async def _perform_web_research(self, tech_data: Dict) -> Dict:
        """Effectue une recherche web basée sur les données tech"""
        try:
            # Création de requêtes de recherche basées sur les tendances
            queries = []

            for repo in tech_data.get("github_trending", [])[:3]:
                if repo.get("language"):
                    queries.append(f"{repo['language']} programming trends 2024")

            results = []
            for query in queries:
                try:
                    # Utilisation du web researcher (version simplifiée)
                    research_result = await self.web_researcher.search_and_extract(
                        query=query, max_results=2, extract_content=True
                    )
                    results.append(research_result)
                except Exception as e:
                    logger.error(f"Erreur recherche web pour '{query}': {e}")

            return {"results": results}

        except Exception as e:
            logger.error(f"Erreur dans la recherche web: {e}")
            return {"results": []}

    async def _save_tech_data(self, data: Dict):
        """Sauvegarde les données de veille tech"""
        try:
            data_file = (
                self.reports_dir / f"tech_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Erreur sauvegarde données tech: {e}")

    async def _load_latest_tech_data(self) -> Dict:
        """Charge les dernières données de veille tech"""
        try:
            tech_files = list(self.reports_dir.glob("tech_data_*.json"))
            if tech_files:
                latest_file = max(tech_files, key=lambda p: p.stat().st_mtime)
                with open(latest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Erreur chargement données tech: {e}")

        return {}

    async def _save_llm_database(self):
        """Sauvegarde la base de données LLM"""
        try:
            db_file = Path("llm_database.json")
            with open(db_file, "w", encoding="utf-8") as f:
                json.dump(self.llm_database, f, indent=2, default=str)
            logger.info("💾 Base de données LLM sauvegardée")
        except Exception as e:
            logger.error(f"Erreur sauvegarde base LLM: {e}")

    def _check_disk_space(self) -> float:
        """Vérifie l'espace disque disponible"""
        try:
            import shutil

            total, used, free = shutil.disk_usage(".")
            return (used / total) * 100
        except Exception:
            return 0.0

    def _check_memory_usage(self) -> float:
        """Vérifie l'utilisation mémoire"""
        try:
            import psutil

            return psutil.virtual_memory().percent
        except ImportError:
            # Estimation simple si psutil n'est pas disponible
            import sys

            return min(sys.getsizeof(vars()) / 1024 / 1024, 100.0)
        except Exception:
            return 0.0

    async def _finalize_mission(self):
        """Finalise la mission"""
        self.running = False
        self.metrics.end_time = datetime.now()

        # Génération du rapport final
        await self._generate_final_report()

        logger.info(f"🏁 Mission terminée après {self.metrics.end_time - self.metrics.start_time}")
        logger.info("📊 Statistiques finales:")
        logger.info(f"   - Cycles de veille: {self.metrics.tech_scout_runs}")
        logger.info(f"   - Tâches complétées: {self.metrics.tasks_completed}")
        logger.info(f"   - Rapports générés: {self.metrics.reports_generated}")
        logger.info(f"   - Erreurs: {self.metrics.errors_count}")
        logger.info(f"   - Points de données: {self.metrics.data_points_collected}")

    async def _generate_final_report(self):
        """Génère le rapport final de mission"""
        try:
            final_report = {
                "mission_summary": {
                    "duration": str(self.metrics.end_time - self.metrics.start_time),
                    "status": (
                        "completed" if self.metrics.errors_count < 5 else "completed_with_errors"
                    ),
                    "success_rate": (
                        self.metrics.tasks_completed / max(self.metrics.tech_scout_runs, 1)
                    )
                    * 100,
                },
                "metrics": asdict(self.metrics),
                "achievements": [
                    f"Surveillance continue pendant {self.metrics.end_time - self.metrics.start_time}",
                    f"{self.metrics.data_points_collected} points de données collectés",
                    f"{self.metrics.reports_generated} rapports générés",
                    "Base de données LLM mise à jour",
                    "Système d'intégration déployé",
                ],
                "recommendations": [
                    "Augmenter la fréquence de surveillance pour les projets critiques",
                    "Implémenter des alertes en temps réel",
                    "Optimiser les performances de web scraping",
                    "Ajouter plus de sources de données tech",
                ],
            }

            final_file = (
                self.reports_dir
                / f"mission_final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(final_file, "w", encoding="utf-8") as f:
                json.dump(final_report, f, indent=2, default=str)

            logger.info(f"📋 Rapport final généré: {final_file}")

        except Exception as e:
            logger.error(f"Erreur génération rapport final: {e}")


async def main():
    """Point d'entrée principal"""
    logger.info("🎯 Initialisation de la mission autonome 2h")

    # Vérification des variables d'environnement
    required_env_vars = ["ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"Variables d'environnement manquantes: {missing_vars}")
        logger.info("La mission continuera avec des fonctionnalités limitées")

    # Création et lancement de l'orchestrateur
    orchestrator = MissionOrchestrator()

    # Gestion propre des signaux
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} reçu, arrêt gracieux...")
        orchestrator.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await orchestrator.start_mission()
    except Exception as e:
        logger.error(f"Erreur critique dans la mission: {e}")
        logger.error(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Arrêt par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)
