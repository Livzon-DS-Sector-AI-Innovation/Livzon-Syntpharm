"""从飞书同步部门数据到本地数据库。"""
import asyncio
import os
import sys
sys.path.insert(0, '/home/zhuangweizi/Livzon-Syntpharm/backend')

from app.core.database import async_session_factory
from app.modules.hr.models import HrDepartment
from sqlalchemy import select
import uuid
import httpx

APP_ID = os.getenv("FEISHU__PLATFORM__APP_ID")
APP_SECRET = os.getenv("FEISHU__PLATFORM__APP_SECRET")

if not APP_ID or not APP_SECRET:
    print("❌ 错误: 请在 .env 文件中设置 FEISHU__PLATFORM__APP_ID 和 FEISHU__PLATFORM__APP_SECRET")
    sys.exit(1)

async def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        data = resp.json()
        if data.get("code") == 0:
            return data["tenant_access_token"]
        else:
            raise Exception(f"获取 Token 失败: {data}")

async def sync_departments():
    print("🔄 开始从飞书同步部门...")

    token = await get_tenant_access_token()

    # 获取部门列表
    url = "https://open.feishu.cn/open-apis/contact/v3/departments/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"parent_department_id": "0"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        data = resp.json()

    if data.get("code") != 0:
        print(f"❌ 获取部门失败: {data}")
        return

    all_depts = []
    items = data.get("data", {}).get("items", [])
    for item in items:
        all_depts.append({
            "id": item["department_id"],
            "name": item["name"],
            "parent_id": item.get("parent_department_id")
        })

    print(f"✅ 从飞书获取到 {len(all_depts)} 个部门")

    # 写入本地数据库
    async with async_session_factory() as db:
        for dept_data in all_depts:
            result = await db.execute(select(HrDepartment).where(HrDepartment.feishu_department_id == dept_data["id"]))
            existing = result.scalar_one_or_none()

            if not existing:
                new_dept = HrDepartment(
                    id=uuid.uuid4(),
                    name=dept_data["name"],
                    code=dept_data["id"],
                    feishu_department_id=dept_data["id"],
                    is_deleted=False
                )
                db.add(new_dept)
                print(f"  ➕ 新增部门: {dept_data['name']}")

        await db.commit()
        print("🎉 部门同步完成！")

if __name__ == "__main__":
    asyncio.run(sync_departments())
