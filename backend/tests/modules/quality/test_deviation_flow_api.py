"""偏差流程端点必须要求登录。

`deviation_flow_router` 挂到 `/api/v1/quality` 之后，这 10 个 handler 最初没有声明
任何认证依赖；`PermissionBindingMiddleware` 只校验「路由是否登记过权限绑定」，
登记了就 `call_next` 放行，因此匿名请求可以直接读写偏差单。这里锁死
「未登录 = 401」，同时锁住错误路径必须返回真实 HTTP 4xx（信封 code 与状态码一致）。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

BASE = "/api/v1/quality/deviation-flow"

_ANY_ID = str(uuid.uuid4())


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", ""),
        ("GET", "/options"),
        ("GET", f"/{_ANY_ID}"),
        ("GET", f"/{_ANY_ID}/attachments"),
        ("GET", f"/attachments/{_ANY_ID}/download"),
        ("DELETE", f"/{_ANY_ID}"),
    ],
)
async def test_anonymous_cannot_read_or_write_deviation_flow(
    anonymous_client: AsyncClient,
    method: str,
    path: str,
) -> None:
    response = await anonymous_client.request(method, f"{BASE}{path}")

    assert response.status_code == 401, response.text


@pytest.mark.xfail(
    strict=True,
    reason=(
        "阻塞：deviation_flow_api 的裸 SQL 打的是 qms.qms_deviation / qms.qms_deviation_attachment，"
        "而 alembic 跑到 head（0092）也没有这两张表，全仓无任何建表 DDL。"
        "表补齐后本用例应转绿（strict 会让它 XPASS 报错，提醒摘掉这个标记）。"
    ),
)
@pytest.mark.usefixtures("db_session")
async def test_missing_deviation_returns_real_404(auth_client: AsyncClient) -> None:
    """原来是 HTTP 200 + 信封 code=404，前端 `apiGet` 当成功处理、拿到 data=null。"""
    response = await auth_client.get(f"{BASE}/{uuid.uuid4()}")

    assert response.status_code == 404, response.text
    assert response.json()["code"] == 404
