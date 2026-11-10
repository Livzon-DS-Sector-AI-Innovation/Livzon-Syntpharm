"""P2 提示词模板化 / 示例库 / 解析留痕的单元测试。

不连数据库、不调 LLM：
- 提示词：变量渲染、覆盖兜底、JSON 花括号不被当占位符、指纹跟随生效文本；
- 示例库：注入条数上限、排除已填槽位、空值停用、人工修正覆盖；
- 留痕统计：漏选 = 当前启用但 AI 没选，多选 = AI 选了但现在停用。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.modules.research.report_gen import prompts as prompts_module
from app.modules.research.report_gen import service as service_module
from app.modules.research.report_gen.api import router as report_gen_router
from app.modules.research.report_gen.examples import load_examples, record_manual_example
from app.modules.research.report_gen.prompts_version import (
    agent_prompt_version,
    structure_prompt_version,
)
from app.modules.research.report_gen.schemas import (
    ReportGenStructureDiff,
    ReportGenStructureRunData,
    ReportGenStructureRunListData,
)
from app.modules.research.report_gen.structure_runs import summarize_edit
from app.platform.identity.deps import require_current_user
from app.platform.permission.deps import require_current_user as permission_require_current_user
from app.platform.permission.service.authorization import PermissionContext

NOW = datetime.now(UTC)


# ---------------------------------------------------------------- 提示词


def test_render_prompt_fills_variables_and_keeps_json_braces() -> None:
    template = '品种 $drug_name，共 $slot_total 个槽位；返回 {"slots": []}'
    rendered = prompts_module.render_prompt(template, {"drug_name": "达格列净", "slot_total": 3})

    assert "达格列净" in rendered
    assert "共 3 个槽位" in rendered
    # JSON 花括号不能被当成占位符吃掉
    assert '{"slots": []}' in rendered


def test_render_prompt_keeps_unknown_variable() -> None:
    assert prompts_module.render_prompt("$unknown 保留", {"other": "x"}) == "$unknown 保留"
    # 没有变量时原样返回，连 $ 都不处理
    assert prompts_module.render_prompt("$drug_name") == "$drug_name"


def test_resolve_prompt_falls_back_to_builtin() -> None:
    assert prompts_module.resolve_prompt("", "内置") == "内置"
    assert prompts_module.resolve_prompt("   ", "内置") == "内置"
    assert prompts_module.resolve_prompt(None, "内置") == "内置"
    assert prompts_module.resolve_prompt(" 库里的 ", "内置") == "库里的"


def test_prompt_version_follows_effective_text() -> None:
    default_agent = agent_prompt_version()
    assert default_agent == agent_prompt_version()
    assert len(default_agent) == len("prm-") + 8
    assert structure_prompt_version() == structure_prompt_version()

    # 库里覆盖过的文本进指纹：改一个字就变
    assert agent_prompt_version(prompts_module.AGENT_SYSTEM_PROMPT + "改") != default_agent
    assert structure_prompt_version(prompts_module.STRUCTURE_SYSTEM_PROMPT + "改") != structure_prompt_version()


# ---------------------------------------------------------------- 示例库


class _Result:
    def __init__(self, rows: list[Any], first: Any = None) -> None:
        self._rows = rows
        self._first = first

    def scalars(self) -> Any:
        return SimpleNamespace(all=lambda: self._rows, first=lambda: self._first)


class _ReadSession:
    """够 load_examples 用：execute().scalars().all() + flush()。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows
        self.flushed = 0

    async def execute(self, statement: Any) -> _Result:
        return _Result(self._rows)

    async def flush(self) -> None:
        self.flushed += 1


class _UpsertSession:
    """够 record_manual_example 用：execute().scalars().first() + add() + flush()。"""

    def __init__(self, existing: Any = None) -> None:
        self.existing = existing
        self.added: list[Any] = []
        self.flushed = 0

    async def execute(self, statement: Any) -> _Result:
        return _Result([], first=self.existing)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed += 1


def _example_row(slot_key: str, value: str = "达格列净", evidence: str | None = "CAS 461-58-5") -> Any:
    return SimpleNamespace(
        slot_key=slot_key,
        slot_label="品种名称",
        value=value,
        evidence_text=evidence,
        usage_count=0,
    )


