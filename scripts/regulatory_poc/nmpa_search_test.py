#!/usr/bin/env python3
"""
NMPA 搜索结果页面爬取测试
目标: https://www.nmpa.gov.cn/datasearch/search-result.html
策略: 监听页面网络请求 + 页面 DOM 解析
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/tmp/playwright-browsers"

from playwright.sync_api import sync_playwright

LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--window-size=1920,1080",
]

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
window.chrome = {runtime: {}};
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (p) => (
    p.name === 'notifications' ? Promise.resolve({state: Notification.permission}) : origQuery(p)
);
"""

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    results = {
        "timestamp": datetime.now().isoformat(),
        "target_url": "https://www.nmpa.gov.cn/datasearch/search-result.html",
        "search_keyword": "药品注册",
        "page_title": None,
        "api_responses": [],
        "dom_results": [],
        "pagination_found": False,
        "errors": [],
    }

    print("=" * 70)
    print("NMPA 搜索结果页面爬取测试")
    print("=" * 70)

    pw = sync_playwright().start()

    # ── 启动浏览器 ──
    print("\n[1] 启动反检测浏览器...")
    try:
        browser = pw.chromium.launch(
            headless=True,
            executable_path="/tmp/playwright-browsers/chromium-1223/chrome-linux64/chrome",
            args=LAUNCH_ARGS,
            ignore_default_args=["--enable-automation"],
        )
        print("   ✅ 启动成功 (full chrome)")
    except Exception as e:
        print(f"   ⚠️  full chrome 失败: {e}")
        try:
            browser = pw.chromium.launch(
                headless=True,
                args=LAUNCH_ARGS,
            )
            print("   ✅ 使用默认 chromium")
        except Exception as e2:
            print(f"   ❌ 浏览器启动全部失败: {e2}")
            results["errors"].append(str(e2)[:500])
            pw.stop()
            _save(results)
            return

    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    context.add_init_script(STEALTH_JS)
    page = context.new_page()

    # ── 监听网络请求 ──
    captured_apis = []

    def on_response(response):
        url = response.url
        if "nmpa.gov.cn" not in url:
            return
        ct = response.headers.get("content-type", "")
        status = response.status
        # 记录所有 JSON / XHR 响应
        if "json" in ct or "javascript" in ct or "/api/" in url or "search" in url.lower():
            try:
                body = response.text() if status == 200 else f"[HTTP {status}]"
            except:
                body = "[无法读取body]"
            entry = {
                "url": url[:300],
                "status": status,
                "content_type": ct[:100],
                "body_length": len(body),
                "body_preview": body[:2000] if isinstance(body, str) else str(body)[:2000],
            }
            captured_apis.append(entry)
            print(f"   📡 [{status}] {url[:120]}")

    page.on("response", on_response)

    # ── 访问目标页面 ──
    search_url = "https://www.nmpa.gov.cn/datasearch/search-result.html"
    print(f"\n[2] 访问: {search_url}")
    try:
        resp = page.goto(search_url, wait_until="networkidle", timeout=30000)
        results["page_title"] = page.title()
        print(f"   ✅ 页面标题: {page.title()}")
        print(f"   HTTP 状态: {resp.status if resp else 'N/A'}")
    except Exception as e:
        print(f"   ❌ 页面加载失败: {e}")
        results["errors"].append(f"Page load failed: {str(e)[:300]}")
        # 继续尝试

    # 截图
    _screenshot(page, "01_initial_page")

    # ── 分析页面结构 ──
    print("\n[3] 分析页面结构...")
    page_info = page.evaluate("""() => {
        const info = {
            forms: [],
            inputs: [],
            buttons: [],
            select_elements: [],
            iframes: [],
            scripts_count: document.querySelectorAll('script').length,
            body_text_preview: document.body ? document.body.innerText.substring(0, 500) : '',
        };
        // 表单
        document.querySelectorAll('form').forEach(f => {
            info.forms.push({action: f.action, method: f.method, id: f.id, class: f.className});
        });
        // 输入框
        document.querySelectorAll('input, textarea').forEach(el => {
            info.inputs.push({
                tag: el.tagName, type: el.type, name: el.name,
                id: el.id, placeholder: el.placeholder, value: el.value
            });
        });
        // 按钮
        document.querySelectorAll('button, input[type=submit], .search-btn, [onclick]').forEach(el => {
            info.buttons.push({
                tag: el.tagName, text: el.innerText?.substring(0, 50),
                id: el.id, class: el.className, onclick: el.getAttribute('onclick')
            });
        });
        // select
        document.querySelectorAll('select').forEach(el => {
            const opts = [];
            el.querySelectorAll('option').forEach(o => opts.push({value: o.value, text: o.text}));
            info.select_elements.push({id: el.id, name: el.name, options: opts.slice(0, 20)});
        });
        // iframes
        document.querySelectorAll('iframe').forEach(f => {
            info.iframes.push({src: f.src, id: f.id, name: f.name});
        });
        return info;
    }""")
    print(f"   表单数: {len(page_info.get('forms', []))}")
    print(f"   输入框数: {len(page_info.get('inputs', []))}")
    print(f"   按钮数: {len(page_info.get('buttons', []))}")
    print(f"   下拉框数: {len(page_info.get('select_elements', []))}")
    print(f"   iframe数: {len(page_info.get('iframes', []))}")
    print(f"   script数: {page_info.get('scripts_count', 0)}")

    results["page_structure"] = page_info

    # 打印输入框信息
    for inp in page_info.get("inputs", []):
        print(
            f"   📝 input: type={inp['type']} name={inp['name']} id={inp['id']} placeholder={inp.get('placeholder', '')}"
        )

    for sel in page_info.get("select_elements", []):
        print(f"   📋 select: id={sel['id']} name={sel['name']} options={len(sel['options'])}")

    # ── 尝试搜索 ──
    keyword = "药品注册"
    print(f"\n[4] 尝试搜索关键词: {keyword}")

    # 先检查是否有搜索输入框
    search_input = page.query_selector(
        'input[type="text"], input[name*="keyword"], input[name*="search"], input.search-input, #keyword, .search-txt input'
    )
    if search_input:
        print(f"   ✅ 找到搜索框")
        search_input.fill(keyword)
        time.sleep(1)

        # 找搜索按钮
        search_btn = page.query_selector(
            'button[type="submit"], .search-btn, input[type="submit"], button:has-text("搜索"), button:has-text("查询"), .search-button'
        )
        if search_btn:
            print(f"   ✅ 找到搜索按钮，点击...")
            search_btn.click()
        else:
            print(f"   ⚠️  未找到搜索按钮，尝试回车...")
            search_input.press("Enter")

        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass

        results["page_title_after_search"] = page.title()
        print(f"   搜索后页面标题: {page.title()}")
        print(f"   搜索后URL: {page.url}")
        _screenshot(page, "02_after_search")
    else:
        print(f"   ⚠️  未找到搜索输入框，尝试直接带参数访问...")
        # 尝试直接带参数访问
        param_urls = [
            f"https://www.nmpa.gov.cn/datasearch/search-result.html?keyword={keyword}",
            f"https://www.nmpa.gov.cn/datasearch/search-result.html?searchWord={keyword}",
            f"https://www.nmpa.gov.cn/datasearch/search-result.html?q={keyword}",
            f"https://www.nmpa.gov.cn/datasearch/search-result.html?wd={keyword}",
        ]
        for purl in param_urls:
            print(f"   尝试: {purl}")
            try:
                resp = page.goto(purl, wait_until="networkidle", timeout=15000)
                results["page_title"] = page.title()
                print(f"   标题: {page.title()}")
                _screenshot(page, "02_param_search")
                if page.title() and "搜索" in page.title():
                    break
            except Exception as e:
                print(f"   ❌ {str(e)[:100]}")

    # ── 提取搜索结果 ──
    print("\n[5] 提取搜索结果...")
    search_results = page.evaluate("""() => {
        const results = [];
        // 尝试多种常见的搜索结果选择器
        const selectors = [
            '.search-result-item', '.result-item', '.list-item',
            '.data-list li', '.search-list li', '.result-list li',
            'ul.result li', '.news-list li', '.datasearch-result li',
            '.search-result li', '.list-content li', '.dataList li',
            '.result-list .item', '.search_content .item',
            'table tbody tr', '.table-list tr',
        ];
        for (const sel of selectors) {
            const els = document.querySelectorAll(sel);
            if (els.length > 0) {
                els.forEach(el => {
                    results.push({
                        selector: sel,
                        text: el.innerText?.substring(0, 300),
                        html: el.innerHTML?.substring(0, 500),
                    });
                });
                break;
            }
        }
        // 如果都没找到，获取主体内容
        if (results.length === 0) {
            const main = document.querySelector('.search-result, .result, .main-content, #content, .container, main, article');
            if (main) {
                results.push({
                    selector: 'main-content',
                    text: main.innerText?.substring(0, 2000),
                    html: main.innerHTML?.substring(0, 3000),
                });
            }
        }
        return results;
    }""")

    results["dom_results"] = search_results
    print(f"   找到 {len(search_results)} 条结果")
    for i, r in enumerate(search_results[:5]):
        print(f"   [{i + 1}] selector={r.get('selector', '?')}")
        text = r.get("text", "")[:150]
        print(f"       {text}")

    # ── 检查所有捕获的 API ──
    print(f"\n[6] 共捕获 {len(captured_apis)} 个 API 响应")
    results["api_responses"] = captured_apis

    for i, api in enumerate(captured_apis):
        print(f"\n   API #{i + 1}:")
        print(f"   URL: {api['url']}")
        print(f"   Status: {api['status']}, Type: {api['content_type']}")
        print(f"   Body length: {api['body_length']}")
        if api["body_length"] > 0 and api["body_length"] < 5000:
            print(f"   Body: {api['body_preview'][:500]}")

    # ── 尝试翻页 ──
    print("\n[7] 检查分页...")
    pagination_info = page.evaluate("""() => {
        const pagers = document.querySelectorAll('.pagination, .pager, .page-bar, .page-nav, .page, .pagebar, [class*=paginat], [class*=page-]');
        const info = [];
        pagers.forEach(p => {
            info.push({
                class: p.className,
                html: p.innerHTML?.substring(0, 500),
                text: p.innerText?.substring(0, 200),
            });
        });
        // 也检查 "下一页" 链接
        const nextLinks = document.querySelectorAll('a:has-text("下一页"), a:has-text("下页"), .next, [class*=next]');
        nextLinks.forEach(a => {
            info.push({type: 'next-link', text: a.innerText, href: a.href});
        });
        return info;
    }""")
    results["pagination"] = pagination_info
    if pagination_info:
        results["pagination_found"] = True
        for p in pagination_info:
            print(f"   📄 {p.get('class', p.get('type', '?'))}: {p.get('text', '')[:100]}")
    else:
        print("   未找到分页元素")

    # ── 保存结果 ──
    _save(results)
    print(f"\n{'=' * 70}")
    print(f"✅ 测试完成，结果已保存到 nmpa_search_test_result.json")
    print(f"{'=' * 70}")

    context.close()
    browser.close()
    pw.stop()


def _screenshot(page, name):
    path = os.path.join(OUTPUT_DIR, f"nmpa_{name}.png")
    try:
        page.screenshot(path=path, full_page=False)
        print(f"   📸 截图: {path}")
    except Exception as e:
        print(f"   ⚠️  截图失败: {e}")


def _save(data):
    path = os.path.join(OUTPUT_DIR, "nmpa_search_test_result.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
