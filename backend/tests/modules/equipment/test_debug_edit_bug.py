from typing import Any
"""[DEBUG-eqedit] 临时诊断测试：设备台账编辑保存无效果 — 反馈环。

模拟用户症状：PUT 更新设备后数据未变化。
诊断完成后此文件应删除。
"""

import uuid

BASE = "/api/v1/equipment/equipments"


async def _create_equipment(auth_client) -> tuple[str, dict[str, Any]]:
    payload = {
        "name": "诊断设备",
        "asset_no": f"DIAG-{uuid.uuid4().hex[:8]}",
        "status": "在用",
        "model": "M-100",
    }
    resp = await auth_client.post(BASE, json=payload)
    assert resp.status_code == 200, f"create failed: {resp.status_code} {resp.text}"
    body = resp.json()
    assert body.get("code") == 200, f"create envelope: {body}"
    return body["data"]["id"], payload


async def test_put_update_persists(auth_client):
    """编辑保存后，GET 复查应返回新值。"""
    eq_id, _ = await _create_equipment(auth_client)

    update = {"name": "诊断设备-已改名", "model": "M-200", "label_no": "L-001"}
    resp = await auth_client.put(f"{BASE}/{eq_id}", json=update)
    assert resp.status_code == 200, f"update failed: {resp.status_code} {resp.text}"
    body = resp.json()
    assert body.get("code") == 200, f"update envelope: {body}"

    resp = await auth_client.get(f"{BASE}/{eq_id}")
    assert resp.status_code == 200, f"get failed: {resp.status_code} {resp.text}"
    data = resp.json()["data"]
    assert data["name"] == "诊断设备-已改名", f"name 未更新: {data['name']}"
    assert data["model"] == "M-200", f"model 未更新: {data['model']}"
    assert data["label_no"] == "L-001", f"label_no 未更新: {data['label_no']}"
