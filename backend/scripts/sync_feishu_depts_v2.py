import asyncio, os, sys, httpx, uuid
sys.path.insert(0, '/home/zhuangweizi/Livzon-Syntpharm/backend')
from app.core.database import async_session_factory
from app.modules.hr.models import HrDepartment
from sqlalchemy import select

APP_ID = os.getenv("FEISHU__PLATFORM__APP_ID")
APP_SECRET = os.getenv("FEISHU__PLATFORM__APP_SECRET")

async def sync():
    async with httpx.AsyncClient() as client:
        # 1. Get Token
        resp = await client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", 
                                json={"app_id": APP_ID, "app_secret": APP_SECRET})
        token = resp.json()["tenant_access_token"]
        
        # 2. Get Scoped Departments (The two companies)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("https://open.feishu.cn/open-apis/contact/v3/scopes", headers=headers)
        scopes = resp.json().get("data", {}).get("department_scopes", [])
        
        all_depts = []
        for scope in scopes:
            dept_id = scope["department_id"]
            # Recursively fetch children
            queue = [dept_id]
            while queue:
                current_id = queue.pop(0)
                resp = await client.get(f"https://open.feishu.cn/open-apis/contact/v3/departments/{current_id}", 
                                       params={"department_id_type": "open_department_id"}, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    if data:
                        all_depts.append({"id": data["department_id"], "name": data["name"]})
                        # Get children
                        resp_children = await client.get("https://open.feishu.cn/open-apis/contact/v3/departments", 
                                                       params={"parent_department_id": current_id, "page_size": 50}, headers=headers)
                        children = resp_children.json().get("data", {}).get("items", [])
                        for c in children:
                            queue.append(c["department_id"])

        print(f"✅ 从飞书获取到 {len(all_depts)} 个部门")
        
        # 3. Save to DB
        async with async_session_factory() as db:
            for d in all_depts:
                exists = await db.execute(select(HrDepartment).where(HrDepartment.feishu_department_id == d["id"]))
                if not exists.scalar_one_or_none():
                    db.add(HrDepartment(id=uuid.uuid4(), name=d["name"], code=d["id"], feishu_department_id=d["id"], is_deleted=False))
            await db.commit()
            print("🎉 部门同步完成！")

asyncio.run(sync())
