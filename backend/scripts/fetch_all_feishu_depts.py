import asyncio, os, httpx

APP_ID = os.getenv("FEISHU__PLATFORM__APP_ID")
APP_SECRET = os.getenv("FEISHU__PLATFORM__APP_SECRET")

async def fetch():
    async with httpx.AsyncClient() as client:
        # 1. Get Token
        resp = await client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", 
                                json={"app_id": APP_ID, "app_secret": APP_SECRET})
        token = resp.json()["tenant_access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Try to get departments by searching for common keywords in your company
        # Since we know the company names, let's try to find their IDs first or just list all accessible depts
        all_depts = []
        
        # Use search endpoint which is often more permissive than list
        async def search_depts(parent_id="0"):
            payload = {"parent_department_id": parent_id, "page_size": 50}
            resp = await client.post("https://open.feishu.cn/open-apis/contact/v3/departments/search", 
                                   headers=headers, json=payload)
            data = resp.json()
            if data.get("code") == 0:
                items = data.get("data", {}).get("items", [])
                for item in items:
                    all_depts.append(item["name"])
                    # Recursively get children
                    await search_depts(item["department_id"])
        
        # Start from root. If 40004, we try the specific IDs from the screenshot if we can find them.
        # But first, let's try a broad search for "车间" or "部"
        print("🔍 正在尝试从飞书拉取部门结构...")
        
        # Let's try to get the list of departments under the two known companies.
        # Since we don't have their IDs directly from the env, we'll try to find them by name.
        # Or we can try to list all departments the app has access to.
        
        # Alternative: Use the 'get_department_list' with a known parent if we had one.
        # Let's try the search endpoint with an empty parent to see if it returns the top-level ones.
        
        await search_depts("0")
        
        if not all_depts:
            print("⚠️ 根节点查询为空。尝试通过关键词搜索特定部门...")
            # Try searching for "珠海保税区丽珠合成制药有限公司"
            # This requires a different endpoint or logic. 
            
        print(f"\n📊 飞书部门统计:")
        print(f"   总共发现: {len(all_depts)} 个部门/车间")
        if all_depts:
            print("\n--- 部门列表 ---")
            for d in sorted(set(all_depts)):
                print(f"   - {d}")

asyncio.run(fetch())
