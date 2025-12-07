"""
Agent de veille technologique compatible AgentScope 1.0.8.
Surveille GitHub trending, PyPI, génère rapports quotidiens.
"""

import json
import logging
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Imports AgentScope 1.0.8 compatibles
try:
    from agentscope.agents.agent import AgentBase
    from agentscope.message import Msg
except ImportError as e:
    logging.error(f"AgentScope import error: {e}")

    # Fallback pour développement sans AgentScope
    class AgentBase:
        def __init__(self, name: str, **kwargs):
            self.name = name

    class Msg:
        def __init__(self, name: str, content: str, role: str = "user"):
            self.name = name
            self.content = content
            self.role = role


# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TechNews:
    """Structure pour une nouvelle technologique."""

    title: str
    url: str
    description: str
    source: str
    date: datetime
    tags: List[str]
    score: int = 0


@dataclass
class GitHubRepo:
    """Structure pour un repository GitHub."""

    name: str
    full_name: str
    description: str
    url: str
    stars: int
    language: str
    growth: int
    topics: List[str]


@dataclass
class PyPIPackage:
    """Structure pour un package PyPI."""

    name: str
    version: str
    description: str
    author: str
    url: str
    release_date: datetime
    downloads: int = 0


@dataclass
class TechReport:
    """Rapport de veille technologique."""

    date: datetime
    trending_repos: List[GitHubRepo]
    new_packages: List[PyPIPackage]
    tech_news: List[TechNews]
    summary: str
    recommendations: List[str]


