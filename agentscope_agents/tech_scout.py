"""
Agent de veille technologique qui surveille GitHub trending repos, nouvelles versions PyPI,
tech news avec web search. Utilise GITHUB_TOKEN env var pour GitHub API.
import logging
logger = logging.getLogger(__name__)
Génère rapports quotidiens avec analyse par Claude.
"""

import json
import logging
import os
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import agentscope
import feedparser
import requests
from agentscope.agents import AgentBase
from agentscope.message import Msg
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TechNews:
    """Représente une nouvelle technologique."""

    title: str
    url: str
    summary: str
    source: str
    published_at: datetime
    tags: List[str]
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "tags": self.tags,
            "score": self.score,
        }


@dataclass
class GitHubRepo:
    """Représente un repository GitHub trending."""

    name: str
    full_name: str
    description: str
    url: str
    language: str
    stars: int
    forks: int
    growth_stars: int
    topics: List[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "url": self.url,
            "language": self.language,
            "stars": self.stars,
            "forks": self.forks,
            "growth_stars": self.growth_stars,
            "topics": self.topics,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PyPIRelease:
    """Représente une nouvelle version PyPI."""

    name: str
    version: str
    summary: str
    url: str
    author: str
    published_at: datetime
    download_count: int
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "summary": self.summary,
            "url": self.url,
            "author": self.author,
            "published_at": self.published_at.isoformat(),
            "download_count": self.download_count,
            "tags": self.tags,
        }


@dataclass
class TechReport:
    """Rapport de veille technologique."""

    date: datetime
    github_repos: List[GitHubRepo]
    pypi_releases: List[PyPIRelease]
    tech_news: List[TechNews]
    analysis: str
    trends: Dict[str, Any]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "github_repos": [repo.to_dict() for repo in self.github_repos],
            "pypi_releases": [release.to_dict() for release in self.pypi_releases],
            "tech_news": [news.to_dict() for news in self.tech_news],
            "analysis": self.analysis,
            "trends": self.trends,
            "recommendations": self.recommendations,
        }


