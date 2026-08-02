# mypy: ignore-errors
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.registration.regulatory_tracker.crawler.base_crawler import BaseCrawler


class FakeBrowserContext:
    """Fake BrowserContext for BaseCrawler tests."""

    def __init__(self):
        self.page = MagicMock()
        self.close = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


class ConcreteCrawler(BaseCrawler):
    """Minimal crawler implementation for testing BaseCrawler lifecycle."""

    def __init__(self, headless: bool | None = None, should_fail_start: bool = False):
        super().__init__(headless=headless)
        self.should_fail_start = should_fail_start
        self.start_called = False
        self.stop_called = False
        self._custom_ctx = None

    async def start(self) -> None:
        self.start_called = True
        if self.should_fail_start:
            raise RuntimeError("Simulated start failure")
        self._custom_ctx = FakeBrowserContext()
        self._browser_ctx = self._custom_ctx

    async def stop(self) -> None:
        self.stop_called = True
        await self._close_browser()


class TestBaseCrawler:
    """Tests for BaseCrawler lifecycle and properties."""

    async def test_context_manager_calls_start_and_stop(self):
        crawler = ConcreteCrawler(headless=True)

        async with crawler as c:
            assert c.start_called is True
            assert c._browser_ctx is not None

        assert crawler.stop_called is True

    async def test_context_manager_cleans_up_on_exception(self):
        crawler = ConcreteCrawler(should_fail_start=True)

        with pytest.raises(RuntimeError, match="Simulated start failure"):
            async with crawler:
                pass

    async def test_page_property_returns_page(self):
        crawler = ConcreteCrawler(headless=True)

        async with crawler as c:
            page = c.page
            assert page is c._browser_ctx.page

    async def test_page_property_raises_before_start(self):
        crawler = ConcreteCrawler(headless=True)

        with pytest.raises(RuntimeError, match="Browser not started"):
            _ = crawler.page

    async def test_page_property_raises_after_close(self):
        crawler = ConcreteCrawler(headless=True)

        async with crawler:
            pass

        with pytest.raises(RuntimeError, match="Browser not started"):
            _ = crawler.page

    async def test_headless_override_stored(self):
        crawler = ConcreteCrawler(headless=False)
        assert crawler._headless_override is False

    async def test_headless_none_default(self):
        crawler = ConcreteCrawler()
        assert crawler._headless_override is None

    async def test_launch_browser_delegates_to_service(self, monkeypatch):
        fake_launch = AsyncMock(return_value=FakeBrowserContext())
        monkeypatch.setattr(
            "app.modules.registration.regulatory_tracker.crawler.base_crawler.browser_service.launch",
            fake_launch,
        )

        crawler = ConcreteCrawler(headless=True)
        await crawler._launch_browser(headless=True)

        fake_launch.assert_called_once_with(headless=True, browsers_path="")
        assert crawler._browser_ctx is not None

    async def test_launch_browser_with_custom_browsers_path(self, monkeypatch):
        fake_launch = AsyncMock(return_value=FakeBrowserContext())
        monkeypatch.setattr(
            "app.modules.registration.regulatory_tracker.crawler.base_crawler.browser_service.launch",
            fake_launch,
        )

        crawler = ConcreteCrawler(headless=True)
        await crawler._launch_browser(headless=False, browsers_path="/custom")

        fake_launch.assert_called_once_with(headless=False, browsers_path="/custom")

    async def test_close_browser_safe_when_not_started(self):
        crawler = ConcreteCrawler(headless=True)
        await crawler._close_browser()  # Should not raise

    async def test_direct_start_and_stop(self):
        crawler = ConcreteCrawler(headless=True)

        await crawler.start()
        assert crawler.start_called is True
        assert crawler._browser_ctx is not None

        await crawler.stop()
        assert crawler.stop_called is True
        assert crawler._browser_ctx is None

    async def test_multiple_close_calls_safe(self):
        crawler = ConcreteCrawler(headless=True)

        async with crawler:
            pass

        await crawler._close_browser()  # Should not raise on redundant close
        await crawler._close_browser()  # Should not raise on redundant close


class TestBaseCrawlerNotImplemented:
    """Tests for abstract BaseCrawler requiring concrete implementation."""

    async def test_abstract_start_raises(self):
        crawler = BaseCrawler(headless=True)

        with pytest.raises(NotImplementedError):
            await crawler.start()

    async def test_stop_without_start_safe(self):
        crawler = BaseCrawler(headless=True)
        await crawler.stop()  # Should not raise
