"""运行时配置项读取/写入/删除接口的状态码契约。

修复前：目标配置项不存在时，路由返回 HTTP 200，把错误码塞在响应体
`code: 404` 里；只看 HTTP 状态的调用方会把失败当成功（与
`tests/modules/quality/test_static_data_api.py::test_unknown_dictionary_returns_404`
修的是同一类问题）。本用例钉住「未命中必须是真 404」这个契约。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

BASE = "/api/v1/module-settings"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", f"{BASE}/not_a_module/not_a_key"),
        ("DELETE", f"{BASE}/not_a_module/not_a_key"),
    ],
)
async def test_missing_setting_returns_404(auth_client: AsyncClient, method: str, path: str) -> None:
    """读取或删除不存在的配置项返回 HTTP 404，而不是 200 + body code: 404。"""
    response = await auth_client.request(method, path)

    assert response.status_code == 404, f"{method} {path} expected 404, got {response.status_code}: {response.text}"
    body = response.json()
    assert body.get("code") == 404
    assert "不存在" in body.get("message", "")


async def test_update_missing_setting_returns_404(auth_client: AsyncClient) -> None:
    """更新不存在的配置项同样返回 HTTP 404。"""
    response = await auth_client.put(f"{BASE}/not_a_module/not_a_key", json={"value": "x"})

    assert response.status_code == 404, f"PUT expected 404, got {response.status_code}: {response.text}"
    assert response.json().get("code") == 404