class TechScoutV2(AgentBase):
    """Agent de veille technologique compatible AgentScope 1.0.8."""

    def __init__(
        self,
        name: str = "TechScout",
        github_token: Optional[str] = None,
        output_dir: Path = Path("reports/tech_scout"),
        languages: List[str] = None,
        categories: List[str] = None,
        **kwargs,
    ):
        """
        Initialise l'agent de veille technologique.

        Args:
            name: Nom de l'agent
            github_token: Token GitHub pour l'API
            output_dir: Répertoire de sortie des rapports
            languages: Langages à surveiller
            categories: Catégories de technologies
        """
        super().__init__(name=name, **kwargs)

        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.languages = languages or ["Python", "JavaScript", "TypeScript", "Rust", "Go", "Java"]
        self.categories = categories or [
            "machine-learning",
            "web-development",
            "devops",
            "blockchain",
            "mobile",
            "data-science",
            "security",
            "ai",
        ]

        # Configuration des sessions HTTP avec retry
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Headers pour GitHub API
        self.github_headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TechScout/1.0",
        }
        if self.github_token:
            self.github_headers["Authorization"] = f"token {self.github_token}"

        logger.info(f"TechScout initialisé - Output: {self.output_dir}")

    def fetch_github_trending(self, time_range: str = "daily") -> List[GitHubRepo]:
        """
        Récupère les repositories GitHub trending.

        Args:
            time_range: daily, weekly, monthly

        Returns:
            Liste des repos trending
        """
        repos = []

        try:
            # GitHub ne fournit pas d'API officielle pour trending
            # On utilise l'API search avec des critères de popularité
            for language in self.languages:
                url = "https://api.github.com/search/repositories"

                # Date pour filtrer les repos récents
                since_date = datetime.now() - timedelta(days=7)
                date_str = since_date.strftime("%Y-%m-%d")

                params = {
                    "q": f"language:{language} created:>{date_str}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10,
                }

                response = self.session.get(
                    url, headers=self.github_headers, params=params, timeout=30
                )
                response.raise_for_status()

                data = response.json()

                for item in data.get("items", []):
                    repo = GitHubRepo(
                        name=item["name"],
                        full_name=item["full_name"],
                        description=item.get("description", ""),
                        url=item["html_url"],
                        stars=item["stargazers_count"],
                        language=item.get("language", ""),
                        growth=item["stargazers_count"],  # Approximation
                        topics=item.get("topics", []),
                    )
                    repos.append(repo)

                # Respecter les limites de l'API
                time.sleep(1)

        except Exception as e:
            logger.error(f"Erreur lors de la récupération GitHub trending: {e}")

        # Déduplication et tri
        unique_repos = {}
        for repo in repos:
            if repo.full_name not in unique_repos:
                unique_repos[repo.full_name] = repo

        sorted_repos = sorted(unique_repos.values(), key=lambda x: x.stars, reverse=True)

        logger.info(f"Récupéré {len(sorted_repos)} repos trending")
        return sorted_repos[:20]  # Top 20

    def fetch_pypi_new_releases(self, days: int = 7) -> List[PyPIPackage]:
        """
        Récupère les nouveaux packages PyPI.

        Args:
            days: Nombre de jours en arrière

        Returns:
            Liste des nouveaux packages
        """
        packages = []

        try:
            # PyPI RSS feed pour les nouveaux packages
            rss_url = "https://pypi.org/rss/packages.xml"

            response = self.session.get(rss_url, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            cutoff_date = datetime.now() - timedelta(days=days)

            for entry in feed.entries[:50]:  # Limiter le nombre
                try:
                    # Parser le titre pour extraire nom et version
                    title_match = re.match(r"(.+?)\s+(\d+\.\d+.*)", entry.title)
                    if not title_match:
                        continue

                    package_name = title_match.group(1).strip()
                    version = title_match.group(2).strip()

                    # Date de publication
                    pub_date = datetime(*entry.published_parsed[:6])

                    if pub_date < cutoff_date:
                        continue

                    # Récupérer les détails du package
                    package_url = f"https://pypi.org/pypi/{package_name}/json"
                    pkg_response = self.session.get(package_url, timeout=10)

                    if pkg_response.status_code == 200:
                        pkg_data = pkg_response.json()
                        info = pkg_data.get("info", {})

                        package = PyPIPackage(
                            name=package_name,
                            version=version,
                            description=info.get("summary", ""),
                            author=info.get("author", ""),
                            url=info.get("home_page", ""),
                            release_date=pub_date,
                        )
                        packages.append(package)

                    # Éviter de surcharger l'API
                    time.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Erreur traitement package {entry.title}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Erreur lors de la récupération PyPI: {e}")

        logger.info(f"Récupéré {len(packages)} nouveaux packages PyPI")
        return packages

    def fetch_tech_news(self) -> List[TechNews]:
        """
        Récupère les actualités technologiques.

        Returns:
            Liste des actualités tech
        """
        news = []

        # Sources de news tech
        sources = [
            {
                "name": "Hacker News",
                "rss": "https://hnrss.org/frontpage",
                "tags": ["general", "startup", "programming"],
            },
            {
                "name": "Python Weekly",
                "rss": "https://www.pythonweekly.com/rss.xml",
                "tags": ["python", "programming"],
            },
            {
                "name": "JavaScript Weekly",
                "rss": "https://javascriptweekly.com/rss",
                "tags": ["javascript", "web-development"],
            },
        ]

        for source in sources:
            try:
                response = self.session.get(source["rss"], timeout=30)
                response.raise_for_status()

                feed = feedparser.parse(response.content)

                for entry in feed.entries[:10]:  # Top 10 par source
                    pub_date = datetime.now()
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])

                    # Filtrer les news récentes (dernière semaine)
                    if pub_date < datetime.now() - timedelta(days=7):
                        continue

                    tech_news = TechNews(
                        title=entry.title,
                        url=entry.link,
                        description=getattr(entry, "summary", "")[:500],
                        source=source["name"],
                        date=pub_date,
                        tags=source["tags"].copy(),
                    )
                    news.append(tech_news)

                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.warning(f"Erreur récupération news {source['name']}: {e}")

        # Tri par date
        news.sort(key=lambda x: x.date, reverse=True)

        logger.info(f"Récupéré {len(news)} actualités tech")
        return news[:30]  # Top 30

    def analyze_trends(self, report: TechReport) -> Tuple[str, List[str]]:
        """
        Analyse les tendances et génère un résumé.

        Args:
            report: Rapport à analyser

        Returns:
            Tuple (résumé, recommandations)
        """
        # Analyse des langages trending
        languages_count = Counter()
        for repo in report.trending_repos:
            if repo.language:
                languages_count[repo.language] += 1

        # Analyse des topics
        topics_count = Counter()
        for repo in report.trending_repos:
            topics_count.update(repo.topics)

        # Analyse des catégories de packages
        categories_count = Counter()
        for pkg in report.new_packages:
            # Classification simple basée sur les mots-clés
            desc_lower = pkg.description.lower()
            if any(word in desc_lower for word in ["ml", "machine learning", "ai"]):
                categories_count["AI/ML"] += 1
            elif any(word in desc_lower for word in ["web", "api", "http"]):
                categories_count["Web"] += 1
            elif any(word in desc_lower for word in ["data", "analysis"]):
                categories_count["Data"] += 1

        # Génération du résumé
        summary_parts = []

        if languages_count:
            top_langs = languages_count.most_common(3)
            langs_str = ", ".join([f"{lang} ({count})" for lang, count in top_langs])
            summary_parts.append(f"Langages tendance: {langs_str}")

        if topics_count:
            top_topics = topics_count.most_common(5)
            topics_str = ", ".join([topic for topic, _ in top_topics])
            summary_parts.append(f"Topics populaires: {topics_str}")

        if categories_count:
            top_cats = categories_count.most_common(3)
            cats_str = ", ".join([f"{cat} ({count})" for cat, count in top_cats])
            summary_parts.append(f"Catégories PyPI: {cats_str}")

        summary = ". ".join(summary_parts) if summary_parts else "Analyse en cours..."

        # Génération des recommandations
        recommendations = []

        if "Python" in languages_count and languages_count["Python"] > 2:
            recommendations.append(
                "Python continue de dominer - surveiller les frameworks émergents"
            )

        if "ai" in [topic.lower() for topic, _ in topics_count.most_common(10)]:
            recommendations.append("L'IA reste un domaine très actif - opportunités d'innovation")

        if "Web" in categories_count:
            recommendations.append("Développement web actif - nouvelles bibliothèques à évaluer")

        if len(report.trending_repos) > 15:
            recommendations.append("Activité GitHub élevée - période favorable pour l'innovation")

        if not recommendations:
            recommendations = ["Continuer la surveillance des tendances technologiques"]

        return summary, recommendations

    def generate_report(self, save: bool = True) -> TechReport:
        """
        Génère un rapport complet de veille technologique.

        Args:
            save: Sauvegarder le rapport sur disque

        Returns:
            Rapport de veille
        """
        logger.info("Génération du rapport de veille technologique...")

        # Collecte des données
        trending_repos = self.fetch_github_trending()
        new_packages = self.fetch_pypi_new_releases()
        tech_news = self.fetch_tech_news()

        # Création du rapport initial
        report = TechReport(
            date=datetime.now(),
            trending_repos=trending_repos,
            new_packages=new_packages,
            tech_news=tech_news,
            summary="",
            recommendations=[],
        )

        # Analyse et enrichissement
        summary, recommendations = self.analyze_trends(report)
        report.summary = summary
        report.recommendations = recommendations

        if save:
            self.save_report(report)

        logger.info(
            f"Rapport généré: {len(trending_repos)} repos, {len(new_packages)} packages, {len(tech_news)} news"
        )
        return report

    def save_report(self, report: TechReport) -> Path:
        """
        Sauvegarde le rapport sur disque.

        Args:
            report: Rapport à sauvegarder

        Returns:
            Chemin du fichier sauvegardé
        """
        # Fichier JSON détaillé
        json_file = self.output_dir / f"tech_report_{report.date.strftime('%Y%m%d_%H%M%S')}.json"

        # Conversion en dict pour sérialisation
        report_dict = {
            "date": report.date.isoformat(),
            "summary": report.summary,
            "recommendations": report.recommendations,
            "trending_repos": [
                {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "url": repo.url,
                    "stars": repo.stars,
                    "language": repo.language,
                    "topics": repo.topics,
                }
                for repo in report.trending_repos
            ],
            "new_packages": [
                {
                    "name": pkg.name,
                    "version": pkg.version,
                    "description": pkg.description,
                    "author": pkg.author,
                    "url": pkg.url,
                    "release_date": pkg.release_date.isoformat(),
                }
                for pkg in report.new_packages
            ],
            "tech_news": [
                {
                    "title": news.title,
                    "url": news.url,
                    "description": news.description,
                    "source": news.source,
                    "date": news.date.isoformat(),
                    "tags": news.tags,
                }
                for news in report.tech_news
            ],
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        # Fichier Markdown pour lecture humaine
        md_file = self.output_dir / f"tech_report_{report.date.strftime('%Y%m%d_%H%M%S')}.md"
        self.save_markdown_report(report, md_file)

        logger.info(f"Rapport sauvegardé: {json_file}")
        return json_file

    def save_markdown_report(self, report: TechReport, file_path: Path):
        """
        Sauvegarde le rapport au format Markdown.

        Args:
            report: Rapport à sauvegarder
            file_path: Chemin du fichier Markdown
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Rapport de Veille Technologique\n\n")
            f.write(f"**Date**: {report.date.strftime('%d/%m/%Y %H:%M')}\n\n")

            f.write(f"## Résumé\n\n{report.summary}\n\n")

            f.write("## Recommandations\n\n")
            for rec in report.recommendations:
                f.write(f"- {rec}\n")
            f.write("\n")

            f.write(f"## Repositories GitHub Trending ({len(report.trending_repos)})\n\n")
            for repo in report.trending_repos[:10]:
                f.write(f"### [{repo.name}]({repo.url})\n")
                f.write(f"**Language**: {repo.language} | **Stars**: {repo.stars}\n\n")
                f.write(f"{repo.description}\n\n")
                if repo.topics:
                    f.write(f"**Topics**: {', '.join(repo.topics)}\n\n")
                f.write("---\n\n")

            f.write(f"## Nouveaux Packages PyPI ({len(report.new_packages)})\n\n")
            for pkg in report.new_packages[:10]:
                f.write(f"### [{pkg.name} {pkg.version}](https://pypi.org/project/{pkg.name})\n")
                f.write(f"**Auteur**: {pkg.author}\n\n")
                f.write(f"{pkg.description}\n\n")
                f.write("---\n\n")

            f.write(f"## Actualités Tech ({len(report.tech_news)})\n\n")
            for news in report.tech_news[:10]:
                f.write(f"### [{news.title}]({news.url})\n")
                f.write(f"**Source**: {news.source} | **Tags**: {', '.join(news.tags)}\n\n")
                f.write(f"{news.description}\n\n")
                f.write("---\n\n")

    def reply(self, x: Msg) -> Msg:
        """
        Interface AgentScope - traite un message et génère une réponse.

        Args:
            x: Message reçu

        Returns:
            Réponse de l'agent
        """
        try:
            if "generate" in x.content.lower() or "rapport" in x.content.lower():
                report = self.generate_report()

                response = f"""Rapport de veille technologique généré avec succès !

📊 **Résumé**: {report.summary}

🔥 **Repositories trending**: {len(report.trending_repos)}
📦 **Nouveaux packages PyPI**: {len(report.new_packages)}
📰 **Actualités tech**: {len(report.tech_news)}

💡 **Recommandations principales**:
{chr(10).join(f"• {rec}" for rec in report.recommendations[:3])}

Rapport sauvegardé dans {self.output_dir}
"""

                return Msg(name=self.name, content=response, role="assistant")

            elif "status" in x.content.lower():
                # Status de l'agent
                latest_report = max(
                    self.output_dir.glob("tech_report_*.json"), key=os.path.getctime, default=None
                )

                if latest_report:
                    mod_time = datetime.fromtimestamp(os.path.getmtime(latest_report))
                    age = datetime.now() - mod_time
                    status = f"Dernier rapport: {mod_time.strftime('%d/%m/%Y %H:%M')} (il y a {age.days} jour(s))"
                else:
                    status = "Aucun rapport généré"

                return Msg(name=self.name, content=f"TechScout Status: {status}", role="assistant")

            else:
                return Msg(
                    name=self.name,
                    content="Commandes disponibles: 'generate rapport', 'status'",
                    role="assistant",
                )

        except Exception as e:
            logger.error(f"Erreur dans reply(): {e}")
            return Msg(
                name=self.name, content=f"Erreur lors du traitement: {str(e)}", role="assistant"
            )


def main():
    """Test et démonstration de l'agent TechScout."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent de veille technologique")
    parser.add_argument("--output", "-o", default="reports/tech_scout", help="Répertoire de sortie")
    parser.add_argument("--token", "-t", help="Token GitHub")
    parser.add_argument("--test", action="store_true", help="Mode test")

    args = parser.parse_args()

    # Création de l'agent
    agent = TechScoutV2(name="TechScout", github_token=args.token, output_dir=Path(args.output))

    if args.test:
        # Test simple
        print("🔍 Test de l'agent TechScout...")

        # Test du message
        test_msg = Msg(name="user", content="generate rapport", role="user")
        response = agent.reply(test_msg)

        print(f"Réponse: {response.content}")

        # Test du status
        status_msg = Msg(name="user", content="status", role="user")
        status_response = agent.reply(status_msg)

        print(f"Status: {status_response.content}")

    else:
        # Génération complète
        print("🚀 Génération du rapport de veille technologique...")
        report = agent.generate_report()

        print("\n✅ Rapport généré:")
        print(f"📊 {report.summary}")
        print(f"🔥 {len(report.trending_repos)} repos trending")
        print(f"📦 {len(report.new_packages)} nouveaux packages")
        print(f"📰 {len(report.tech_news)} actualités")
        print(f"💾 Sauvegardé dans {agent.output_dir}")


if __name__ == "__main__":
    main()
