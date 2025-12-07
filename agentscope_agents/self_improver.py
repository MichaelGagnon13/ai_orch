"""
Agent d'auto-amélioration simple qui lit les logs et affiche un résumé des erreurs.
"""

import logging

logger = logging.getLogger(__name__)

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from agentscope.agents import AgentBase
from agentscope.message import Msg

# Configuration du logging
logger = logging.getLogger(__name__)


@dataclass
class ErrorSummary:
    """Résumé d'une erreur détectée."""

    error_type: str
    count: int
    first_occurrence: str
    last_occurrence: str
    sample_message: str
    severity: str


class SelfImproverAgent(AgentBase):
    """
    Agent qui analyse les logs du système et génère des rapports d'erreurs.
    """

    def __init__(
        self,
        name: str = "self_improver",
        model_config_name: str = "claude-sonnet-4-20250514",
        logs_directory: str = "logs",
        **kwargs,
    ):
        """
        Initialise l'agent d'auto-amélioration.

        Args:
            name: Nom de l'agent
            model_config_name: Configuration du modèle à utiliser
            logs_directory: Répertoire contenant les logs à analyser
        """
        super().__init__(name=name, model_config_name=model_config_name, **kwargs)
        self.logs_directory = Path(logs_directory)
        self.error_patterns = {
            "ERROR": r"ERROR\s*[:\-]\s*(.+)",
            "EXCEPTION": r"Exception\s*[:\-]\s*(.+)",
            "FAILED": r"FAILED\s*[:\-]\s*(.+)",
            "TIMEOUT": r"timeout|timed out",
            "CONNECTION": r"connection.*(?:failed|refused|error)",
            "API_ERROR": r"API.*(?:error|failed|limit)",
            "MEMORY": r"memory|out of memory|allocation failed",
        }

    def reply(self, x: Optional[Msg] = None) -> Msg:
        """
        Point d'entrée principal pour analyser les logs.

        Args:
            x: Message d'entrée (optionnel)

        Returns:
            Message contenant le rapport d'erreurs
        """
        try:
            logger.info(f"[{self.name}] Début de l'analyse des logs")

            if not self.logs_directory.exists():
                error_msg = f"Répertoire de logs introuvable: {self.logs_directory}"
                logger.error(f"[{self.name}] {error_msg}")
                return Msg(name=self.name, content=f"❌ {error_msg}", role="assistant")

            # Analyse des logs
            error_summary = self._analyze_logs()

            # Génération du rapport
            report = self._generate_report(error_summary)

            logger.info(f"[{self.name}] Analyse terminée avec succès")

            return Msg(name=self.name, content=report, role="assistant")

        except Exception as e:
            error_msg = f"Erreur lors de l'analyse: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}", exc_info=True)
            return Msg(name=self.name, content=f"❌ {error_msg}", role="assistant")

    def _analyze_logs(self) -> Dict[str, ErrorSummary]:
        """
        Analyse tous les fichiers de logs et extrait les erreurs.

        Returns:
            Dictionnaire des erreurs groupées par type
        """
        error_data = defaultdict(list)
        total_files = 0
        processed_files = 0

        # Recherche de tous les fichiers de logs
        log_files = list(self.logs_directory.glob("**/*.log")) + list(
            self.logs_directory.glob("**/*.txt")
        )

        total_files = len(log_files)
        logger.info(f"[{self.name}] Analyse de {total_files} fichiers de logs")

        for log_file in log_files:
            try:
                self._analyze_log_file(log_file, error_data)
                processed_files += 1
            except Exception as e:
                logger.warning(f"[{self.name}] Erreur lors de l'analyse de {log_file}: {e}")

        logger.info(f"[{self.name}] {processed_files}/{total_files} fichiers traités")

        # Création des résumés d'erreurs
        error_summaries = {}
        for error_type, occurrences in error_data.items():
            if occurrences:
                timestamps = [occ["timestamp"] for occ in occurrences]
                messages = [occ["message"] for occ in occurrences]

                error_summaries[error_type] = ErrorSummary(
                    error_type=error_type,
                    count=len(occurrences),
                    first_occurrence=min(timestamps) if timestamps else "Inconnu",
                    last_occurrence=max(timestamps) if timestamps else "Inconnu",
                    sample_message=messages[0] if messages else "Aucun message",
                    severity=self._determine_severity(error_type, len(occurrences)),
                )

        return error_summaries

    def _analyze_log_file(self, log_file: Path, error_data: Dict[str, List]) -> None:
        """
        Analyse un fichier de log spécifique.

        Args:
            log_file: Chemin vers le fichier de log
            error_data: Dictionnaire pour accumuler les erreurs
        """
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # Extraction du timestamp si présent
                    timestamp = self._extract_timestamp(line)

                    # Recherche de patterns d'erreur
                    for error_type, pattern in self.error_patterns.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            error_data[error_type].append(
                                {
                                    "file": str(log_file),
                                    "line": line_num,
                                    "timestamp": timestamp,
                                    "message": line[:200],  # Limite la longueur
                                }
                            )
                            break  # Première correspondance seulement

        except Exception as e:
            logger.warning(f"[{self.name}] Impossible de lire {log_file}: {e}")

    def _extract_timestamp(self, line: str) -> str:
        """
        Extrait le timestamp d'une ligne de log.

        Args:
            line: Ligne de log

        Returns:
            Timestamp extrait ou timestamp actuel
        """
        # Patterns de timestamp courants
        timestamp_patterns = [
            r"\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}",
            r"\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}:\d{2}",
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        ]

        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group()

        # Utilise le timestamp du fichier ou timestamp actuel
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _determine_severity(self, error_type: str, count: int) -> str:
        """
        Détermine la sévérité d'une erreur.

        Args:
            error_type: Type d'erreur
            count: Nombre d'occurrences

        Returns:
            Niveau de sévérité
        """
        critical_types = {"MEMORY", "EXCEPTION"}
        high_types = {"ERROR", "FAILED"}

        if error_type in critical_types or count > 50:
            return "CRITIQUE"
        elif error_type in high_types or count > 20:
            return "ÉLEVÉ"
        elif count > 5:
            return "MOYEN"
        else:
            return "FAIBLE"

    def _generate_report(self, error_summaries: Dict[str, ErrorSummary]) -> str:
        """
        Génère un rapport lisible des erreurs détectées.

        Args:
            error_summaries: Résumés d'erreurs par type

        Returns:
            Rapport formaté
        """
        if not error_summaries:
            return "✅ Aucune erreur détectée dans les logs analysés."

        # En-tête
        total_errors = sum(summary.count for summary in error_summaries.values())
        report_lines = [
            "📊 RAPPORT D'ANALYSE DES LOGS",
            "=" * 40,
            f"📅 Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"📁 Répertoire: {self.logs_directory}",
            f"🔍 Total erreurs: {total_errors}",
            f"📋 Types d'erreurs: {len(error_summaries)}",
            "",
        ]

        # Tri par sévérité puis par nombre d'occurrences
        severity_order = {"CRITIQUE": 0, "ÉLEVÉ": 1, "MOYEN": 2, "FAIBLE": 3}
        sorted_errors = sorted(
            error_summaries.items(),
            key=lambda x: (severity_order.get(x[1].severity, 999), -x[1].count),
        )

        # Détail des erreurs
        for error_type, summary in sorted_errors:
            severity_emoji = {"CRITIQUE": "🚨", "ÉLEVÉ": "⚠️", "MOYEN": "⚡", "FAIBLE": "ℹ️"}.get(
                summary.severity, "❓"
            )

            report_lines.extend(
                [
                    f"{severity_emoji} {error_type} ({summary.severity})",
                    f"   📊 Occurrences: {summary.count}",
                    f"   🕐 Première: {summary.first_occurrence}",
                    f"   🕐 Dernière: {summary.last_occurrence}",
                    f"   💬 Exemple: {summary.sample_message[:100]}...",
                    "",
                ]
            )

        # Recommandations
        report_lines.extend(
            [
                "🔧 RECOMMANDATIONS:",
                "-" * 20,
            ]
        )

        for error_type, summary in sorted_errors:
            if summary.severity in ["CRITIQUE", "ÉLEVÉ"]:
                if error_type == "MEMORY":
                    report_lines.append("• Vérifier l'utilisation mémoire et optimiser")
                elif error_type == "API_ERROR":
                    report_lines.append("• Vérifier les clés API et les limites de taux")
                elif error_type == "CONNECTION":
                    report_lines.append("• Vérifier la connectivité réseau")
                else:
                    report_lines.append(f"• Investiguer les erreurs {error_type}")

        if not any(s.severity in ["CRITIQUE", "ÉLEVÉ"] for s in error_summaries.values()):
            report_lines.append("• Système globalement stable, surveillance continue recommandée")

        return "\n".join(report_lines)


