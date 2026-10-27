"""复现 E2E 场景：test-login → 用返回的 token 创建能耗车间。

用途：e2e 的 global setup 会给测试账号造数，权限体系上线后若测试账号没有授权
会 403。本脚本验证 `test-login` 已经把 E2E 测试账号挂成超管，造数能通过。

运行（需要已迁移的库）：
    DATABASE_URL=... APP_ENV=e2e E2E_AUTH_SECRET=e2e-test-secret \
    uv run python scripts/test/e2e_login_permission_check.py
"""

from __future__ import annotations

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.platform.permission.service.management import sync_registry


async def main() -> int:
    # 对应应用启动时的 lifespan：把 registry 同步进 DB（角色 / 权限码 / 接口绑定）
    await sync_registry()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://e2e") as client:
        login = await client.post(
            "/api/v1/identity/auth/test-login",
            headers={"X-E2E-Secret": "e2e-test-secret"},
        )
        print("test-login:", login.status_code)
        if login.status_code != 200:
            print(login.text)
            return 1

        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/v1/energy/workshops",
            headers=headers,
            json={
                "name": "101车间",
                "code": f"E2E-{uuid.uuid4().hex[:6]}",
                "location": "测试地点",
                "is_active": True,
                "category": "workshop",
            },
        )
        print("create workshop:", created.status_code)
        if created.status_code != 200:
            print(created.text)
            return 1

        listed = await client.get("/api/v1/energy/workshops?category=workshop", headers=headers)
        print("list workshops:", listed.status_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