async def test_load_examples_respects_limit_and_exclusions() -> None:
    session = _ReadSession([_example_row("drug_name"), _example_row("cas_no", "461-58-5")])

    examples = await load_examples(session, uuid4(), limit=2, exclude_keys={"cas_no"})  # type: ignore[arg-type]

    assert set(examples) == {"drug_name"}
    assert examples["drug_name"]["value"] == "达格列净"
    # 只给真正下发的示例计数
    assert session._rows[0].usage_count == 1
    assert session._rows[1].usage_count == 0


async def test_load_examples_disabled_when_limit_zero() -> None:
    session = _ReadSession([_example_row("drug_name")])

    assert await load_examples(session, uuid4(), limit=0) == {}  # type: ignore[arg-type]
    assert await load_examples(session, None, limit=5) == {}  # type: ignore[arg-type]


async def test_record_manual_example_inserts_and_deactivates() -> None:
    empty_session = _UpsertSession()
    assert (
        await record_manual_example(
            empty_session, template_id=uuid4(), slot_key="drug_name", slot_label="品种", value="  "
        )
        is False
    )
    assert empty_session.added == []

    insert_session = _UpsertSession()
    assert await record_manual_example(
        insert_session, template_id=uuid4(), slot_key="drug_name", slot_label="品种", value=" 达格列净 "
    )
    assert len(insert_session.added) == 1
    created = insert_session.added[0]
    assert created.source == "manual_edit"
    assert created.value == "达格列净"
    assert created.is_active is True

    existing = _example_row("drug_name")
    existing.is_active = True
    deactivate_session = _UpsertSession(existing=existing)
    assert await record_manual_example(
        deactivate_session, template_id=uuid4(), slot_key="drug_name", slot_label="品种", value=""
    )
    # 人工清空 = 判定该槽位不该有内容：停用而不是删除
    assert existing.is_active is False


async def test_record_manual_example_skips_unchanged() -> None:
    existing = _example_row("drug_name", value="达格列净")
    existing.is_active = True
    session = _UpsertSession(existing=existing)

    assert not await record_manual_example(
        session, template_id=uuid4(), slot_key="drug_name", slot_label="品种", value="达格列净"
    )
    assert session.flushed == 0


# ---------------------------------------------------------------- 留痕统计


def test_summarize_edit_counts_missing_and_extra() -> None:
    slots = [
        {"slot_key": "a", "is_enabled": True},
        {"slot_key": "b", "is_enabled": False},
        {"slot_key": "d", "is_enabled": True},
    ]

    diff = summarize_edit(["a", "b", "c"], slots)

    assert diff["ai_slot_count"] == 3
    assert diff["current_slot_count"] == 3
    assert diff["kept_count"] == 1
    assert diff["missing_count"] == 1 and diff["missing_keys"] == ["d"]
    assert diff["extra_count"] == 2 and diff["extra_keys"] == ["b", "c"]


def test_summarize_edit_handles_empty_history() -> None:
    diff = summarize_edit(None, [{"slot_key": "a", "is_enabled": True}])

    assert diff["ai_slot_count"] == 0
    assert diff["missing_count"] == 1
    assert diff["extra_count"] == 0


# ---------------------------------------------------------------- 接口契约


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


async def test_structure_runs_endpoint_returns_diff(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    template_id = uuid4()

    async def _runs(db, template_id_arg, limit=10):  # noqa: ANN001, ANN202
        assert template_id_arg == template_id
        return ReportGenStructureRunListData(
            total=1,
            items=[
                ReportGenStructureRunData(
                    id=str(uuid4()),
                    source_key="tpl/v1.docx",
                    prompt_version="prm-e2469dce",
                    model_name="Qwen3.7-Plus",
                    candidate_count=120,
                    slot_count=18,
                    duration_ms=4200,
                    status="ok",
                    created_at=NOW,
                    diff=ReportGenStructureDiff(
                        ai_slot_count=18,
                        current_slot_count=20,
                        kept_count=16,
                        missing_count=2,
                        extra_count=2,
                        missing_keys=["batch_no", "report_date"],
                        extra_keys=["remark", "sign"],
                    ),
                )
            ],
        )

    monkeypatch.setattr(service_module, "list_structure_runs", _runs)

    response = await client.get(f"/api/v1/research/report-gen/templates/{template_id}/structure-runs?limit=5")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["diff"]["missing_count"] == 2
    assert body["items"][0]["prompt_version"] == "prm-e2469dce"
