# mypy: ignore-errors
"""Base crawler using the central Playwright browser service.

Provides browser lifecycle management via BrowserService. Subclasses
implement start() to configure and launch the browser, then use
self.page for navigation and interaction.

Usage:
    class MyCrawler(BaseCrawler):
        async def start(self):
            headless = await get_module_setting_bool(...)
            await self._launch_browser(headless=headless)

    async with MyCrawler(headless=True) as crawler:
        await crawler.page.goto("https://example.com")
"""

import logging
from abc import ABC
from typing import Any

from app.core.browser import BrowserContext, browser_service

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base for regulatory data crawlers.

    Manages Playwright browser lifecycle through the central
    BrowserService. Subclasses call _launch_browser() in their
    start() method after reading configuration.
    """

    def __init__(self, headless: bool | None = None):
        self._headless_override = headless
        self._browser_ctx: BrowserContext | None = None

    async def start(self) -> None:
        """Initialize and launch the browser.

        Subclasses must implement this to read configuration
        and call self._launch_browser().
        """
        raise NotImplementedError

    async def stop(self) -> None:
        """Clean up browser resources."""
        await self._close_browser()

    async def _launch_browser(self, headless: bool, browsers_path: str = "") -> None:
        """Launch browser via the central BrowserService.

        Args:
            headless: Whether to run in headless mode.
            browsers_path: Optional custom path for Playwright browsers.
        """
        self._browser_ctx = await browser_service.launch(
            headless=headless,
            browsers_path=browsers_path,
        )

    @property
    def page(self) -> Any:
        """Return the Playwright page for navigation and interaction."""
        if self._browser_ctx is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._browser_ctx.page

    async def _close_browser(self) -> None:
        """Close the browser context and clean up resources."""
        if self._browser_ctx is not None:
            await self._browser_ctx.close()
            self._browser_ctx = None

    async def __aenter__(self) -> "BaseCrawler":
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()
