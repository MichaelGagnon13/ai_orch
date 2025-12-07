#!/usr/bin/env python3
"""
WebResearcher - Agent de recherche web via DuckDuckGo
"""

import json
import logging
import random
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebResearcher:
    """Agent de recherche web avec DuckDuckGo"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.timeout = 30

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Recherche sur DuckDuckGo

        Args:
            query: Requête de recherche
            max_results: Nombre max de résultats

        Returns:
            Liste de dict avec title, url, snippet
        """
        try:
            headers = {"User-Agent": random.choice(self.USER_AGENTS)}

            # URL DuckDuckGo HTML
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"

            logger.info(f"Recherche: {query}")
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # Parse les résultats
            for result in soup.find_all("div", class_="result")[:max_results]:
                try:
                    title_tag = result.find("a", class_="result__a")
                    snippet_tag = result.find("a", class_="result__snippet")

                    if title_tag:
                        results.append(
                            {
                                "title": title_tag.get_text(strip=True),
                                "url": title_tag.get("href", ""),
                                "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                            }
                        )
                except Exception as e:
                    logger.warning(f"Erreur parsing résultat: {e}")
                    continue

            logger.info(f"✅ {len(results)} résultats trouvés")
            return results

        except requests.Timeout:
            logger.error(f"❌ Timeout après {self.timeout}s")
            return []
        except requests.RequestException as e:
            logger.error(f"❌ Erreur requête: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Erreur inattendue: {e}")
            return []


if __name__ == "__main__":
    # Test
    researcher = WebResearcher()
    results = researcher.search("Python AgentScope", max_results=3)
    print(json.dumps(results, indent=2, ensure_ascii=False))
