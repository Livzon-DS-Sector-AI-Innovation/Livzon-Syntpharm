import asyncio
import os
import sys
import httpx
import uuid
sys.path.insert(0, '/home/zhuangweizi/Livzon-Syntpharm/backend')
from app.core.database import async_session_factory
from app.modules.hr.models import HrDepartment
from sqlalchemy import select

APP_ID = os.getenv("FEISHU__PLATFORM__APP_ID")
APP_SECRET = os.getenv("FEISHU__PLATFORM__APP_SECRET")

async def sync():
    # 1. 获取 Token
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                                json={"app_id": APP_ID, "app_secret": APP_SECRET})
        token = resp.json()["tenant_access_token"]

        # 2. 获取部门列表 (使用 search 接口)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        resp = await client.post("https://open.feishu.cn/open-apis/contact/v3/departments/search",
                                headers=headers, json={"parent_department_id": "0"})
        depts = resp.json().get("data", {}).get("items", [])

    print(f"✅ 从飞书获取到 {len(depts)} 个部门")

    # 3. 存入数据库
    async with async_session_factory() as db:
        for d in depts:
            exists = await db.execute(select(HrDepartment).where(HrDepartment.feishu_department_id == d["department_id"]))
            if not exists.scalar_one_or_none():
                db.add(HrDepartment(id=uuid.uuid4(), name=d["name"], code=d["department_id"], feishu_department_id=d["department_id"], is_deleted=False))
        await db.commit()
        print("🎉 同步完成！")

asyncio.run(sync())