def create_self_improver_agent(
    name: str = "self_improver",
    model_config_name: str = "claude-sonnet-4-20250514",
    logs_directory: str = "logs",
) -> SelfImproverAgent:
    """
    Factory function pour créer un agent d'auto-amélioration.

    Args:
        name: Nom de l'agent
        model_config_name: Configuration du modèle
        logs_directory: Répertoire des logs

    Returns:
        Instance de SelfImproverAgent
    """
    return SelfImproverAgent(
        name=name, model_config_name=model_config_name, logs_directory=logs_directory
    )


def analyze_logs_simple(logs_directory: str = "logs") -> str:
    """
    Fonction utilitaire pour une analyse simple des logs sans AgentScope.

    Args:
        logs_directory: Répertoire contenant les logs

    Returns:
        Rapport d'analyse
    """
    logs_path = Path(logs_directory)

    if not logs_path.exists():
        return f"❌ Répertoire de logs introuvable: {logs_directory}"

    # Patterns d'erreur simplifiés
    error_patterns = {
        "ERROR": r"ERROR",
        "EXCEPTION": r"Exception",
        "FAILED": r"FAILED",
        "WARNING": r"WARNING",
    }

    error_counts = Counter()
    total_lines = 0

    # Analyse des fichiers
    log_files = list(logs_path.glob("**/*.log")) + list(logs_path.glob("**/*.txt"))

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    total_lines += 1
                    line_upper = line.upper()
                    for error_type in error_patterns:
                        if error_type in line_upper:
                            error_counts[error_type] += 1
        except Exception as e:
            logger.warning(f"Erreur lecture {log_file}: {e}")

    # Génération du rapport simple
    if not error_counts:
        return f"✅ Aucune erreur détectée dans {len(log_files)} fichiers ({total_lines} lignes)"

    report = [
        f"📊 Analyse rapide - {len(log_files)} fichiers, {total_lines} lignes",
        "Erreurs détectées:",
    ]

    for error_type, count in error_counts.most_common():
        report.append(f"  • {error_type}: {count}")

    return "\n".join(report)


if __name__ == "__main__":
    # Test simple sans AgentScope
    print("Test d'analyse des logs:")
    result = analyze_logs_simple()
    print(result)