class TechScoutAgent(AgentBase):
    """Agent de veille technologique."""

    def __init__(
        self,
        name: str = "TechScout",
        model_config_name: Optional[str] = None,
        github_token: Optional[str] = None,
        output_dir: str = "reports/tech_scout",
        **kwargs,
    ):
        super().__init__(name=name, model_config_name=model_config_name, **kwargs)

        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Configuration des sessions HTTP
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Headers GitHub
        if self.github_token:
            self.session.headers.update(
                {
                    "Authorization": f"token {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )

        # Sources de news tech
        self.tech_feeds = [
            "https://feeds.feedburner.com/oreilly/radar",
            "https://www.infoworld.com/index.rss",
            "https://feeds.arstechnica.com/arstechnica/technology-lab",
            "https://www.wired.com/feed/tag/ai/latest/rss",
            "https://venturebeat.com/feed/",
            "https://techcrunch.com/feed/",
        ]

        # Langages surveillés
        self.watched_languages = [
            "Python",
            "JavaScript",
            "TypeScript",
            "Rust",
            "Go",
            "Java",
            "C++",
            "C#",
            "Swift",
            "Kotlin",
            "Scala",
            "Julia",
            "R",
        ]

        # Packages PyPI populaires
        self.watched_packages = [
            "tensorflow",
            "pytorch",
            "scikit-learn",
            "pandas",
            "numpy",
            "requests",
            "flask",
            "django",
            "fastapi",
            "asyncio",
            "aiohttp",
            "pydantic",
            "sqlalchemy",
            "celery",
            "redis",
        ]

        logger.info(f"TechScoutAgent initialisé: {name}")

    def reply(self, x: Msg) -> Msg:
        """Point d'entrée principal pour traiter les messages."""
        try:
            content = x.content if isinstance(x.content, str) else str(x.content)

            if "daily_report" in content.lower():
                report = self.generate_daily_report()
                return Msg(
                    name=self.name,
                    content=f"Rapport quotidien généré: {report['file_path']}",
                    role="assistant",
                )

            elif "github_trending" in content.lower():
                repos = self.scan_github_trending()
                return Msg(
                    name=self.name,
                    content=f"Trouvé {len(repos)} repositories trending",
                    role="assistant",
                )

            elif "pypi_releases" in content.lower():
                releases = self.scan_pypi_releases()
                return Msg(
                    name=self.name,
                    content=f"Trouvé {len(releases)} nouvelles releases",
                    role="assistant",
                )

            elif "tech_news" in content.lower():
                news = self.scan_tech_news()
                return Msg(
                    name=self.name, content=f"Trouvé {len(news)} nouvelles tech", role="assistant"
                )

            else:
                return Msg(
                    name=self.name,
                    content="Commandes disponibles: daily_report, github_trending, pypi_releases, tech_news",
                    role="assistant",
                )

        except Exception as e:
            logger.error(f"Erreur dans reply: {e}")
            return Msg(
                name=self.name, content=f"Erreur lors du traitement: {str(e)}", role="assistant"
            )

    def scan_github_trending(self, period: str = "daily") -> List[GitHubRepo]:
        """Scanne les repositories GitHub trending."""
        try:
            repos = []

            # API GitHub Search pour repos populaires récents
            query_params = {
                "q": f'created:>{(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")}',
                "sort": "stars",
                "order": "desc",
                "per_page": 50,
            }

            response = self.session.get(
                "https://api.github.com/search/repositories", params=query_params, timeout=30
            )
            response.raise_for_status()

            data = response.json()

            for item in data.get("items", []):
                try:
                    repo = GitHubRepo(
                        name=item["name"],
                        full_name=item["full_name"],
                        description=item.get("description", ""),
                        url=item["html_url"],
                        language=item.get("language", ""),
                        stars=item["stargazers_count"],
                        forks=item["forks_count"],
                        growth_stars=item["stargazers_count"],  # Approximation
                        topics=item.get("topics", []),
                        created_at=datetime.fromisoformat(
                            item["created_at"].replace("Z", "+00:00")
                        ),
                        updated_at=datetime.fromisoformat(
                            item["updated_at"].replace("Z", "+00:00")
                        ),
                    )
                    repos.append(repo)

                except Exception as e:
                    logger.warning(f"Erreur parsing repo {item.get('name', 'unknown')}: {e}")

            logger.info(f"Récupéré {len(repos)} repositories trending")
            return repos

        except Exception as e:
            logger.error(f"Erreur scan GitHub trending: {e}")
            return []

    def scan_pypi_releases(self) -> List[PyPIRelease]:
        """Scanne les nouvelles versions PyPI."""
        try:
            releases = []

            for package_name in self.watched_packages[:10]:  # Limite pour éviter rate limiting
                try:
                    response = self.session.get(
                        f"https://pypi.org/pypi/{package_name}/json", timeout=10
                    )
                    response.raise_for_status()

                    data = response.json()
                    info = data["info"]

                    # Vérifier si la version est récente
                    latest_version = info["version"]
                    releases_data = data.get("releases", {})

                    if latest_version in releases_data:
                        release_info = releases_data[latest_version]
                        if release_info:
                            upload_time = release_info[0].get("upload_time_iso_8601")
                            if upload_time:
                                release_date = datetime.fromisoformat(
                                    upload_time.replace("Z", "+00:00")
                                )

                                # Ne garder que les releases des 7 derniers jours
                                if release_date > datetime.now().replace(
                                    tzinfo=release_date.tzinfo
                                ) - timedelta(days=7):
                                    release = PyPIRelease(
                                        name=info["name"],
                                        version=latest_version,
                                        summary=info.get("summary", ""),
                                        url=info.get("project_url")
                                        or f"https://pypi.org/project/{package_name}/",
                                        author=info.get("author", ""),
                                        published_at=release_date,
                                        download_count=0,  # PyPI ne fournit plus facilement ces stats
                                        tags=(
                                            info.get("keywords", "").split(",")
                                            if info.get("keywords")
                                            else []
                                        ),
                                    )
                                    releases.append(release)

                    time.sleep(0.1)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Erreur récupération package {package_name}: {e}")

            logger.info(f"Récupéré {len(releases)} nouvelles releases PyPI")
            return releases

        except Exception as e:
            logger.error(f"Erreur scan PyPI releases: {e}")
            return []

    def scan_tech_news(self) -> List[TechNews]:
        """Scanne les nouvelles technologiques."""
        try:
            all_news = []

            for feed_url in self.tech_feeds:
                try:
                    feed = feedparser.parse(feed_url)

                    for entry in feed.entries[:10]:  # Limiter à 10 par feed
                        try:
                            # Parser la date
                            published_at = datetime.now()
                            if hasattr(entry, "published_parsed") and entry.published_parsed:
                                published_at = datetime(*entry.published_parsed[:6])
                            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                                published_at = datetime(*entry.updated_parsed[:6])

                            # Ne garder que les news récentes
                            if published_at > datetime.now() - timedelta(days=2):
                                # Extraire tags depuis le titre et summary
                                tags = self._extract_tech_tags(
                                    f"{entry.title} {entry.get('summary', '')}"
                                )

                                news = TechNews(
                                    title=entry.title,
                                    url=entry.link,
                                    summary=entry.get("summary", "")[:500],
                                    source=feed.feed.get("title", "Unknown"),
                                    published_at=published_at,
                                    tags=tags,
                                    score=self._score_news(entry.title, entry.get("summary", "")),
                                )
                                all_news.append(news)

                        except Exception as e:
                            logger.warning(f"Erreur parsing news entry: {e}")

                    time.sleep(0.5)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Erreur parsing feed {feed_url}: {e}")

            # Trier par score et garder les meilleures
            all_news.sort(key=lambda x: x.score, reverse=True)

            logger.info(f"Récupéré {len(all_news)} nouvelles tech")
            return all_news[:50]  # Top 50

        except Exception as e:
            logger.error(f"Erreur scan tech news: {e}")
            return []

    def _extract_tech_tags(self, text: str) -> List[str]:
        """Extrait les tags technologiques d'un texte."""
        tags = []
        text_lower = text.lower()

        # Technologies communes
        tech_keywords = [
            "ai",
            "artificial intelligence",
            "machine learning",
            "ml",
            "deep learning",
            "python",
            "javascript",
            "typescript",
            "rust",
            "go",
            "java",
            "c++",
            "react",
            "vue",
            "angular",
            "node.js",
            "django",
            "flask",
            "fastapi",
            "docker",
            "kubernetes",
            "cloud",
            "aws",
            "azure",
            "gcp",
            "blockchain",
            "cryptocurrency",
            "nft",
            "web3",
            "cybersecurity",
            "security",
            "privacy",
            "database",
            "sql",
            "nosql",
            "mongodb",
            "postgresql",
            "api",
            "rest",
            "graphql",
            "microservices",
            "devops",
            "cicd",
            "automation",
            "mobile",
            "ios",
            "android",
            "flutter",
            "react native",
        ]

        for keyword in tech_keywords:
            if keyword in text_lower:
                tags.append(keyword)

        return list(set(tags))[:10]  # Limiter à 10 tags uniques

    def _score_news(self, title: str, summary: str) -> float:
        """Score une nouvelle selon sa pertinence technologique."""
        score = 0.0
        text = f"{title} {summary}".lower()

        # Mots-clés haute valeur
        high_value_keywords = [
            "breakthrough",
            "revolutionary",
            "new release",
            "launch",
            "announce",
            "open source",
            "github",
            "python",
            "ai",
            "machine learning",
        ]

        for keyword in high_value_keywords:
            if keyword in text:
                score += 1.0

        # Bonus pour languages surveillés
        for lang in self.watched_languages:
            if lang.lower() in text:
                score += 0.5

        return score

    def analyze_with_claude(self, report_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Analyse les données avec Claude pour générer insights et recommandations."""
        try:
            # Préparer le prompt pour Claude
            prompt = f"""
Analyse ce rapport de veille technologique et fournis:
1. Une analyse des tendances principales
2. Des recommandations d'actions

Données:
- {len(report_data.get('github_repos', []))} repositories GitHub trending
- {len(report_data.get('pypi_releases', []))} nouvelles releases PyPI
- {len(report_data.get('tech_news', []))} nouvelles technologiques

Repositories populaires:
{json.dumps([repo['name'] for repo in report_data.get('github_repos', [])[:5]], indent=2)}

Nouvelles releases:
{json.dumps([f"{r['name']} {r['version']}" for r in report_data.get('pypi_releases', [])[:5]], indent=2)}

Top news:
{json.dumps([news['title'][:100] for news in report_data.get('tech_news', [])[:5]], indent=2)}

Format de réponse souhaité:
ANALYSE:
[analyse détaillée des tendances]

RECOMMANDATIONS:
- [recommandation 1]
- [recommandation 2]
- [etc.]
"""

            # Simuler l'analyse Claude (remplacer par vraie intégration)
            analysis = self._generate_mock_analysis(report_data)
            recommendations = self._generate_mock_recommendations(report_data)

            return analysis, recommendations

        except Exception as e:
            logger.error(f"Erreur analyse Claude: {e}")
            return "Analyse indisponible", []

    def _generate_mock_analysis(self, data: Dict[str, Any]) -> str:
        """Génère une analyse mock en attendant l'intégration Claude."""
        trends = []

        # Analyser les langages
        languages = Counter()
        for repo in data.get("github_repos", []):
            if repo["language"]:
                languages[repo["language"]] += 1

        if languages:
            top_lang = languages.most_common(1)[0][0]
            trends.append(f"{top_lang} domine les repositories trending")

        # Analyser les tags des news
        all_tags = []
        for news in data.get("tech_news", []):
            all_tags.extend(news["tags"])

        tag_counts = Counter(all_tags)
        if tag_counts:
            top_tag = tag_counts.most_common(1)[0][0]
            trends.append(f"Forte activité autour de {top_tag}")

        analysis = f"""
Tendances observées ce {datetime.now().strftime('%Y-%m-%d')}:

{chr(10).join(f"• {trend}" for trend in trends)}

Les repositories GitHub montrent une activité soutenue avec {len(data.get('github_repos', []))} projets émergents.
Les releases PyPI indiquent {len(data.get('pypi_releases', []))} mises à jour importantes.
L'écosystème tech reste dynamique avec {len(data.get('tech_news', []))} nouvelles significatives.
"""
        return analysis

    def _generate_mock_recommendations(self, data: Dict[str, Any]) -> List[str]:
        """Génère des recommandations mock."""
        recommendations = []

        if data.get("github_repos"):
            recommendations.append(
                f"Évaluer les {len(data['github_repos'])} nouveaux repositories pour opportunités d'intégration"
            )

        if data.get("pypi_releases"):
            recommendations.append(
                f"Planifier mise à jour des {len(data['pypi_releases'])} packages récemment mis à jour"
            )

        recommendations.extend(
            [
                "Maintenir surveillance des tendances IA et ML",
                "Préparer évaluation des nouvelles technologies identifiées",
                "Programmer revue technique hebdomadaire des findings",
            ]
        )

        return recommendations

    def generate_daily_report(self) -> Dict[str, Any]:
        """Génère le rapport quotidien de veille technologique."""
        try:
            logger.info("Génération du rapport quotidien...")

            # Collecter les données
            github_repos = self.scan_github_trending()
            pypi_releases = self.scan_pypi_releases()
            tech_news = self.scan_tech_news()

            # Analyser les tendances
            trends = self._analyze_trends(github_repos, pypi_releases, tech_news)

            # Préparer les données pour Claude
            report_data = {
                "github_repos": [repo.to_dict() for repo in github_repos],
                "pypi_releases": [release.to_dict() for release in pypi_releases],
                "tech_news": [news.to_dict() for news in tech_news],
                "trends": trends,
            }

            # Analyser avec Claude
            analysis, recommendations = self.analyze_with_claude(report_data)

            # Créer le rapport final
            report = TechReport(
                date=datetime.now(),
                github_repos=github_repos,
                pypi_releases=pypi_releases,
                tech_news=tech_news,
                analysis=analysis,
                trends=trends,
                recommendations=recommendations,
            )

            # Sauvegarder
            report_file = (
                self.output_dir / f"tech_report_{datetime.now().strftime('%Y-%m-%d')}.json"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            # Générer rapport HTML
            html_file = self._generate_html_report(report)

            logger.info(f"Rapport quotidien généré: {report_file}")

            return {
                "json_file": str(report_file),
                "html_file": str(html_file),
                "github_repos_count": len(github_repos),
                "pypi_releases_count": len(pypi_releases),
                "tech_news_count": len(tech_news),
            }

        except Exception as e:
            logger.error(f"Erreur génération rapport quotidien: {e}")
            raise

    def _analyze_trends(
        self, repos: List[GitHubRepo], releases: List[PyPIRelease], news: List[TechNews]
    ) -> Dict[str, Any]:
        """Analyse les tendances dans les données collectées."""
        trends = {}

        # Langages tendance
        languages = Counter()
        for repo in repos:
            if repo.language:
                languages[repo.language] += 1
        trends["top_languages"] = dict(languages.most_common(5))

        # Topics GitHub tendance
        all_topics = []
        for repo in repos:
            all_topics.extend(repo.topics)
        topics = Counter(all_topics)
        trends["top_topics"] = dict(topics.most_common(10))

        # Tags news tendance
        all_tags = []
        for article in news:
            all_tags.extend(article.tags)
        tags = Counter(all_tags)
        trends["top_news_tags"] = dict(tags.most_common(10))

        # Packages PyPI actifs
        package_names = [release.name for release in releases]
        trends["active_packages"] = package_names

        # Métriques générales
        trends["metrics"] = {
            "total_github_repos": len(repos),
            "total_pypi_releases": len(releases),
            "total_tech_news": len(news),
            "avg_repo_stars": sum(repo.stars for repo in repos) / len(repos) if repos else 0,
            "report_date": datetime.now().isoformat(),
        }

        return trends

    def _generate_html_report(self, report: TechReport) -> Path:
        """Génère un rapport HTML lisible."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Tech Scout Report - {report.date.strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .repo {{ border-left: 4px solid #3498db; padding-left: 15px; margin: 15px 0; }}
        .news {{ border-left: 4px solid #e74c3c; padding-left: 15px; margin: 15px 0; }}
        .release {{ border-left: 4px solid #2ecc71; padding-left: 15px; margin: 15px 0; }}
        .analysis {{ background: #fff3cd; padding: 20px; margin: 20px 0; border-radius: 5px; }}
        ul {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>🔍 Tech Scout Report</h1>
    <p><strong>Date:</strong> {report.date.strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="metric">
        <strong>📊 Métriques:</strong>
        {len(report.github_repos)} repos GitHub •
        {len(report.pypi_releases)} releases PyPI •
        {len(report.tech_news)} tech news
    </div>

    <h2>📈 GitHub Trending</h2>
"""

        for repo in report.github_repos[:10]:
            html_content += f"""
    <div class="repo">
        <h3><a href="{repo.url}" target="_blank">{repo.full_name}</a></h3>
        <p>{repo.description}</p>
        <small>⭐ {repo.stars} stars • 🔧 {repo.language} • 🏷️ {', '.join(repo.topics[:5])}</small>
    </div>
"""

        html_content += """
    <h2>📦 PyPI Releases</h2>
"""

        for release in report.pypi_releases[:10]:
            html_content += f"""
    <div class="release">
        <h3><a href="{release.url}" target="_blank">{release.name} v{release.version}</a></h3>
        <p>{release.summary}</p>
        <small>👤 {release.author} • 📅 {release.published_at.strftime('%Y-%m-%d')}</small>
    </div>
"""

        html_content += """
    <h2>📰 Tech News</h2>
"""

        for news in report.tech_news[:10]:
            html_content += f"""
    <div class="news">
        <h3><a href="{news.url}" target="_blank">{news.title}</a></h3>
        <p>{news.summary}</p>
        <small>📰 {news.source} • 📅 {news.published_at.strftime('%Y-%m-%d')} • 🏷️ {', '.join(news.tags[:5])}</small>
    </div>
"""

        html_content += f"""
    <div class="analysis">
        <h2>🧠 Analysis</h2>
        <pre>{report.analysis}</pre>

        <h3>💡 Recommendations</h3>
        <ul>
"""

        for rec in report.recommendations:
            html_content += f"<li>{rec}</li>"

        html_content += """
        </ul>
    </div>

</body>
</html>
"""

        html_file = self.output_dir / f"tech_report_{report.date.strftime('%Y-%m-%d')}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return html_file


def main():
    """Fonction principale pour test."""
    # Initialiser AgentScope
    agentscope.init(
        model_configs=[
            {
                "config_name": "claude_config",
                "model_type": "anthropic_chat",
                "model_name": "claude-3-sonnet-20240229",
            }
        ]
    )

    # Créer l'agent
    agent = TechScoutAgent(name="TechScout", model_config_name="claude_config")

    # Générer un rapport
    result = agent.generate_daily_report()
    print(f"Rapport généré: {result}")


if __name__ == "__main__":
    main()
