"""NMPA 备案信息数据采集适配器（CDE 模式重写）。

核心原则（与 CDE crawler 完全一致）：
- 不手动构造反爬参数
- 不缓存动态 Token
- 不直接 requests 硬调接口
- 使用 Playwright 打开页面
- 监听页面自身触发的 XHR/Fetch 响应
- 翻页通过页面操作触发

与 CDE 的区别：
- NMPA 使用瑞数(RS)反爬，需要 headful 模式
- API 端点未知，支持自动发现模式
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright

from app.shared.config_reader import get_module_setting, get_module_setting_bool

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

# ── NMPA URL 配置 ──
# 主入口：数据查询首页（显示所有分类卡片）
NMPA_DATASEARCH_HOME = "https://www.nmpa.gov.cn/datasearch/home-index.html"


# 已知的 NMPA 数据 API URL 关键词（按优先级）
API_MATCH_PATTERNS = [
    "nmpa.gov.cn/datasearch/data",
    "nmpa.gov.cn/datasearch/search",
    "nmpa.gov.cn/datasearch/rest",
    "nmpa.gov.cn/api/datasearch",
    "nmpa.gov.cn/data",
    "nmpa.gov.cn/search",
]


class NmpaRecordAdapter:
    """NMPA 备案信息采集适配器（CDE 模式）。

    使用 Playwright 页面驱动模式：
    1. 打开数据查询页面
    2. 监听页面自身触发的数据 API 响应
    3. 通过点击分页按钮触发翻页

    支持两种模式：
    - 自动发现模式：捕获所有 XHR 响应，记录到日志供分析
    - 生产模式：匹配已知 API 端点模式提取数据
    """

    def __init__(
        self,
        headless: bool | None = None,
        list_url: str | None = None,
        discovery_mode: bool | None = None,
        browsers_path: str | None = None,
        detail_url_template: str | None = None,
    ):
        self._headless_override = headless
        self._list_url_override = list_url
        self._discovery_mode_override = discovery_mode
        self._browsers_path_override = browsers_path
        self._detail_url_template_override = detail_url_template
        # These will be populated in start() after reading from config
        self.headless = False
        self.list_url = ""
        self.discovery_mode = True
        self.browsers_path = ""
        self.detail_url_template = ""
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        # 自动发现模式下记录所有捕获的响应
        self._discovered_responses: list[dict] = []

    # ── 生命周期 ──────────────────────────────────────────

    async def start(self):
        """启动浏览器"""
        # Read config from database if not overridden
        self.headless = self._headless_override
        if self.headless is None:
            self.headless = await get_module_setting_bool(
                "regulatory_tracker", "NMPA_CRAWLER_HEADLESS", False
            )

        self.list_url = self._list_url_override
        if self.list_url is None:
            self.list_url = await get_module_setting(
                "regulatory_tracker",
                "NMPA_BAXX_SEARCH_URL",
                "https://www.nmpa.gov.cn/datasearch/search-result.html",
            )

        self.discovery_mode = self._discovery_mode_override
        if self.discovery_mode is None:
            self.discovery_mode = await get_module_setting_bool(
                "regulatory_tracker", "NMPA_API_DISCOVERY_MODE", True
            )

        self.browsers_path = self._browsers_path_override
        if self.browsers_path is None:
            self.browsers_path = await get_module_setting(
                "regulatory_tracker", "CRAWLER_BROWSERS_PATH", ""
            )

        self.detail_url_template = self._detail_url_template_override
        if self.detail_url_template is None:
            self.detail_url_template = await get_module_setting(
                "regulatory_tracker",
                "NMPA_DETAIL_URL_TEMPLATE",
                "https://www.nmpa.gov.cn/datasearch/search-info?recordId={record_id}",
            )

        if self.browsers_path:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = self.browsers_path

        self._pw = await async_playwright().start()
        launch_kwargs: dict[str, Any] = {
            "headless": self.headless,
            "args": LAUNCH_ARGS,
            "ignore_default_args": ["--enable-automation"],
        }
        self._browser = await self._pw.chromium.launch(**launch_kwargs)
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        await self._context.add_init_script(STEALTH_JS)
        self._page = await self._context.new_page()
        self._discovered_responses = []
        logger.info(
            f"NMPA 浏览器启动 (headless={self.headless}, discovery={self.discovery_mode})"
        )

    async def stop(self):
        """关闭浏览器"""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception as e:
            logger.warning(f"关闭浏览器出错: {e}")
        finally:
            self._context = None
            self._browser = None
            self._pw = None
            self._page = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()

    # ── 响应解析 ──────────────────────────────────────────

    def _is_data_api(self, url: str) -> bool:
        """判断 URL 是否为数据 API 端点"""
        url_lower = url.lower()
        if "nmpa.gov.cn" not in url_lower:
            return False
        for pattern in API_MATCH_PATTERNS:
            if pattern.lower() in url_lower:
                return True
        # 自动发现模式下匹配任何含数据的 API
        if self.discovery_mode:
            return True
        return False

    def _parse_api_response(self, url: str, body: str) -> dict | None:
        """解析数据 API 响应。

        NMPA 的数据响应可能有多种格式：
        - {"data": {"list": [...], "total": N}}
        - {"records": [...], "total": N}
        - {"data": [...], "total": N}
        - {"result": {"data": [...], "totalCount": N}}
        """
        if not body or not body.strip().startswith("{"):
            return None

        try:
            data = json.loads(body)
        except Exception as e:
            logger.debug(f"JSON 解析失败: {e}")
            return None

        # 尝试多种数据结构提取记录
        records = None
        total = 0

        # 模式1: {"data": {"list": [...], "total": N}}
        if isinstance(data.get("data"), dict):
            inner = data["data"]
            if isinstance(inner.get("list"), list):
                records = inner["list"]
                total = inner.get("total", len(records))
            elif isinstance(inner.get("records"), list):
                records = inner["records"]
                total = inner.get("total", len(records))

        # 模式2: {"records": [...], "total": N}
        if records is None and isinstance(data.get("records"), list):
            records = data["records"]
            total = data.get("total", len(records))

        # 模式3: {"data": [...]}
        if records is None and isinstance(data.get("data"), list):
            records = data["data"]
            total = data.get("total", len(records))

        # 模式4: {"result": {"data": [...], "totalCount": N}}
        if records is None and isinstance(data.get("result"), dict):
            inner = data["result"]
            if isinstance(inner.get("data"), list):
                records = inner["data"]
                total = inner.get("totalCount", len(records))
            elif isinstance(inner.get("list"), list):
                records = inner["list"]
                total = inner.get("totalCount", len(records))

        # 模式5: 列表在顶层某个 key 中
        if records is None:
            for key in ("list", "rows", "items", "content", "results"):
                if isinstance(data.get(key), list) and len(data[key]) > 0:
                    records = data[key]
                    total = data.get("total", data.get("totalCount", len(records)))
                    break

        if not records:
            return None

        # 从 URL 解析页码
        page_num = 1
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            for k in ("pageNum", "pageNo", "page", "current", "currentPage"):
                if k in params:
                    page_num = int(params[k][0])
                    break
        except Exception:
            pass

        pages = max(1, (total + 9) // 10)  # 假设每页 10 条

        return {
            "page_num": page_num,
            "records": records,
            "total": total,
            "pages": pages,
            "success": True,
        }

    # ── 核心：页面打开 + 响应监听（CDE 模式）───────────────

    async def _open_page_and_capture(self, timeout_ms: int = 60000) -> dict | None:
        """打开列表页，监听响应，等待数据加载。

        核心逻辑（与 CDE 完全一致）：
        1. 注册响应监听器
        2. 打开页面（networkidle 等待）
        3. 等待数据 API 响应被捕获（asyncio.Event）
        4. 移除监听器
        """
        captured: dict[str, Any] = {"result": None}
        event = asyncio.Event()

        async def on_response(response):
            url = response.url
            if not self._is_data_api(url):
                return
            try:
                body = await response.text()
                # 自动发现模式：记录所有响应
                if self.discovery_mode:
                    self._discovered_responses.append(
                        {
                            "url": url,
                            "status": response.status,
                            "method": response.request.method,
                            "resource_type": response.request.resource_type,
                            "body_len": len(body),
                            "body_head": body[:500],
                        }
                    )
                    logger.info(
                        f"[DISCOVERY] XHR: {response.status} {url[:150]} body_len={len(body)}"
                    )

                result = self._parse_api_response(url, body)
                if result:
                    captured["result"] = result
                    event.set()
                    if not self.discovery_mode:
                        logger.info(
                            f"✅ 捕获数据 API 响应: {url[:120]}, records={len(result['records'])}"
                        )
            except Exception as e:
                logger.debug(f"处理响应异常: {e}")

        self._page.on("response", on_response)

        try:
            logger.info(f"打开 NMPA 页面: {self.list_url}")
            resp = await self._page.goto(
                self.list_url,
                wait_until="networkidle",
                timeout=timeout_ms,
            )
            logger.info(
                f"页面初始响应: {resp.status if resp else 'N/A'}, title={await self._page.title()}"
            )

            # 等待数据响应
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout_ms / 1000)
            except TimeoutError:
                if self.discovery_mode:
                    logger.warning(
                        f"等待数据 API 响应超时。已发现 {len(self._discovered_responses)} 个响应，"
                        f"请检查日志中的 URL 是否是数据 API"
                    )
                else:
                    logger.warning("等待数据 API 响应超时")
        finally:
            self._page.remove_listener("response", on_response)

        return captured["result"]

    async def _click_next_page_and_capture(
        self, timeout_ms: int = 20000
    ) -> dict | None:
        """点击分页按钮并捕获响应（CDE 模式）"""
        captured: dict[str, Any] = {"result": None}
        event = asyncio.Event()

        async def on_response(response):
            url = response.url
            if not self._is_data_api(url):
                return
            try:
                body = await response.text()
                if self.discovery_mode:
                    self._discovered_responses.append(
                        {
                            "url": url,
                            "status": response.status,
                            "method": response.request.method,
                            "body_len": len(body),
                            "body_head": body[:500],
                        }
                    )
                result = self._parse_api_response(url, body)
                if result:
                    captured["result"] = result
                    event.set()
            except Exception as e:
                logger.debug(f"处理响应异常: {e}")

        self._page.on("response", on_response)

        try:
            # 多种选择器尝试找翻页按钮
            next_selectors = [
                "a:has-text('下一页')",
                "button:has-text('下一页')",
                "li.next > a",
                "a.next",
                "[class*='next']:not([class*='disabled'])",
                ".el-pagination button:has-text('>')",
                ".el-pager li:not(.active):last-child",
                ".ant-pagination-next:not(.ant-pagination-disabled)",
                ".pagination .next:not(.disabled)",
                "[class*='pagination'] [class*='next']",
            ]

            clicked = False
            for sel in next_selectors:
                try:
                    el = self._page.locator(sel).first
                    if await el.count() > 0 and await el.is_visible():
                        await el.click()
                        clicked = True
                        logger.info(f"翻页点击: {sel}")
                        break
                except Exception:
                    continue

            if not clicked:
                # JS 查找翻页文本
                clicked_text = await self._page.evaluate("""() => {
                    const elements = document.querySelectorAll('a, button, li, span');
                    for (const el of elements) {
                        const text = (el.textContent || '').trim();
                        if (['下一页', '>', '›', '>>', 'next'].includes(text)) {
                            if (!el.classList.contains('disabled') &&
                                !el.parentElement?.classList.contains('disabled')) {
                                el.click();
                                return text;
                            }
                        }
                    }
                    return null;
                }""")
                if clicked_text:
                    clicked = True
                    logger.info(f"JS 翻页: {clicked_text}")

            if not clicked:
                logger.warning("未找到可点击的翻页按钮")
                return None

            try:
                await asyncio.wait_for(event.wait(), timeout=timeout_ms / 1000)
            except TimeoutError:
                logger.warning("翻页响应等待超时")
        finally:
            self._page.remove_listener("response", on_response)

        return captured["result"]

    # ── 公共接口 ──────────────────────────────────────────

    async def sync_page(self, page_num: int = 1) -> dict[str, Any]:
        """同步指定页码的数据。

        Returns:
            {"page_num": int, "records": list, "total": int, "pages": int,
             "success": bool, "error": str | None}
        """
        if page_num < 1:
            return {
                "page_num": page_num,
                "records": [],
                "total": 0,
                "pages": 0,
                "success": False,
                "error": "页码必须 >= 1",
            }

        try:
            if page_num == 1:
                result = await self._open_page_and_capture()
                if not result:
                    if self.discovery_mode and self._discovered_responses:
                        return {
                            "page_num": 1,
                            "records": [],
                            "total": 0,
                            "pages": 0,
                            "success": False,
                            "error": f"自动发现模式：发现 {len(self._discovered_responses)} 个响应，"
                            f"但未匹配到数据模式。请检查日志",
                        }
                    return {
                        "page_num": 1,
                        "records": [],
                        "total": 0,
                        "pages": 0,
                        "success": False,
                        "error": "未捕获到数据 API 响应",
                    }
                return {**result, "error": None}

            # 翻页模式
            first_result = await self._open_page_and_capture()
            if not first_result:
                return {
                    "page_num": page_num,
                    "records": [],
                    "total": 0,
                    "pages": 0,
                    "success": False,
                    "error": "打开页面失败",
                }

            current = 1
            target_result = None

            for _ in range(page_num - 1):
                await asyncio.sleep(1.5)
                result = await self._click_next_page_and_capture()
                if not result:
                    return {
                        "page_num": page_num,
                        "records": [],
                        "total": 0,
                        "pages": 0,
                        "success": False,
                        "error": f"翻页到第 {current + 1} 页失败",
                    }
                current += 1
                if current == page_num:
                    target_result = result
                    break

            if not target_result:
                return {
                    "page_num": page_num,
                    "records": [],
                    "total": 0,
                    "pages": 0,
                    "success": False,
                    "error": f"未获取到第 {page_num} 页数据",
                }

            return {**target_result, "error": None}

        except Exception as e:
            logger.exception(f"同步第 {page_num} 页异常")
            return {
                "page_num": page_num,
                "records": [],
                "total": 0,
                "pages": 0,
                "success": False,
                "error": str(e),
            }

    async def get_total_pages(self) -> int | None:
        """获取总页数"""
        result = await self._open_page_and_capture()
        if result:
            return result.get("pages")
        return None

    def get_discovered_responses(self) -> list[dict]:
        """获取自动发现模式下捕获的所有响应（用于分析 API 端点）"""
        return self._discovered_responses

    # ── 记录标准化 ────────────────────────────────────────

    def normalize_record(self, record: dict) -> dict[str, Any]:
        """将 NMPA 原始记录标准化。

        字段映射会尝试多种可能的字段名，CC 可根据实际 API 返回调整。
        """
        # ID
        doc_id = str(
            record.get("id")
            or record.get("recordId")
            or record.get("备案编号")
            or record.get("批准文号")
            or ""
        )

        # 标题/名称
        title = (
            record.get("title")
            or record.get("name")
            or record.get("产品名称")
            or record.get("备案产品名称")
            or record.get("药品名称")
            or record.get("genericName")
            or ""
        )

        # 日期
        publish_date = None
        date_str = (
            record.get("publishDate")
            or record.get("publish_date")
            or record.get("createTime")
            or record.get("issueDate")
            or record.get("date")
            or record.get("发布日期")
            or record.get("备案日期")
            or ""
        )
        if isinstance(date_str, str) and date_str.strip():
            for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
                try:
                    publish_date = datetime.strptime(date_str.strip(), fmt).date()
                    break
                except ValueError:
                    continue

        # 状态
        status = (
            record.get("status")
            or record.get("state")
            or record.get("nowstate")
            or record.get("状态")
            or ""
        )

        # 分类
        classification = (
            record.get("classification")
            or record.get("category")
            or record.get("fclass")
            or record.get("分类")
            or ""
        )

        # 原文链接
        original_url = record.get("url") or record.get("originalUrl") or ""
        if not original_url and doc_id:
            original_url = self.detail_url_template.format(record_id=doc_id)

        return {
            "document_id": doc_id,
            "title": title,
            "publish_date": publish_date,
            "status_text": status,
            "classification": classification,
            "original_url": original_url,
            "raw_data": record,
        }
