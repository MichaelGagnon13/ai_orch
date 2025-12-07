from collections import defaultdict

"""
Orchestrateur intelligent qui analyse la complexité d'une tâche,
la divise en sous-tâches, les exécute via APIs Claude/GPT,
assemble les résultats et valide la cohérence finale.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from openai import OpenAI

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Niveaux de complexité des tâches"""

    SIMPLE = "simple"  # < 100 lignes estimées
    MODERATE = "moderate"  # 100-300 lignes
    COMPLEX = "complex"  # 300-500 lignes
    VERY_COMPLEX = "very_complex"  # > 500 lignes, nécessite division


class AIProvider(Enum):
    """Fournisseurs d'API IA"""

    CLAUDE = "claude"
    GPT = "gpt"
    AUTO = "auto"  # Sélection automatique


@dataclass
class SubTask:
    """Représente une sous-tâche"""

    id: str
    title: str
    description: str
    estimated_lines: int
    dependencies: List[str]
    priority: int
    context: Optional[Dict[str, Any]] = None
    status: str = "pending"
    result: Optional[str] = None
    execution_time: Optional[float] = None
    provider_used: Optional[str] = None
    error: Optional[str] = None


@dataclass
class TaskAnalysis:
    """Analyse d'une tâche"""

    complexity: TaskComplexity
    estimated_total_lines: int
    requires_splitting: bool
    subtasks: List[SubTask]
    execution_strategy: str
    estimated_duration: int  # en minutes


@dataclass
class ExecutionResult:
    """Résultat d'exécution d'une tâche"""

    success: bool
    final_result: Optional[str]
    subtask_results: List[Dict[str, Any]]
    total_execution_time: float
    validation_score: float
    errors: List[str]
    metadata: Dict[str, Any]


