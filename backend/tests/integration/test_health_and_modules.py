# mypy: ignore-errors
from httpx import AsyncClient


async def test_health(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_modules(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/system/modules")

    assert response.status_code == 200
    data = response.json()
    codes = {module["code"] for module in data}
    assert "production" in codes
    assert "quality" in codes
    assert "registration" in codes
