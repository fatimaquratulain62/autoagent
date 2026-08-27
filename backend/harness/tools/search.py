"""Web search tool using Tavily API."""
import json
from typing import ClassVar, Optional

import httpx
from pydantic import BaseModel, Field

from backend.harness.tools.base import BaseTool, register_tool
from models.schemas import get_settings

settings = get_settings()


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query to execute")
    max_results: int = Field(8, description="Maximum number of results to return (1-20)", ge=1, le=20)


class WebSearchTool(BaseTool):
    name: ClassVar[str] = "web_search"
    description: ClassVar[str] = (
        "Search the web for current information. Use this when you need recent facts, "
        "news, data, or to find URLs to browse. Returns titles, URLs, and snippets."
    )
    input_schema: ClassVar[type[BaseModel]] = WebSearchInput

    async def run(self, query: str, max_results: int = 8) -> str:
        if not settings.TAVILY_API_KEY:
            # Fallback: use DuckDuckGo HTML scraping
            return await self._duckduckgo_search(query, max_results)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        if data.get("answer"):
            results.append(f"Quick answer: {data['answer']}\n")

        for r in data.get("results", []):
            results.append(
                f"Title: {r.get('title', 'N/A')}\n"
                f"URL: {r.get('url', '')}\n"
                f"Snippet: {r.get('content', '')[:200]}\n"
                f"Score: {r.get('score', 0):.2f}"
            )

        return "\n\n---\n\n".join(results) if results else "No results found."

    async def _duckduckgo_search(self, query: str, max_results: int) -> str:
        """Fallback search using DuckDuckGo lite."""
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AutoAgent/1.0)"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for result in soup.select(".result")[:max_results]:
            title_el = result.select_one(".result__title a")
            snippet_el = result.select_one(".result__snippet")
            if title_el:
                title = title_el.get_text(strip=True)
                url = title_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                results.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}")

        return "\n\n---\n\n".join(results) if results else "No results found."


register_tool(WebSearchTool())