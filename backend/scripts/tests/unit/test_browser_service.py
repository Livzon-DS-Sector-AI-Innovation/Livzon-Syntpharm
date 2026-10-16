# mypy: ignore-errors
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.browser.service import BrowserContext, BrowserService


class FakePage:
    """Fake Playwright Page for testing."""

    def __init__(self):
        self.goto = AsyncMock()
        self.title = AsyncMock(return_value="Test Page")
        self.on = MagicMock()
        self.remove_listener = MagicMock()
        self.locator = MagicMock()
        self.evaluate = AsyncMock(return_value=None)
        self.close = AsyncMock()


class FakeContext:
    """Fake Playwright BrowserContext for testing."""

    def __init__(self):
        self.page = FakePage()
        self.new_page = AsyncMock(return_value=self.page)
        self.add_init_script = AsyncMock()
        self.close = AsyncMock()


class FakeBrowser:
    """Fake Playwright Browser for testing."""

    def __init__(self):
        self.context = FakeContext()
        self.new_context = AsyncMock(return_value=self.context)
        self.close = AsyncMock()


class FakePlaywright:
    """Fake Playwright instance for testing."""

    def __init__(self):
        self.browser = FakeBrowser()
        self.chromium = MagicMock()
        self.chromium.launch = AsyncMock(return_value=self.browser)
        self.stop = AsyncMock()


def _patch_async_playwright(monkeypatch, fake_pw):
    """Patch async_playwright to return a mock with .start() that returns fake_pw."""
    fake = MagicMock()
    fake.start = AsyncMock(return_value=fake_pw)
    monkeypatch.setattr("app.core.browser.service.async_playwright", lambda: fake)


@pytest.fixture
def fake_pw():
    return FakePlaywright()


@pytest.fixture
def browser_service():
    return BrowserService()


@pytest.fixture
async def browser_ctx(fake_pw, monkeypatch):
    _patch_async_playwright(monkeypatch, fake_pw)
    service = BrowserService()
    ctx = await service.launch(headless=True)
    yield ctx
    await ctx.close()


class TestBrowserService:
    """Tests for BrowserService."""

    async def test_launch_creates_browser_context(self, browser_service, fake_pw, monkeypatch):
        _patch_async_playwright(monkeypatch, fake_pw)

        ctx = await browser_service.launch(headless=True)

        assert isinstance(ctx, BrowserContext)
        assert ctx.page is fake_pw.browser.context.page

        await ctx.close()

    async def test_launch_passes_headless_flag(self, browser_service, fake_pw, monkeypatch):
        _patch_async_playwright(monkeypatch, fake_pw)

        await browser_service.launch(headless=True)
        call_kwargs = fake_pw.chromium.launch.call_args[1]
        assert call_kwargs["headless"] is True

    async def test_launch_passes_custom_config(self, browser_service, fake_pw, monkeypatch):
        _patch_async_playwright(monkeypatch, fake_pw)

        await browser_service.launch(
            headless=False,
            viewport={"width": 1024, "height": 768},
            user_agent="TestBot/1.0",
            locale="en-US",
            timezone_id="UTC",
        )

        call_kwargs = fake_pw.browser.new_context.call_args[1]
        assert call_kwargs["viewport"] == {"width": 1024, "height": 768}
        assert call_kwargs["user_agent"] == "TestBot/1.0"
        assert call_kwargs["locale"] == "en-US"
        assert call_kwargs["timezone_id"] == "UTC"

    async def test_launch_injects_stealth_script(self, browser_service, fake_pw, monkeypatch):
        _patch_async_playwright(monkeypatch, fake_pw)

        await browser_service.launch(headless=True)
        fake_pw.browser.context.add_init_script.assert_called_once()

    async def test_launch_sets_browsers_path_env(self, browser_service, fake_pw, monkeypatch):
        _patch_async_playwright(monkeypatch, fake_pw)
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "")
        import os

        await browser_service.launch(headless=True, browsers_path="/custom/path")
        assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == "/custom/path"


class TestBrowserContext:
    """Tests for BrowserContext."""

    async def test_close_cleans_up_resources(self, browser_ctx, fake_pw):
        await browser_ctx.close()

        fake_pw.browser.context.close.assert_called_once()
        fake_pw.browser.close.assert_called_once()
        fake_pw.stop.assert_called_once()

    async def test_context_manager_cleanup(self, browser_service, fake_pw, monkeypatch):
        _patch_async_playwright(monkeypatch, fake_pw)

        async with await browser_service.launch(headless=True) as ctx:
            assert ctx.page is fake_pw.browser.context.page

        fake_pw.browser.context.close.assert_called_once()
        fake_pw.browser.close.assert_called_once()
        fake_pw.stop.assert_called_once()

    async def test_close_handles_exceptions_gracefully(self, browser_ctx, fake_pw):
        fake_pw.browser.context.close.side_effect = Exception("Close error")
        fake_pw.browser.close.side_effect = Exception("Browser error")

        await browser_ctx.close()

    async def test_new_page_creates_page(self, browser_ctx, fake_pw):
        new_page = FakePage()
        fake_pw.browser.context.new_page.return_value = new_page

        result = await browser_ctx.new_page()
        assert result is new_page
        assert browser_ctx.page is new_page
