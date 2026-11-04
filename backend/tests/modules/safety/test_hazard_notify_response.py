"""回归测试：通知 / 内容类端点的响应体必须匹配其声明的 ``response_model``。

历史 bug（2026-11 审计发现）：``notify-reviewer`` 与 ``notify-rectification``
用 ``build_response(data={"level": ..., ...})`` 返回共享 ``ApiResponse``，而路由声明
``response_model=HazardApiResponse``（其 ``data`` 类型是 ``HazardReportResponse``）。
FastAPI 在响应序列化阶段校验失败 → 返回 500，而业务动作（飞书通知入队）已经执行，
用户看到"失败"再点一次就会重复推送。

修复方式：为这些端点定义专用响应模型。这些用例通过真实的 HTTP 路径断言
状态码与 ``data`` 结构，避免同类问题再次回归。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.api import hazards as hazards_api
from app.modules.safety.models import HazardReport
from app.modules.safety.service import sop_generator


@pytest.fixture
def stub_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    """打桩 job 提交，避免测试往 core.jobs 写真实任务。"""

    async def _noop_submit_job_safe(name: str, runner: Any) -> None:  # noqa: ARG001
        return None

    monkeypatch.setattr(hazards_api, "submit_job_safe", _noop_submit_job_safe)


async def _create_hazard(db_session: AsyncSession, **overrides: Any) -> HazardReport:
    payload: dict[str, Any] = {
        "hazard_no": f"HAZ-TEST-{uuid.uuid4().hex[:8]}",
        "hazard_type": "物的不安全状态",
        "hazard_level": "general",
        "description": "测试隐患",
        "discovered_at": datetime.now(UTC),
        "rectification_status": "completed",
    }
    payload.update(overrides)
    hazard = HazardReport(**payload)
    db_session.add(hazard)
    await db_session.flush()
    return hazard


class TestNotifyEndpointsResponseModel:
    async def test_notify_rectification_returns_typed_payload(
        self, auth_client: AsyncClient, db_session: AsyncSession, stub_jobs: None
    ) -> None:
        hazard = await _create_hazard(db_session, rectification_responsible_person_name="张三")

        response = await auth_client.post(
            f"/api/v1/safety/hazards/{hazard.id}/rectification/notify-rectification"
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["code"] == 200
        assert body["data"] == {"target": "张三"}

    async def test_notify_rectification_unknown_target_returns_placeholder(
        self, auth_client: AsyncClient, db_session: AsyncSession, stub_jobs: None
    ) -> None:
        hazard = await _create_hazard(db_session, rectification_responsible_person_name=None)

        response = await auth_client.post(
            f"/api/v1/safety/hazards/{hazard.id}/rectification/notify-rectification"
        )

        assert response.status_code == 200, response.text
        assert response.json()["data"] == {"target": "未知"}

    async def test_notify_reviewer_returns_typed_payload(
        self, auth_client: AsyncClient, db_session: AsyncSession, stub_jobs: None
    ) -> None:
        # 默认 verify_level_* 均为 pending → 当前复核级别为 1（部门负责人）
        hazard = await _create_hazard(db_session, rectification_status="completed")

        response = await auth_client.post(f"/api/v1/safety/hazards/{hazard.id}/rectification/notify-reviewer")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["code"] == 200
        assert body["data"] == {"level": 1, "level_label": "部门负责人"}


class TestRegulationContentResponseModel:
    async def test_get_content_returns_typed_payload(
        self, auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        regulation_id = uuid.uuid4()

        async def _fake_get_content(self: Any, _regulation_id: uuid.UUID) -> dict[str, Any]:
            return {
                "regulation_id": str(regulation_id),
                "regulation_name": "测试操规",
                "content": "# 标题",
                "status": "draft",
            }

        monkeypatch.setattr(sop_generator.SopGeneratorService, "get_content", _fake_get_content)

        response = await auth_client.get(f"/api/v1/safety/regulations/{regulation_id}/content")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["data"] == {
            "regulation_id": str(regulation_id),
            "regulation_name": "测试操规",
            "content": "# 标题",
            "status": "draft",
        }

    async def test_put_content_returns_typed_payload(
        self, auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        regulation_id = uuid.uuid4()

        async def _fake_update_content(self: Any, _regulation_id: uuid.UUID, _content: str, _status: str | None):
            return SimpleNamespace(status="reviewed")

        monkeypatch.setattr(sop_generator.SopGeneratorService, "update_content", _fake_update_content)

        response = await auth_client.put(
            f"/api/v1/safety/regulations/{regulation_id}/content",
            json={"content": "# 修改后", "status": "reviewed"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["message"] == "内容保存成功"
        assert body["data"] == {"regulation_id": str(regulation_id), "status": "reviewed"}
