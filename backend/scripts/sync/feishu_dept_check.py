import asyncio
import os
import httpx

APP_ID = os.getenv("FEISHU__PLATFORM__APP_ID")
APP_SECRET = os.getenv("FEISHU__PLATFORM__APP_SECRET")


async def check():
    async with httpx.AsyncClient() as client:
        # 1. 获取 Token
        resp = await client.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": APP_ID, "app_secret": APP_SECRET},
        )
        token = resp.json()["tenant_access_token"]
        print(f"Token: {token[:20]}...")

        # 2. 尝试获取根部门下的子部门 (page_size=50)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            "https://open.feishu.cn/open-apis/contact/v3/departments",
            params={"parent_department_id": "0", "page_size": 50, "department_id_type": "open_department_id"},
            headers=headers,
        )
        data = resp.json()

        if data["code"] == 0:
            items = data.get("data", {}).get("items", [])
            print(f"✅ 成功获取到 {len(items)} 个部门！")
            for item in items[:5]:
                print(f"   - {item['name']} (ID: {item['department_id']})")
        else:
            print(f"❌ 失败: {data['msg']} (Code: {data['code']})")
            print("建议检查：1. 应用是否已发布版本 2. 管理员后台是否授权了通讯录权限")


asyncio.run(check())
