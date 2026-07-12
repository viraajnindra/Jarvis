"""Playwright browser tool: VISIBLE Chromium, dedicated Jarvis profile.

The profile lives in data/browser_profile — sign into sites there manually once;
Jarvis never touches your personal browser or saved passwords. Every navigation
is ACT-tier (approval card). Page reads return untrusted-wrapped text.
"""

import asyncio
import logging

import config
from tools.registry import ACT, READ, UNTRUSTED_HEADER, tool

log = logging.getLogger("jarvis.browser")

PROFILE_DIR = config.DATA_DIR / "browser_profile"
MAX_PAGE_CHARS = 8000

_pw = None
_context = None
_lock = asyncio.Lock()


async def _page():
    """Lazy-start the visible browser; reuse one context/page."""
    global _pw, _context
    from playwright.async_api import async_playwright

    async with _lock:
        if _context is not None:
            try:
                return _context.pages[-1] if _context.pages else await _context.new_page()
            except Exception:  # noqa: BLE001 - browser was closed by the user
                _context = None
        if _pw is None:
            _pw = await async_playwright().start()
        _context = await _pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 850},
        )
        return _context.pages[0] if _context.pages else await _context.new_page()


@tool(
    "browser_goto",
    "Navigate the dedicated Jarvis browser window to a URL (visible to the user).",
    {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    ACT,
    summary=lambda a: ("Navigate Jarvis browser", a.get("url", "?"), ""),
)
async def browser_goto(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"error": "only http(s) URLs"}
    page = await _page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    return {"url": page.url, "title": await page.title()}


@tool(
    "browser_read",
    "Read the visible text of the current page in the Jarvis browser.",
    {"type": "object", "properties": {}},
    READ,
)
async def browser_read() -> dict:
    global _context
    if _context is None:
        return {"error": "browser not open; use browser_goto first"}
    page = await _page()
    text = await page.evaluate("document.body ? document.body.innerText : ''")
    text = " ".join(text.split())[:MAX_PAGE_CHARS]
    return {
        "url": page.url,
        "title": await page.title(),
        "untrusted_content": UNTRUSTED_HEADER + text,
    }
