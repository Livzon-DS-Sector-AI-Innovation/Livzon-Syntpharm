# mypy: ignore-errors
from __future__ import annotations


async def test_create_device_config_api(auth_client, sample_device_config_data):
    response = await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["platform_code"] == "zhiheng"


async def test_list_device_configs_api(auth_client, sample_device_config_data):
    await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)

    response = await auth_client.get("/api/v1/energy/devices?platform_code=zhiheng")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] >= 1


async def test_get_device_config_api(auth_client, sample_device_config_data):
    create_resp = await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)
    config_id = create_resp.json()["data"]["id"]

    response = await auth_client.get(f"/api/v1/energy/devices/{config_id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == config_id


async def test_update_device_config_api(auth_client, sample_device_config_data):
    create_resp = await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)
    config_id = create_resp.json()["data"]["id"]

    response = await auth_client.put(
        f"/api/v1/energy/devices/{config_id}",
        json={"device_name": "新名称"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["device_name"] == "新名称"


async def test_delete_device_config_api(auth_client, sample_device_config_data):
    create_resp = await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)
    config_id = create_resp.json()["data"]["id"]

    response = await auth_client.delete(f"/api/v1/energy/devices/{config_id}")
    assert response.status_code == 200

    get_resp = await auth_client.get(f"/api/v1/energy/devices/{config_id}")
    assert get_resp.status_code == 404


async def test_trigger_collection_api(auth_client):
    response = await auth_client.post(
        "/api/v1/energy/collect/trigger",
        json={"platform_code": "zhiheng"},
    )
    assert response.status_code == 200


async def test_list_collect_logs_api(auth_client):
    response = await auth_client.get("/api/v1/energy/collect/logs")
    assert response.status_code == 200


async def test_energy_statistics_returns_list(auth_client):
    """统计接口的 data 是分组列表，不是单个对象（response_model 契约）。"""
    response = await auth_client.get(
        "/api/v1/energy/data/statistics?start_time=2026-01-01T00:00:00&end_time=2026-12-31T00:00:00"
    )
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


async def test_energy_overview_shape(auth_client):
    """总览接口返回 summary/trend/distribution 三部分（具体响应模型）。"""
    response = await auth_client.get(
        "/api/v1/energy/overview?start_time=2026-01-01T00:00:00&end_time=2026-12-31T00:00:00"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert set(data) == {"summary", "trend", "distribution"}
    assert set(data["summary"]) == {
        "total_electricity",
        "total_water",
        "total_steam",
        "total_natural_gas",
    }
