"""Web tools: search (READ) and page fetch (READ). All fetched content is wrapped
as untrusted data before the model sees it."""

import asyncio

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

from tools.registry import READ, UNTRUSTED_HEADER, tool

MAX_PAGE_CHARS = 8000


@tool(
    "web_search",
    "Search the web. Returns titles, URLs, and snippets.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "search query"},
            "max_results": {"type": "integer", "description": "default 5"},
        },
        "required": ["query"],
    },
    READ,
)
async def web_search(query: str, max_results: int = 5) -> dict:
    def _search() -> list[dict]:
        with DDGS() as ddgs:
            return [
                {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                for r in ddgs.text(query, max_results=max_results)
            ]

    results = await asyncio.to_thread(_search)
    return {"untrusted_results": results, "note": UNTRUSTED_HEADER.strip()}


@tool(
    "fetch_page",
    "Fetch a web page and return its readable text content.",
    {
        "type": "object",
        "properties": {"url": {"type": "string", "description": "full http(s) URL"}},
        "required": ["url"],
    },
    READ,
)
async def fetch_page(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"error": "only http(s) URLs"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Jarvis)"})
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for el in soup(["script", "style", "noscript"]):
        el.decompose()
    text = " ".join(soup.get_text(" ").split())[:MAX_PAGE_CHARS]
    return {"url": url, "untrusted_content": UNTRUSTED_HEADER + text}
