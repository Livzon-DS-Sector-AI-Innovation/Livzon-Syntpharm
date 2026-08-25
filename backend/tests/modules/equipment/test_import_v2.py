"""设备导入 v2 功能测试."""

from typing import Any


def test_download_template_endpoint_exists(client: Any) -> None:
    """测试模板下载接口是否存在并返回成功状态码"""
    response = client.get("/api/v1/equipment/equipments/import/template")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data  # 应该包含 Base64 数据


def test_import_preview_endpoint_path(client: Any) -> None:
    """测试预览接口的路径是否正确（包含 /equipments/）"""
    # 发送一个空的列表进行探测
    response = client.post("/api/v1/equipment/equipments/import/preview", json=[])
    # 即使数据为空，路径正确也应该返回 200 或 422，而不是 404
    assert response.status_code != 404
