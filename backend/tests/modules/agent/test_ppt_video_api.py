"""智能体 API 契约测试：路由可达、响应信封、上传校验、权限码登记。

渲染与 TTS 不在这些用例里跑（外部进程 + 模型），它们由
`test_ppt_video_queue.py`（队列语义）与 TC 走查（真实渲染）覆盖。
"""

import uuid

import pytest
from httpx import AsyncClient

from app.platform.permission.registry import ALL_PERMISSIONS, API_BINDINGS

API = "/api/v1/agent"


def test_agent_permission_codes_are_registered() -> None:
    codes = {perm.code for perm in ALL_PERMISSIONS}
    assert {"agent:module:read", "agent:ppt-video:read", "agent:ppt-video:manage"} <= codes


def test_every_agent_endpoint_has_binding() -> None:
    bindings = {(b.permission_code, b.method, b.route_template) for b in API_BINDINGS}
    expected = {
        ("agent:ppt-video:read", "GET", f"{API}/ppt-videos"),
        ("agent:ppt-video:manage", "POST", f"{API}/ppt-videos"),
        ("agent:ppt-video:read", "GET", f"{API}/ppt-videos/{'{project_id}'}"),
        ("agent:ppt-video:manage", "POST", f"{API}/ppt-videos/{'{project_id}'}/render"),
        # AI 讲稿初稿重生成：只填空页，权限复用 manage
        ("agent:ppt-video:manage", "POST", f"{API}/ppt-videos/{'{project_id}'}/script-ai"),
    }
    assert expected <= bindings


async def test_list_voices_returns_bilingual_catalog(client: AsyncClient) -> None:
    response = await client.get(f"{API}/voices")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    items = body["data"]["items"]
    languages = {item["language"] for item in items}
    assert languages == {"zh", "en"}
    for item in items:
        assert item["license"]
        assert item["version"]


async def test_list_voices_filters_by_language(client: AsyncClient) -> None:
    response = await client.get(f"{API}/voices", params={"language": "en"})

    assert response.status_code == 200
    assert {item["language"] for item in response.json()["data"]["items"]} == {"en"}


async def test_upload_rejects_unsupported_extension(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/ppt-videos",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
        data={"default_language": "zh"},
    )

    assert response.status_code == 400
    assert "格式不支持" in response.json()["message"]


async def test_upload_rejects_fake_pptx(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/ppt-videos",
        files={"file": ("fake.pptx", b"plain text pretending to be a deck", "application/pdf")},
        data={"default_language": "zh"},
    )

    assert response.status_code == 400
    assert "不是有效的 .pptx" in response.json()["message"]


async def test_unknown_project_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"{API}/ppt-videos/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.parametrize("path", ["job", "versions"])
async def test_unknown_project_sub_resources_return_404(client: AsyncClient, path: str) -> None:
    response = await client.get(f"{API}/ppt-videos/{uuid.uuid4()}/{path}")

    assert response.status_code == 404


async def test_render_requires_existing_project(client: AsyncClient) -> None:
    response = await client.post(f"{API}/ppt-videos/{uuid.uuid4()}/render")

    assert response.status_code == 404


async def test_version_manifest_requires_existing_version(client: AsyncClient) -> None:
    response = await client.get(f"{API}/ppt-videos/versions/{uuid.uuid4()}/manifest")

    assert response.status_code == 404
