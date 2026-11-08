"""报告生成 Agent 运行指标与提示词指纹的单元测试。

不连数据库、不调 LLM：
- 指标聚合用假 session 返回一行聚合结果，验证口径换算与空窗口处理；
- 提示词指纹验证「同输入同指纹 / 改一个字就变」；
- 接口层验证 days 透传与响应信封。
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.modules.research.report_gen import prompts as prompts_module
from app.modules.research.report_gen import service as service_module
from app.modules.research.report_gen.api import router as report_gen_router
from app.modules.research.report_gen.prompts_version import (
    agent_prompt_version,
    structure_prompt_version,
)
from app.modules.research.report_gen.schemas import ReportGenMetricsData
from app.platform.identity.deps import require_current_user
from app.platform.permission.deps import require_current_user as permission_require_current_user
from app.platform.permission.service.authorization import PermissionContext

NOW = datetime.now(UTC)


class _FakeResult:
    def __init__(self, row: object, *, many: bool = False) -> None:
        self._row = row
        self._many = many

    def one(self) -> object:
        return self._row

    def all(self) -> list[object]:
        return list(self._row) if self._many else []  # type: ignore[call-overload]


_EMPTY_FEEDBACK = SimpleNamespace(total=0, open=0, applied=0, ignored=0)


class _FakeSession:
    """按调用顺序喂三种聚合结果：任务行 → 意见计数行 → 意见槽位榜。

    agent_metrics 现在要跑三次查询，顺序固定：任务聚合、意见按状态计数、
    意见按槽位分组。第二次/第三次不给就用「窗口内没有意见」兜底。
    """

    def __init__(self, row: object, feedback: object | None = None, slots: list[object] | None = None) -> None:
        self._rows: list[object] = [row, feedback or _EMPTY_FEEDBACK, slots or []]

    async def execute(self, statement: object) -> _FakeResult:  # noqa: ANN401 - 只透传
        row = self._rows.pop(0)
        return _FakeResult(row, many=isinstance(row, list))


def _row(**overrides: object) -> SimpleNamespace:
    payload: dict[str, object] = {
        "total": 5,
        "completed": 3,
        "failed": 1,
        "cancelled": 1,
        "avg_rounds": Decimal("6.50"),
        "avg_duration_seconds": Decimal("123.44"),
        "slot_total": 20,
        "slot_gap": 5,
        "fallback_completed": 1,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


@pytest.fixture(autouse=True)
def _stub_runtime_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """指标要算「当前生效提示词」的指纹，会把 load_config() 拉进来；这里给个固定配置。"""

    async def _load_config() -> SimpleNamespace:
        return SimpleNamespace(
            agent_prompt=prompts_module.AGENT_SYSTEM_PROMPT,
            structure_prompt=prompts_module.STRUCTURE_SYSTEM_PROMPT,
        )

    monkeypatch.setattr(service_module, "load_config", _load_config)


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(report_gen_router, prefix="/api/v1/research/report-gen")

    user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[require_current_user] = lambda: user
    app.dependency_overrides[permission_require_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()

    async def _fake_context(db, current_user, code):  # noqa: ANN001, ANN202
        return PermissionContext(user=current_user, permission_code=code)

    monkeypatch.setattr("app.platform.permission.deps.build_permission_context", _fake_context)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def test_metrics_compute_rates_from_completed_only() -> None:
    metrics = await service_module.agent_metrics(_FakeSession(_row()), days=30)  # type: ignore[arg-type]

    assert metrics.window_days == 30
    assert metrics.total == 5
    assert metrics.success_rate == 0.6
    assert metrics.avg_rounds == 6.5
    # 秒级均值保留 1 位，Decimal 必须转成 float 才能进 JSON
    assert metrics.avg_duration_seconds == 123.4
    assert metrics.gap_rate == 0.25
    assert metrics.fallback_rate == 0.3333
    assert metrics.agent_prompt_version.startswith("prm-")
    assert metrics.structure_prompt_version.startswith("prm-")


async def test_metrics_return_none_when_window_is_empty() -> None:
    empty = _row(
        total=0,
        completed=0,
        failed=0,
        cancelled=0,
        avg_rounds=None,
        avg_duration_seconds=None,
        slot_total=0,
        slot_gap=0,
        fallback_completed=0,
    )

    metrics = await service_module.agent_metrics(_FakeSession(empty), days=7)  # type: ignore[arg-type]

    assert (metrics.total, metrics.completed) == (0, 0)
    assert metrics.success_rate is None
    assert metrics.avg_rounds is None
    assert metrics.avg_duration_seconds is None
    assert metrics.gap_rate is None
    assert metrics.fallback_rate is None


async def test_metrics_include_feedback_adoption() -> None:
    feedback = SimpleNamespace(total=7, open=2, applied=3, ignored=2)
    slots = [
        SimpleNamespace(slot_key="study_conclusion", slot_count=4),
        SimpleNamespace(slot_key="results", slot_count=1),
    ]

    metrics = await service_module.agent_metrics(_FakeSession(_row(), feedback, slots), days=30)  # type: ignore[arg-type]

    assert (metrics.feedback_total, metrics.feedback_open) == (7, 2)
    assert (metrics.feedback_applied, metrics.feedback_ignored) == (3, 2)
    # 分母只算「有人处置过」的（applied + ignored）：还挂着的 open 既不算采纳也不算否决
    assert metrics.feedback_adoption_rate == 0.6
    assert [(item.slot_key, item.count) for item in metrics.feedback_slot_top] == [
        ("study_conclusion", 4),
        ("results", 1),
    ]


async def test_metrics_feedback_rate_none_when_nothing_disposed() -> None:
    feedback = SimpleNamespace(total=5, open=5, applied=0, ignored=0)

    metrics = await service_module.agent_metrics(_FakeSession(_row(), feedback), days=30)  # type: ignore[arg-type]

    assert metrics.feedback_open == 5
    # 全都没处置过时采纳率无意义，返回 None 让前端显示「—」
    assert metrics.feedback_adoption_rate is None
    assert metrics.feedback_slot_top == []


@pytest.mark.parametrize(("days", "expected"), [(500, 90), (0, 1), (30, 30)])
async def test_metrics_clamp_window(days: int, expected: int) -> None:
    metrics = await service_module.agent_metrics(_FakeSession(_row()), days=days)  # type: ignore[arg-type]

    assert metrics.window_days == expected


def test_ratio_guards_zero_denominator() -> None:
    assert service_module._ratio(1, 0) is None
    assert service_module._ratio(0, 4) == 0.0
    assert service_module._ratio(1, 3) == 0.3333


def test_prompt_version_is_stable_and_sensitive() -> None:
    first = agent_prompt_version()
    assert first == agent_prompt_version()
    assert first.startswith("prm-") and len(first) == len("prm-") + 8
    assert structure_prompt_version() == structure_prompt_version()

    # P2 之后指纹按「实际生效文本」算：库里覆盖过的段落一改就换指纹
    assert agent_prompt_version(prompts_module.AGENT_SYSTEM_PROMPT + "改动") != first
    assert agent_prompt_version() == first


async def test_metrics_endpoint_passes_days(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    async def _metrics(db, days: int):  # noqa: ANN001, ANN202
        seen["days"] = days
        return ReportGenMetricsData(
            window_days=days,
            total=4,
            completed=3,
            success_rate=0.75,
            agent_prompt_version="prm-1234abcd",
            structure_prompt_version="prm-5678efgh",
            generated_at=NOW,
        )

    monkeypatch.setattr(service_module, "agent_metrics", _metrics)

    response = await client.get("/api/v1/research/report-gen/settings/metrics?days=7")

    assert response.status_code == 200
    body = response.json()
    assert seen["days"] == 7
    assert body["data"]["window_days"] == 7
    assert body["data"]["success_rate"] == 0.75
    assert body["data"]["agent_prompt_version"] == "prm-1234abcd"
    # 空比率必须原样是 null，前端据此显示「—」而不是 0%
    assert body["data"]["gap_rate"] is None
