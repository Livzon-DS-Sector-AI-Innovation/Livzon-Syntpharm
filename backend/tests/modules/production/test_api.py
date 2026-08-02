# mypy: ignore-errors
from __future__ import annotations

PREFIX = "/api/v1/production"


# ============ Batch Routes ============


async def test_create_batch_api(auth_client, sample_batch_data):
    resp = await auth_client.post(f"{PREFIX}/batches", json=sample_batch_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["batch_no"] == sample_batch_data["batch_no"]


async def test_list_batches_api(auth_client, sample_batch_data):
    await auth_client.post(f"{PREFIX}/batches", json=sample_batch_data)
    resp = await auth_client.get(f"{PREFIX}/batches")
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 1


async def test_get_batch_api(auth_client, sample_batch_data):
    create_resp = await auth_client.post(f"{PREFIX}/batches", json=sample_batch_data)
    batch_id = create_resp.json()["data"]["id"]
    resp = await auth_client.get(f"{PREFIX}/batches/{batch_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == batch_id


async def test_delete_batch_api(auth_client, sample_batch_data):
    create_resp = await auth_client.post(f"{PREFIX}/batches", json=sample_batch_data)
    batch_id = create_resp.json()["data"]["id"]
    resp = await auth_client.delete(f"{PREFIX}/batches/{batch_id}")
    assert resp.status_code == 200

    get_resp = await auth_client.get(f"{PREFIX}/batches/{batch_id}")
    assert get_resp.status_code == 200


# ============ ProductionPlan Routes ============


async def test_create_plan_api(auth_client, sample_production_plan_data):
    resp = await auth_client.post(f"{PREFIX}/plans", json=sample_production_plan_data)
    assert resp.status_code == 200
    assert resp.json()["data"]["plan_name"] == "7月生产计划"


async def test_list_plans_api(auth_client, sample_production_plan_data):
    await auth_client.post(f"{PREFIX}/plans", json=sample_production_plan_data)
    resp = await auth_client.get(f"{PREFIX}/plans")
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 1


async def test_get_plan_api(auth_client, sample_production_plan_data):
    create_resp = await auth_client.post(f"{PREFIX}/plans", json=sample_production_plan_data)
    plan_id = create_resp.json()["data"]["id"]
    resp = await auth_client.get(f"{PREFIX}/plans/{plan_id}")
    assert resp.status_code == 200


async def test_delete_plan_api(auth_client, sample_production_plan_data):
    create_resp = await auth_client.post(f"{PREFIX}/plans", json=sample_production_plan_data)
    plan_id = create_resp.json()["data"]["id"]
    resp = await auth_client.delete(f"{PREFIX}/plans/{plan_id}")
    assert resp.status_code == 200


# ============ ProcessSpec Routes ============


async def test_create_process_spec_api(auth_client, sample_process_spec_data):
    resp = await auth_client.post(f"{PREFIX}/process-specs", json=sample_process_spec_data)
    assert resp.status_code == 200
    assert resp.json()["data"]["product_code"] == "PROD-001"


async def test_delete_process_spec_api(auth_client, sample_process_spec_data):
    create_resp = await auth_client.post(f"{PREFIX}/process-specs", json=sample_process_spec_data)
    spec_id = create_resp.json()["data"]["id"]
    resp = await auth_client.delete(f"{PREFIX}/process-specs/{spec_id}")
    assert resp.status_code == 200


# ============ Anonymous access tests ============


async def test_batches_require_auth(anonymous_client):
    resp = await anonymous_client.get(f"{PREFIX}/batches")
    assert resp.status_code == 401  # Auth enforced — RequiredUser on all endpoints


async def test_plans_require_auth(anonymous_client):
    resp = await anonymous_client.get(f"{PREFIX}/plans")
    assert resp.status_code == 401  # Auth enforced — RequiredUser on all endpoints
