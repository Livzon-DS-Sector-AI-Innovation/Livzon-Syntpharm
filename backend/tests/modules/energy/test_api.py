# mypy: ignore-errors
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_device_config_api(auth_client, sample_device_config_data):
    response = await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["platform_code"] == "zhiheng"


@pytest.mark.asyncio
async def test_list_device_configs_api(auth_client, sample_device_config_data):
    await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)

    response = await auth_client.get("/api/v1/energy/devices?platform_code=zhiheng")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_get_device_config_api(auth_client, sample_device_config_data):
    create_resp = await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)
    config_id = create_resp.json()["data"]["id"]

    response = await auth_client.get(f"/api/v1/energy/devices/{config_id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == config_id


@pytest.mark.asyncio
async def test_update_device_config_api(auth_client, sample_device_config_data):
    create_resp = await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)
    config_id = create_resp.json()["data"]["id"]

    response = await auth_client.put(
        f"/api/v1/energy/devices/{config_id}",
        json={"device_name": "新名称"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["device_name"] == "新名称"


@pytest.mark.asyncio
async def test_delete_device_config_api(auth_client, sample_device_config_data):
    create_resp = await auth_client.post("/api/v1/energy/devices", json=sample_device_config_data)
    config_id = create_resp.json()["data"]["id"]

    response = await auth_client.delete(f"/api/v1/energy/devices/{config_id}")
    assert response.status_code == 200

    get_resp = await auth_client.get(f"/api/v1/energy/devices/{config_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_trigger_collection_api(auth_client):
    response = await auth_client.post(
        "/api/v1/energy/collect/trigger",
        json={"platform_code": "zhiheng"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_collect_logs_api(auth_client):
    response = await auth_client.get("/api/v1/energy/collect/logs")
    assert response.status_code == 200