class TaskSplitter:
    """Orchestrateur intelligent de division et exécution de tâches"""

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 300,
        results_dir: str = "results/task_splitter",
    ):
        """
        Initialise l'orchestrateur de tâches.

        Args:
            anthropic_api_key: Clé API Anthropic
            openai_api_key: Clé API OpenAI
            max_retries: Nombre max de tentatives
            timeout: Timeout par requête
            results_dir: Répertoire de sauvegarde
        """
        self.anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.max_retries = max_retries
        self.timeout = timeout
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Initialisation des clients API
        self.anthropic_client = None
        self.openai_client = None

        if self.anthropic_key:
            try:
                self.anthropic_client = Anthropic(api_key=self.anthropic_key)
                logger.info("Client Anthropic initialisé")
            except Exception as e:
                logger.error(f"Erreur initialisation Anthropic: {e}")

        if self.openai_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
                logger.info("Client OpenAI initialisé")
            except Exception as e:
                logger.error(f"Erreur initialisation OpenAI: {e}")

        if not self.anthropic_client and not self.openai_client:
            raise ValueError("Au moins une clé API (Anthropic ou OpenAI) est requise")

        # Métriques
        self.execution_stats = {
            "tasks_processed": 0,
            "subtasks_created": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
        }

    async def analyze_task_complexity(
        self, task_description: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskAnalysis:
        """
        Analyse la complexité d'une tâche et détermine s'il faut la diviser.

        Args:
            task_description: Description de la tâche
            context: Contexte supplémentaire

        Returns:
            Analyse de la tâche
        """
        logger.info("Analyse de la complexité de la tâche")

        analysis_prompt = f"""
        Analysez cette tâche et déterminez sa complexité:

        TÂCHE: {task_description}

        CONTEXTE: {json.dumps(context or {}, indent=2)}

        Fournissez une analyse sous ce format JSON exact:
        {{
            "complexity": "simple|moderate|complex|very_complex",
            "estimated_total_lines": <nombre>,
            "requires_splitting": <boolean>,
            "reasoning": "<explication>",
            "subtasks": [
                {{
                    "title": "<titre>",
                    "description": "<description>",
                    "estimated_lines": <nombre>,
                    "dependencies": ["<id_autre_subtask>"],
                    "priority": <1-10>
                }}
            ],
            "execution_strategy": "<séquentiel|parallèle|hybride>",
            "estimated_duration": <minutes>
        }}

        Règles:
        - Une tâche > 500 lignes doit être divisée
        - Chaque sous-tâche < 500 lignes
        - Identifier les dépendances entre sous-tâches
        - Prioriser par ordre logique d'exécution
        """

        try:
            response = await self._call_ai_api(analysis_prompt, AIProvider.CLAUDE)
            analysis_data = json.loads(response)

            # Validation des données
            complexity = TaskComplexity(analysis_data["complexity"])
            requires_splitting = analysis_data["requires_splitting"]

            # Création des sous-tâches
            subtasks = []
            for i, subtask_data in enumerate(analysis_data.get("subtasks", [])):
                subtask = SubTask(
                    id=f"subtask_{i+1}",
                    title=subtask_data["title"],
                    description=subtask_data["description"],
                    estimated_lines=subtask_data["estimated_lines"],
                    dependencies=subtask_data.get("dependencies", []),
                    priority=subtask_data.get("priority", 5),
                    context=context,
                )
                subtasks.append(subtask)

            # Si pas de division nécessaire, créer une tâche unique
            if not requires_splitting and not subtasks:
                subtasks = [
                    SubTask(
                        id="main_task",
                        title="Tâche principale",
                        description=task_description,
                        estimated_lines=analysis_data["estimated_total_lines"],
                        dependencies=[],
                        priority=1,
                        context=context,
                    )
                ]

            analysis = TaskAnalysis(
                complexity=complexity,
                estimated_total_lines=analysis_data["estimated_total_lines"],
                requires_splitting=requires_splitting,
                subtasks=subtasks,
                execution_strategy=analysis_data.get("execution_strategy", "séquentiel"),
                estimated_duration=analysis_data.get("estimated_duration", 30),
            )

            logger.info(f"Analyse terminée: {complexity.value}, " f"{len(subtasks)} sous-tâches")

            return analysis

        except Exception as e:
            logger.error(f"Erreur analyse complexité: {e}")
            # Analyse de fallback
            return self._create_fallback_analysis(task_description, context)

    def _create_fallback_analysis(
        self, task_description: str, context: Optional[Dict[str, Any]]
    ) -> TaskAnalysis:
        """Crée une analyse de fallback en cas d'erreur"""
        return TaskAnalysis(
            complexity=TaskComplexity.MODERATE,
            estimated_total_lines=300,
            requires_splitting=False,
            subtasks=[
                SubTask(
                    id="fallback_task",
                    title="Tâche à traiter",
                    description=task_description,
                    estimated_lines=300,
                    dependencies=[],
                    priority=1,
                    context=context,
                )
            ],
            execution_strategy="séquentiel",
            estimated_duration=30,
        )

    async def execute_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_provider: AIProvider = AIProvider.AUTO,
    ) -> ExecutionResult:
        """
        Exécute une tâche complète avec division si nécessaire.

        Args:
            task_description: Description de la tâche
            context: Contexte d'exécution
            preferred_provider: Fournisseur IA préféré

        Returns:
            Résultat d'exécution
        """
        start_time = time.time()
        logger.info(f"Début exécution tâche: {task_description[:100]}...")

        try:
            # 1. Analyser la complexité
            analysis = await self.analyze_task_complexity(task_description, context)

            # 2. Exécuter les sous-tâches
            subtask_results = []
            if analysis.execution_strategy == "séquentiel":
                subtask_results = await self._execute_sequential(
                    analysis.subtasks, preferred_provider
                )
            elif analysis.execution_strategy == "parallèle":
                subtask_results = await self._execute_parallel(
                    analysis.subtasks, preferred_provider
                )
            else:  # hybride
                subtask_results = await self._execute_hybrid(analysis.subtasks, preferred_provider)

            # 3. Assembler les résultats
            final_result = await self._assemble_results(subtask_results, task_description, context)

            # 4. Valider la cohérence
            validation_score = await self._validate_coherence(
                final_result, task_description, subtask_results
            )

            # 5. Créer le résultat final
            execution_time = time.time() - start_time
            errors = [r.get("error", "") for r in subtask_results if r.get("error")]

            result = ExecutionResult(
                success=validation_score >= 0.7,
                final_result=final_result,
                subtask_results=subtask_results,
                total_execution_time=execution_time,
                validation_score=validation_score,
                errors=errors,
                metadata={
                    "analysis": asdict(analysis),
                    "execution_strategy": analysis.execution_strategy,
                    "subtasks_count": len(analysis.subtasks),
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Sauvegarder le résultat
            await self._save_execution_result(result, task_description)

            # Mettre à jour les stats
            self.execution_stats["tasks_processed"] += 1
            self.execution_stats["subtasks_created"] += len(analysis.subtasks)
            self.execution_stats["total_execution_time"] += execution_time

            if result.success:
                self.execution_stats["successful_executions"] += 1
                logger.info(f"Tâche exécutée avec succès en {execution_time:.2f}s")
            else:
                self.execution_stats["failed_executions"] += 1
                logger.warning(f"Tâche échouée, score validation: {validation_score}")

            return result

        except Exception as e:
            logger.error(f"Erreur exécution tâche: {e}")
            execution_time = time.time() - start_time
            self.execution_stats["failed_executions"] += 1

            return ExecutionResult(
                success=False,
                final_result=None,
                subtask_results=[],
                total_execution_time=execution_time,
                validation_score=0.0,
                errors=[str(e)],
                metadata={"error": str(e), "timestamp": datetime.now().isoformat()},
            )

    async def _execute_sequential(
        self, subtasks: List[SubTask], preferred_provider: AIProvider
    ) -> List[Dict[str, Any]]:
        """Exécute les sous-tâches séquentiellement"""
        logger.info(f"Exécution séquentielle de {len(subtasks)} sous-tâches")

        results = []
        completed_tasks = {}

        # Trier par priorité et dépendances
        sorted_subtasks = self._sort_subtasks_by_dependencies(subtasks)

        for subtask in sorted_subtasks:
            logger.info(f"Exécution sous-tâche: {subtask.title}")

            try:
                # Vérifier les dépendances
                if not self._dependencies_satisfied(subtask, completed_tasks):
                    raise ValueError(f"Dépendances non satisfaites pour {subtask.id}")

                # Construire le contexte avec les résultats des dépendances
                execution_context = self._build_execution_context(subtask, completed_tasks)

                # Exécuter la sous-tâche
                result = await self._execute_subtask(subtask, execution_context, preferred_provider)
                results.append(result)

                if result["success"]:
                    completed_tasks[subtask.id] = result
                    subtask.status = "completed"
                    subtask.result = result["result"]
                else:
                    subtask.status = "failed"
                    subtask.error = result.get("error")

            except Exception as e:
                logger.error(f"Erreur sous-tâche {subtask.id}: {e}")
                result = {
                    "subtask_id": subtask.id,
                    "success": False,
                    "error": str(e),
                    "execution_time": 0.0,
                }
                results.append(result)
                subtask.status = "failed"
                subtask.error = str(e)

        return results

    async def _execute_parallel(
        self, subtasks: List[SubTask], preferred_provider: AIProvider
    ) -> List[Dict[str, Any]]:
        """Exécute les sous-tâches en parallèle (sans dépendances)"""
        logger.info(f"Exécution parallèle de {len(subtasks)} sous-tâches")

        # Filtrer les tâches sans dépendances pour le parallélisme
        independent_tasks = [t for t in subtasks if not t.dependencies]
        dependent_tasks = [t for t in subtasks if t.dependencies]

        results = []

        # Exécuter les tâches indépendantes en parallèle
        if independent_tasks:
            parallel_results = await asyncio.gather(
                *[
                    self._execute_subtask(task, {}, preferred_provider)
                    for task in independent_tasks
                ],
                return_exceptions=True,
            )

            for i, result in enumerate(parallel_results):
                if isinstance(result, Exception):
                    result = {
                        "subtask_id": independent_tasks[i].id,
                        "success": False,
                        "error": str(result),
                        "execution_time": 0.0,
                    }
                results.append(result)

        # Exécuter les tâches dépendantes séquentiellement
        if dependent_tasks:
            sequential_results = await self._execute_sequential(dependent_tasks, preferred_provider)
            results.extend(sequential_results)

        return results

    async def _execute_hybrid(
        self, subtasks: List[SubTask], preferred_provider: AIProvider
    ) -> List[Dict[str, Any]]:
        """Exécute avec stratégie hybride (parallèle + séquentiel)"""
        logger.info(f"Exécution hybride de {len(subtasks)} sous-tâches")

        # Analyser le graphe de dépendances
        dependency_levels = self._analyze_dependency_levels(subtasks)
        results = []
        completed_tasks = {}

        # Exécuter par niveaux de dépendances
        for level, level_tasks in dependency_levels.items():
            logger.info(f"Exécution niveau {level}: {len(level_tasks)} tâches")

            if len(level_tasks) == 1:
                # Exécution séquentielle pour une seule tâche
                task = level_tasks[0]
                context = self._build_execution_context(task, completed_tasks)
                result = await self._execute_subtask(task, context, preferred_provider)
                results.append(result)

                if result["success"]:
                    completed_tasks[task.id] = result
            else:
                # Exécution parallèle pour plusieurs tâches
                level_results = await asyncio.gather(
                    *[
                        self._execute_subtask(
                            task,
                            self._build_execution_context(task, completed_tasks),
                            preferred_provider,
                        )
                        for task in level_tasks
                    ],
                    return_exceptions=True,
                )

                for i, result in enumerate(level_results):
                    if isinstance(result, Exception):
                        result = {
                            "subtask_id": level_tasks[i].id,
                            "success": False,
                            "error": str(result),
                            "execution_time": 0.0,
                        }
                    results.append(result)

                    if result["success"]:
                        completed_tasks[level_tasks[i].id] = result

        return results

    async def _execute_subtask(
        self, subtask: SubTask, context: Dict[str, Any], preferred_provider: AIProvider
    ) -> Dict[str, Any]:
        """
        Exécute une sous-tâche individuelle.

        Args:
            subtask: Sous-tâche à exécuter
            context: Contexte d'exécution
            preferred_provider: Fournisseur préféré

        Returns:
            Résultat de l'exécution
        """
        start_time = time.time()

        execution_prompt = f"""
        Exécutez cette sous-tâche avec précision:

        TITRE: {subtask.title}
        DESCRIPTION: {subtask.description}
        LIGNES ESTIMÉES: {subtask.estimated_lines}

        CONTEXTE: {json.dumps(context, indent=2)}

        INSTRUCTIONS:
        - Fournissez un résultat complet et fonctionnel
        - Respectez la limite de ~{subtask.estimated_lines} lignes
        - Utilisez le contexte fourni si pertinent
        - Formatez proprement le code/résultat
        - Ajoutez des commentaires explicatifs

        RÉSULTAT:
        """

        try:
            # Sélectionner le provider
            provider = self._select_provider(preferred_provider, subtask)

            # Exécuter avec retry
            result_text = None
            for attempt in range(self.max_retries):
                try:
                    result_text = await self._call_ai_api(execution_prompt, provider)
                    break
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    logger.warning(f"Tentative {attempt + 1} échouée: {e}")
                    await asyncio.sleep(2**attempt)  # Backoff exponentiel

            execution_time = time.time() - start_time

            # Valider le résultat
            is_valid = await self._validate_subtask_result(subtask, result_text)

            return {
                "subtask_id": subtask.id,
                "success": is_valid,
                "result": result_text,
                "execution_time": execution_time,
                "provider_used": provider.value,
                "lines_count": len(result_text.split("\n")) if result_text else 0,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Erreur exécution sous-tâche {subtask.id}: {e}")

            return {
                "subtask_id": subtask.id,
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
            }

    async def _assemble_results(
        self,
        subtask_results: List[Dict[str, Any]],
        original_task: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """
        Assemble les résultats des sous-tâches en un résultat final cohérent.

        Args:
            subtask_results: Résultats des sous-tâches
            original_task: Tâche originale
            context: Contexte

        Returns:
            Résultat final assemblé
        """
        logger.info("Assemblage des résultats")

        # Filtrer les résultats réussis
        successful_results = [r for r in subtask_results if r.get("success", False)]

        if not successful_results:
            return "ERREUR: Aucune sous-tâche n'a réussi"

        # Construire le prompt d'assemblage
        results_text = ""
        for i, result in enumerate(successful_results):
            results_text += (
                f"\n--- RÉSULTAT SOUS-TÂCHE {i+1} (ID: {result.get('subtask_id')}) ---\n"
            )
            results_text += result.get("result", "")
            results_text += "\n"

        assembly_prompt = f"""
        Assemblez ces résultats de sous-tâches en un résultat final cohérent:

        TÂCHE ORIGINALE: {original_task}
        CONTEXTE: {json.dumps(context or {}, indent=2)}

        RÉSULTATS À ASSEMBLER:
        {results_text}

        INSTRUCTIONS D'ASSEMBLAGE:
        - Créez un résultat final unifié et cohérent
        - Respectez l'intention de la tâche originale
        - Intégrez harmonieusement tous les éléments réussis
        - Résolvez les éventuelles contradictions
        - Ajoutez des transitions si nécessaire
        - Maintenez la qualité et la lisibilité

        RÉSULTAT FINAL ASSEMBLÉ:
        """

        try:
            final_result = await self._call_ai_api(assembly_prompt, AIProvider.CLAUDE)
            logger.info("Assemblage terminé avec succès")
            return final_result

        except Exception as e:
            logger.error(f"Erreur assemblage: {e}")
            # Fallback: concaténation simple
            return "\n\n".join([r.get("result", "") for r in successful_results])

    async def _validate_coherence(
        self, final_result: str, original_task: str, subtask_results: List[Dict[str, Any]]
    ) -> float:
        """
        Valide la cohérence du résultat final.

        Args:
            final_result: Résultat final
            original_task: Tâche originale
            subtask_results: Résultats des sous-tâches

        Returns:
            Score de validation (0.0 à 1.0)
        """
        logger.info("Validation de la cohérence")

        validation_prompt = f"""
        Évaluez la cohérence de ce résultat final par rapport à la tâche originale:

        TÂCHE ORIGINALE: {original_task}

        RÉSULTAT FINAL:
        {final_result}

        CRITÈRES D'ÉVALUATION:
        1. Complétude: Le résultat répond-il entièrement à la tâche? (0-25 points)
        2. Cohérence: Le résultat est-il logique et cohérent? (0-25 points)
        3. Qualité: Le code/contenu est-il de bonne qualité? (0-25 points)
        4. Fonctionnalité: Le résultat est-il utilisable/fonctionnel? (0-25 points)

        Répondez UNIQUEMENT avec un JSON:
        {{
            "completude": <0-25>,
            "coherence": <0-25>,
            "qualite": <0-25>,
            "fonctionnalite": <0-25>,
            "score_total": <0-100>,
            "commentaires": "<explication courte>"
        }}
        """

        try:
            response = await self._call_ai_api(validation_prompt, AIProvider.GPT)
            validation_data = json.loads(response)

            score = validation_data.get("score_total", 0) / 100.0
            logger.info(f"Score de validation: {score:.2f}")

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.error(f"Erreur validation: {e}")
            # Score de fallback basé sur des heuristiques simples
            if not final_result or len(final_result.strip()) < 50:
                return 0.2

            successful_subtasks = len([r for r in subtask_results if r.get("success")])
            total_subtasks = len(subtask_results)

            if total_subtasks == 0:
                return 0.5

            return min(0.8, successful_subtasks / total_subtasks)

    async def _call_ai_api(self, prompt: str, provider: AIProvider) -> str:
        """
        Appelle l'API IA appropriée.

        Args:
            prompt: Prompt à envoyer
            provider: Fournisseur à utiliser

        Returns:
            Réponse de l'API
        """
        if provider == AIProvider.AUTO:
            provider = self._select_best_provider()

        try:
            if provider == AIProvider.CLAUDE and self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=32000,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text

            elif provider == AIProvider.GPT and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-5.1",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=32000,
                )
                return response.choices[0].message.content

            else:
                raise ValueError(f"Provider {provider} non disponible")

        except Exception as e:
            logger.error(f"Erreur API {provider}: {e}")
            raise

    def _select_provider(self, preferred: AIProvider, subtask: SubTask) -> AIProvider:
        """Sélectionne le meilleur provider pour une sous-tâche"""
        if preferred != AIProvider.AUTO:
            return preferred

        # Logique de sélection basée sur le type de tâche
        if "code" in subtask.description.lower() or "python" in subtask.description.lower():
            return AIProvider.GPT if self.openai_client else AIProvider.CLAUDE
        else:
            return AIProvider.CLAUDE if self.anthropic_client else AIProvider.GPT

    def _select_best_provider(self) -> AIProvider:
        """Sélectionne le meilleur provider disponible"""
        if self.anthropic_client:
            return AIProvider.CLAUDE
        elif self.openai_client:
            return AIProvider.GPT
        else:
            raise ValueError("Aucun provider disponible")

    def _sort_subtasks_by_dependencies(self, subtasks: List[SubTask]) -> List[SubTask]:
        """Trie les sous-tâches par ordre de dépendances"""
        sorted_tasks = []
        remaining_tasks = subtasks.copy()
        completed_ids = set()

        while remaining_tasks:
            # Trouver les tâches sans dépendances non satisfaites
            ready_tasks = []
            for task in remaining_tasks:
                if all(dep in completed_ids for dep in task.dependencies):
                    ready_tasks.append(task)

            if not ready_tasks:
                # Dépendances circulaires détectées, prendre la première
                ready_tasks = [remaining_tasks[0]]
                logger.warning("Dépendances circulaires détectées")

            # Trier par priorité
            ready_tasks.sort(key=lambda t: t.priority)

            for task in ready_tasks:
                sorted_tasks.append(task)
                completed_ids.add(task.id)
                remaining_tasks.remove(task)

        return sorted_tasks

    def _dependencies_satisfied(self, subtask: SubTask, completed_tasks: Dict[str, Any]) -> bool:
        """Vérifie si les dépendances d'une sous-tâche sont satisfaites"""
        return all(dep in completed_tasks for dep in subtask.dependencies)

    def _build_execution_context(
        self, subtask: SubTask, completed_tasks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Construit le contexte d'exécution avec les résultats des dépendances"""
        context = subtask.context.copy() if subtask.context else {}

        # Ajouter les résultats des dépendances
        dependencies_results = {}
        for dep_id in subtask.dependencies:
            if dep_id in completed_tasks:
                dependencies_results[dep_id] = completed_tasks[dep_id].get("result", "")

        if dependencies_results:
            context["dependencies_results"] = dependencies_results

        return context

    def _analyze_dependency_levels(self, subtasks: List[SubTask]) -> Dict[int, List[SubTask]]:
        """Analyse les niveaux de dépendances pour l'exécution hybride"""
        levels = defaultdict(list)
        task_levels = {}

        # Calculer le niveau de chaque tâche
        for task in subtasks:
            level = self._calculate_task_level(task, subtasks, task_levels)
            levels[level].append(task)
            task_levels[task.id] = level

        return dict(levels)

    def _calculate_task_level(
        self, task: SubTask, all_tasks: List[SubTask], task_levels: Dict[str, int]
    ) -> int:
        """Calcule le niveau de dépendance d'une tâche"""
        if task.id in task_levels:
            return task_levels[task.id]

        if not task.dependencies:
            task_levels[task.id] = 0
            return 0

        # Trouver le niveau maximum des dépendances
        max_dep_level = -1
        for dep_id in task.dependencies:
            dep_task = next((t for t in all_tasks if t.id == dep_id), None)
            if dep_task:
                dep_level = self._calculate_task_level(dep_task, all_tasks, task_levels)
                max_dep_level = max(max_dep_level, dep_level)

        level = max_dep_level + 1
        task_levels[task.id] = level
        return level

    async def _validate_subtask_result(self, subtask: SubTask, result: str) -> bool:
        """Valide le résultat d'une sous-tâche"""
        if not result or len(result.strip()) < 10:
            return False

        # Validation basique
        if subtask.estimated_lines > 0:
            result_lines = len(result.split("\n"))
            # Tolérance de ±50% sur l'estimation
            min_lines = max(10, subtask.estimated_lines * 0.5)
            max_lines = subtask.estimated_lines * 2

            if not (min_lines <= result_lines <= max_lines):
                logger.warning(
                    f"Taille résultat hors estimation: "
                    f"{result_lines} lignes vs {subtask.estimated_lines} attendues"
                )

        return True

    async def _save_execution_result(self, result: ExecutionResult, task_description: str):
        """Sauvegarde le résultat d'exécution"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_hash = hashlib.md5(task_description.encode()).hexdigest()[:8]
            filename = f"task_result_{timestamp}_{task_hash}.json"
            filepath = self.results_dir / filename

            # Préparer les données à sauvegarder
            save_data = {
                "task_description": task_description,
                "timestamp": datetime.now().isoformat(),
                "result": asdict(result),
                "execution_stats": self.execution_stats.copy(),
            }

            # Sauvegarder en JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            # Sauvegarder aussi le résultat final en texte
            if result.final_result:
                text_filename = f"task_result_{timestamp}_{task_hash}.txt"
                text_filepath = self.results_dir / text_filename

                with open(text_filepath, "w", encoding="utf-8") as f:
                    f.write(f"TÂCHE: {task_description}\n")
                    f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
                    f.write(f"SUCCÈS: {result.success}\n")
                    f.write(f"SCORE VALIDATION: {result.validation_score:.2f}\n")
                    f.write("\n" + "=" * 50 + "\n")
                    f.write("RÉSULTAT FINAL:\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(result.final_result)

            logger.info(f"Résultat sauvegardé: {filepath}")

        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")

    def get_execution_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'exécution"""
        stats = self.execution_stats.copy()
        if stats["tasks_processed"] > 0:
            stats["average_execution_time"] = (
                stats["total_execution_time"] / stats["tasks_processed"]
            )
            stats["success_rate"] = stats["successful_executions"] / stats["tasks_processed"]
        else:
            stats["average_execution_time"] = 0.0
            stats["success_rate"] = 0.0

        return stats


async def main():
    """Fonction de test"""
    # Configuration
    splitter = TaskSplitter()

    # Tâche de test
    test_task = """
    Créer un système de gestion de bibliothèque en Python avec:
    1. Classes pour Livre, Auteur, Emprunteur
    2. Base de données SQLite pour la persistance
    3. API REST avec FastAPI
    4. Interface web simple avec HTML/CSS/JS
    5. Tests unitaires avec pytest
    6. Documentation complète
    """

    print("🚀 Test du TaskSplitter")
    print(f"Tâche: {test_task}")

    # Exécuter la tâche
    result = await splitter.execute_task(test_task)

    print("\n✅ Résultat:")
    print(f"Succès: {result.success}")
    print(f"Temps d'exécution: {result.total_execution_time:.2f}s")
    print(f"Score validation: {result.validation_score:.2f}")
    print(f"Sous-tâches: {len(result.subtask_results)}")

    if result.errors:
        print(f"Erreurs: {result.errors}")

    # Statistiques
    stats = splitter.get_execution_stats()
    print(f"\n📊 Statistiques: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
