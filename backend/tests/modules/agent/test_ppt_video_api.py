"""智能体 API 契约测试：路由可达、响应信封、上传校验、权限码登记。

渲染与 TTS 不在这些用例里跑（外部进程 + 模型），它们由
`test_ppt_video_queue.py`（队列语义）与 TC 走查（真实渲染）覆盖。
"""

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from starlette.requests import Request as StarletteRequest

from app.modules.agent import api as agent_api
from app.modules.agent import service as agent_service
from app.platform.permission.registry import ALL_PERMISSIONS, API_BINDINGS

API = "/api/v1/agent"

#: 只需通过 `_check_ppt_magic`（解析被 mock），内容本身不重要
FAKE_PPTX = b"PK\x03\x04" + b"\x00" * 32
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


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
        # 下载源 PPT：只读，与成片下载同权限
        ("agent:ppt-video:read", "GET", f"{API}/ppt-videos/{'{project_id}'}/source/file"),
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
        # 界面只露中文音色名与一句中文说明，不允许出现 voice_id / English · Bella 这类内部标识
        assert item["description"]
        assert item["voice_id"] not in item["display_name"]
        assert not any(char.isascii() and char.isalpha() for char in item["display_name"])


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


async def test_upload_stops_before_parsing_when_client_disconnected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """解析前就断开：直接 499，不白跑 LibreOffice 转换。"""

    async def _disconnected(_request: StarletteRequest) -> bool:
        return True

    async def _forbidden_create(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("客户端已断开时不应进入解析")

    monkeypatch.setattr(StarletteRequest, "is_disconnected", _disconnected)
    monkeypatch.setattr(agent_service, "create_project", _forbidden_create)

    response = await client.post(
        f"{API}/ppt-videos",
        files={"file": ("deck.pptx", FAKE_PPTX, PPTX_MIME)},
        data={"default_language": "zh"},
    )

    assert response.status_code == 499
    assert response.json()["code"] == 499


async def test_upload_discards_created_project_when_client_disconnected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """解析完成后才发现断开：删掉源 PPT、不投递初稿任务，并靠异常让事务回滚。"""
    from app.modules.agent import api as agent_api

    project = SimpleNamespace(id=uuid.uuid4())
    calls: dict[str, Any] = {"start_script_ai": 0, "deleted": []}
    # 第一次检测（解析前）仍在，第二次（解析后）已断开
    answers = iter([False, True])

    async def _disconnected(_request: StarletteRequest) -> bool:
        return next(answers)

    async def _create(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return project

    async def _start_script_ai(*_args: object, **_kwargs: object) -> None:
        calls["start_script_ai"] += 1

    def _delete_object(module: str, object_key: str) -> None:
        calls["deleted"].append((module, object_key))

    monkeypatch.setattr(StarletteRequest, "is_disconnected", _disconnected)
    monkeypatch.setattr(agent_service, "create_project", _create)
    monkeypatch.setattr(agent_service, "start_script_ai", _start_script_ai)
    monkeypatch.setattr(agent_api, "delete_object", _delete_object)

    response = await client.post(
        f"{API}/ppt-videos",
        files={"file": ("deck.pptx", FAKE_PPTX, PPTX_MIME)},
        data={"default_language": "zh"},
    )

    assert response.status_code == 499
    assert calls["start_script_ai"] == 0
    assert calls["deleted"] == [(agent_api.BUCKET, agent_service.source_object_key(project.id))]


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


async def test_source_download_requires_existing_project(client: AsyncClient) -> None:
    response = await client.get(f"{API}/ppt-videos/{uuid.uuid4()}/source/file")

    assert response.status_code == 404


async def test_page_images_status_requires_existing_project(client: AsyncClient) -> None:
    response = await client.get(f"{API}/ppt-videos/{uuid.uuid4()}/page-images/status")

    assert response.status_code == 404


async def test_regenerate_page_images_requires_existing_project(client: AsyncClient) -> None:
    response = await client.post(f"{API}/ppt-videos/{uuid.uuid4()}/page-images")

    assert response.status_code == 404


def test_page_images_endpoints_are_bound_to_permissions() -> None:
    bindings = {(b.permission_code, b.method, b.route_template) for b in API_BINDINGS}

    assert ("agent:ppt-video:manage", "POST", f"{API}/ppt-videos/{'{project_id}'}/page-images") in bindings
    assert (
        "agent:ppt-video:read",
        "GET",
        f"{API}/ppt-videos/{'{project_id}'}/page-images/status",
    ) in bindings


# ── 媒体流：预览（inline）与下载（attachment）共用同一端点 ──────────────────


def _request(range_header: str | None = None) -> StarletteRequest:
    headers = [(b"range", range_header.encode())] if range_header else []
    return StarletteRequest({"type": "http", "method": "GET", "path": "/", "headers": headers})


def _fake_stat(total: int):
    def _stat(_bucket: str, _key: str) -> int:
        return total

    return _stat


def test_stream_object_inline_disposition(monkeypatch: pytest.MonkeyPatch) -> None:
    # 预览必须用 inline，否则浏览器拿到 attachment 会直接下载
    monkeypatch.setattr(agent_api, "stat_object", _fake_stat(1024))

    response = agent_api._stream_object("k", "video/mp4", _request(), file_name="成片.mp4", inline=True)

    assert response.headers["Content-Disposition"].startswith("inline;")
    assert response.status_code == 200


def test_stream_object_download_stays_attachment(monkeypatch: pytest.MonkeyPatch) -> None:
    # 下载语义不变：不传 inline 时仍是 attachment
    monkeypatch.setattr(agent_api, "stat_object", _fake_stat(1024))

    response = agent_api._stream_object("k", "video/mp4", _request(), file_name="成片.mp4")

    assert response.headers["Content-Disposition"].startswith("attachment;")


def test_stream_object_inline_keeps_range_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    # 播放器拖进度依赖 Range：切 inline 后 206 与 Content-Range 必须照旧
    monkeypatch.setattr(agent_api, "stat_object", _fake_stat(1024))

    response = agent_api._stream_object("k", "video/mp4", _request("bytes=0-99"), file_name="成片.mp4", inline=True)

    assert response.status_code == 206
    assert response.headers["Content-Range"] == "bytes 0-99/1024"
    assert response.headers["Content-Length"] == "100"
