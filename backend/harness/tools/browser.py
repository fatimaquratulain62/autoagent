"""URL browsing tool using httpx + BeautifulSoup."""
import re
from typing import ClassVar

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from backend.harness.tools.base import BaseTool, register_tool


class BrowseUrlInput(BaseModel):
    url: str = Field(..., description="The URL to fetch and extract text from")


class BrowseUrlTool(BaseTool):
    name: ClassVar[str] = "browse_url"
    description: ClassVar[str] = (
        "Fetch a webpage and extract its main text content. Use after web_search to read "
        "a specific page. Returns the page title and cleaned text content."
    )
    input_schema: ClassVar[type[BaseModel]] = BrowseUrlInput

    async def run(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        async with httpx.AsyncClient(
            timeout=30,
            headers=headers,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

            if "json" in content_type:
                return f"JSON response:\n{resp.text[:5000]}"

            soup = BeautifulSoup(resp.text, "lxml")

            # Remove noise
            for tag in soup(["script", "style", "nav", "footer", "header",
                              "aside", "form", "noscript", "iframe", "svg"]):
                tag.decompose()

            title = soup.find("title")
            title_text = title.get_text(strip=True) if title else "No title"

            # Try to get main content
            main = (
                soup.find("main")
                or soup.find("article")
                or soup.find(id=re.compile(r"(content|main|article)", re.I))
                or soup.find("body")
            )

            if main:
                text = main.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Collapse whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned = "\n".join(lines)

            # Truncate — keep short to preserve context window
            word_count = len(cleaned.split())
            if len(cleaned) > 3000:
                cleaned = cleaned[:3000] + "\n\n[... content truncated. Use http_request or run_python to fetch more ...]"

            return (
                f"Title: {title_text}\n"
                f"URL: {url}\n"
                f"Word count: {word_count}\n\n"
                f"{cleaned}"
            )


register_tool(BrowseUrlTool())