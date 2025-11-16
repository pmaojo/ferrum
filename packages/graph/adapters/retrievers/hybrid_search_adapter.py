from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp


class HybridSearchAdapter:
    """Hybrid search combining GraphRAG with SearXNG web search."""

    def __init__(self, searxng_endpoint: str = "http://localhost:4000"):
        self.searxng_endpoint = searxng_endpoint

    async def search_web(
        self, query: str, limit: int = 10, categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search the web using SearXNG."""
        params = {"q": query, "format": "json", "pageno": 1}

        if categories:
            params["categories"] = ",".join(categories)

        async with aiohttp.ClientSession() as session:
            try:
                search_url = urljoin(self.searxng_endpoint, "/search")
                async with session.get(search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])[:limit]
                        return [
                            {
                                "title": result.get("title", ""),
                                "content": result.get("content", ""),
                                "url": result.get("url", ""),
                                "score": 1.0,  # SearXNG doesn't provide scores
                                "source": "web",
                            }
                            for result in results
                        ]
            except Exception as e:
                print(f"Error searching with SearXNG: {e}")
                return []

        return []

    async def hybrid_search(
        self, query: str, kg_results: List[Dict[str, Any]], web_limit: int = 5
    ) -> Dict[str, Any]:
        """Combine knowledge graph results with web search."""
        web_results = await self.search_web(query, limit=web_limit)

        return {
            "query": query,
            "kg_results": kg_results,
            "web_results": web_results,
            "total_results": len(kg_results) + len(web_results),
            "sources": ["knowledge_graph", "web"],
        }
