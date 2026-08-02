"""Central Playwright browser service.

Usage:
    from app.core.browser import browser_service

    async with browser_service.launch(headless=True) as ctx:
        await ctx.page.goto("https://example.com")
"""

from .service import BrowserContext, BrowserService, browser_service

__all__ = [
    "BrowserService",
    "BrowserContext",
    "browser_service",
]
