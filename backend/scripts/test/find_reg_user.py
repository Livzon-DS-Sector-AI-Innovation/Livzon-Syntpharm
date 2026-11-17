"""临时脚本：找到有 registration:drug:read 权限的活跃用户并打印其 JWT。

用法：docker exec -w /app erp-backend /app/.venv/bin/python scripts/find_reg_user.py
"""

import asyncio
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.platform.identity.models import User
from app.platform.identity.service import generate_jwt


async def main() -> None:
    async with async_session_factory() as db:
        users = (await db.execute(select(User).where(User.status == "active"))).scalars().all()

    for user in users:
        token = generate_jwt(user)
        req = urllib.request.Request(
            "http://localhost:8000/api/v1/registration/drugs",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    print(f"OK {user.name} ({user.id})")
                    print(f"TOKEN={token}")
                    return
        except urllib.error.HTTPError as e:
            print(f"{e.code} {user.name}")
        except Exception as e:  # noqa: BLE001
            print(f"ERR {user.name}: {e}")
    print("NO_USER_WITH_PERMISSION")


asyncio.run(main())
