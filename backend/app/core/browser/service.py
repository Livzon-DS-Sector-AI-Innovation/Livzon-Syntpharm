# mypy: ignore-errors
"""Central Playwright browser service.

Provides a shared BrowserService singleton that wraps common Playwright
lifecycle management — launch args, anti-detection stealth scripts,
viewport/locale/user-agent context, and graceful shutdown.

Usage:
    from app.core.browser import browser_service

    async with browser_service.launch(headless=True) as ctx:
        await ctx.page.goto("https://example.com")
        title = await ctx.page.title()
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import BrowserContext as PWBrowserContext

logger = logging.getLogger(__name__)

LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
]

STEALTH_JS = """
// ── WebDriver 隐藏 ──
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// ── Plugins 伪装 ──
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [1, 2, 3, 4, 5];
        arr.item = (i) => arr[i];
        arr.namedItem = (n) => null;
        arr.refresh = () => {};
        Object.setPrototypeOf(arr, PluginArray.prototype);
        return arr;
    }
});
Object.defineProperty(navigator, 'mimeTypes', {
    get: () => {
        const arr = [1, 2, 3];
        arr.item = (i) => arr[i];
        arr.namedItem = (n) => null;
        Object.setPrototypeOf(arr, MimeTypeArray.prototype);
        return arr;
    }
});

// ── 语言伪装 ──
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
Object.defineProperty(navigator, 'language', {get: () => 'zh-CN'});

// ── Chrome 运行时 ──
window.chrome = {
    runtime: {},
    loadTimes: () => {},
    csi: () => {},
    app: {}
};

// ── 权限 ──
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({state: Notification.permission}) :
        origQuery(parameters)
);

// ── 硬件信息 ──
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});

// ── 平台/厂商 ──
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
Object.defineProperty(navigator, 'vendorSub', {get: () => ''});
Object.defineProperty(navigator, 'productSub', {get: () => '20030107'});

// ── WebGL 伪装 ──
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
};

// ── 清除自动化痕迹 ──
delete navigator.__proto__.webdriver;
"""

VIEWPORT = {"width": 1920, "height": 1080}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

LOCALE = "zh-CN"

TIMEZONE_ID = "Asia/Shanghai"


@dataclass
class BrowserContext:
    """Wraps a Playwright browser, context, and page.

    Created by BrowserService.launch(). Callers use the page
    for navigation and interaction, then call close() or use
    async with to clean up.
    """

    _playwright: Any
    _browser: Browser
    _context: PWBrowserContext
    page: Page

    async def new_page(self) -> Page:
        """Create and return a new configured page within this context."""
        self.page = await self._context.new_page()
        return self.page

    async def close(self) -> None:
        """Gracefully close context, browser, and playwright."""
        try:
            if self._context:
                await self._context.close()
        except Exception as e:
            logger.debug(f"Error closing browser context: {e}")
        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.debug(f"Error closing browser: {e}")
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.debug(f"Error stopping playwright: {e}")

    async def __aenter__(self) -> "BrowserContext":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


class BrowserService:
    """Central service for creating configured Playwright browser contexts.

    All crawlers and browser-automation code should use this service
    instead of manually managing Playwright lifecycle.
    """

    async def launch(
        self,
        headless: bool = True,
        browsers_path: str = "",
        viewport: dict[str, int] | None = None,
        user_agent: str | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
        stealth_js: str | None = None,
    ) -> BrowserContext:
        """Launch a Chromium browser with standard anti-detection configuration.

        Args:
            headless: Run in headless mode. Default True.
            browsers_path: Custom path for Playwright browsers. Uses env var
                           PLAYWRIGHT_BROWSERS_PATH if provided.
            viewport: Override default viewport {width, height}.
            user_agent: Override default user agent string.
            locale: Override default locale.
            timezone_id: Override default timezone.
            stealth_js: Override default stealth script.

        Returns:
            BrowserContext wrapping the browser, context, and page.
        """
        if browsers_path:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path

        pw = await async_playwright().start()

        launch_kwargs: dict[str, Any] = {
            "headless": headless,
            "args": LAUNCH_ARGS,
            "ignore_default_args": ["--enable-automation"],
        }
        browser = await pw.chromium.launch(**launch_kwargs)

        ctx_viewport = viewport or VIEWPORT
        ctx_user_agent = user_agent or USER_AGENT
        ctx_locale = locale or LOCALE
        ctx_timezone = timezone_id or TIMEZONE_ID

        context = await browser.new_context(
            viewport=ctx_viewport,
            user_agent=ctx_user_agent,
            locale=ctx_locale,
            timezone_id=ctx_timezone,
        )

        js = stealth_js or STEALTH_JS
        await context.add_init_script(js)

        page = await context.new_page()
        logger.info(f"Browser launched (headless={headless})")

        return BrowserContext(
            _playwright=pw,
            _browser=browser,
            _context=context,
            page=page,
        )


browser_service = BrowserService()
