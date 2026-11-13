"""偏差流程处理人解析与部门联系人 QA 字段拆分（不依赖真实数据库）。

覆盖两处修复：

- 「质量负责人审核」取偏差所属部门配置的质量负责人，缺省回退质量保证部；
- 「所属QA审核」「QA负责人审核」分别对应 ``qa_reviewer_id`` / ``qa_head_id``，
  历史 ``qa_staff_ids`` 位置约定只作兜底。
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.deviation_config_schemas import (
    DepartmentContactCreateRequest,
    DepartmentContactUpdateRequest,
)
from app.modules.quality.qms.deviation_config_service import DeviationConfigService
from app.modules.quality.qms.deviation_department_models import DepartmentContact
from app.modules.quality.qms.deviation_flow import (
    QA_DEPARTMENT,
    HandlerDirectory,
    HandlerRef,
    resolve_step_handlers,
)
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger


def _ref(name: str) -> HandlerRef:
    return HandlerRef(id=uuid.uuid4(), name=name)


def _directory(*refs: HandlerRef) -> HandlerDirectory:
    return HandlerDirectory({ref.id: ref for ref in refs})


def _ledger(department: str) -> DeviationLedger:
    return DeviationLedger(
        id=uuid.uuid4(),
        code="PC20261111001",
        department=department,
        status="pending_qa_review",
        handler_ids=[],
        cross_dept_reviewers=[],
    )


def _contact(department: str, **overrides: Any) -> DepartmentContact:
    row = DepartmentContact(department=department, **overrides)
    row.id = row.id or uuid.uuid4()
    return row


# ── 质量负责人审核 ──────────────────────────────────────────────────────


def test_quality_head_review_prefers_own_department() -> None:
    """所属部门配了自己的质量负责人：节点必须指派给该人，而不是质量保证部。"""
    own_head = _ref("刘俊广")
    qa_head = _ref("赵建汉")
    contacts = {
        "AI创新部": _contact("AI创新部", quality_head_id=own_head.id),
        QA_DEPARTMENT: _contact(QA_DEPARTMENT, quality_head_id=qa_head.id),
    }

    handlers = resolve_step_handlers(_ledger("AI创新部"), contacts, _directory(own_head, qa_head))

    assert handlers["quality_head_review"] == [own_head.id]


def test_quality_head_review_falls_back_to_qa_department() -> None:
    """所属部门没配质量负责人：回退到质量保证部的配置。"""
    qa_head = _ref("赵建汉")
    contacts = {
        "302车间": _contact("302车间"),
        QA_DEPARTMENT: _contact(QA_DEPARTMENT, quality_head_id=qa_head.id),
    }

    handlers = resolve_step_handlers(_ledger("302车间"), contacts, _directory(qa_head))

    assert handlers["quality_head_review"] == [qa_head.id]


def test_quality_head_review_falls_back_to_qa_dept_head() -> None:
    """两处都没配质量负责人：回退质量保证部部门负责人，避免环节无人可办。"""
    qa_dept_head = _ref("何姗")
    contacts = {QA_DEPARTMENT: _contact(QA_DEPARTMENT, dept_head_id=qa_dept_head.id)}

    handlers = resolve_step_handlers(_ledger("302车间"), contacts, _directory(qa_dept_head))

    assert handlers["quality_head_review"] == [qa_dept_head.id]


# ── 所属 QA / QA 负责人 ──────────────────────────────────────────────────


def test_qa_review_prefers_reviewer_column_over_legacy_array() -> None:
    """两个独立字段是权威来源，历史数组不再影响节点指派。"""
    reviewer = _ref("何姗")
    legacy = _ref("刘俊广")
    contacts = {
        "AI创新部": _contact(
            "AI创新部",
            qa_reviewer_id=reviewer.id,
            qa_staff_ids=[str(legacy.id)],
        )
    }

    handlers = resolve_step_handlers(_ledger("AI创新部"), contacts, _directory(reviewer, legacy))

    assert handlers["qa_review"] == [reviewer.id]
    assert handlers["final_code_input"] == [reviewer.id]


def test_qa_review_falls_back_to_legacy_array() -> None:
    """导入脚本只写 qa_staff_ids 时，所属 QA 仍要解析得出来。"""
    reviewer = _ref("何姗")
    contacts = {"101车间": _contact("101车间", qa_staff_ids=[str(reviewer.id)])}

    handlers = resolve_step_handlers(_ledger("101车间"), contacts, _directory(reviewer))

    assert handlers["qa_review"] == [reviewer.id]


def test_qa_head_review_prefers_own_department() -> None:
    """QA 负责人审核优先取偏差所属部门配置的 QA 负责人。"""
    own_head = _ref("刘俊广")
    qa_dept_head = _ref("刘清清")
    contacts = {
        "AI创新部": _contact("AI创新部", qa_head_id=own_head.id),
        QA_DEPARTMENT: _contact(QA_DEPARTMENT, qa_head_id=qa_dept_head.id),
    }

    handlers = resolve_step_handlers(_ledger("AI创新部"), contacts, _directory(own_head, qa_dept_head))

    assert handlers["qa_head_review"] == [own_head.id]


def test_qa_head_review_falls_back_to_qa_department() -> None:
    """本部门没配 QA 负责人时回退质量保证部（保持历史行为）。"""
    qa_head = _ref("刘清清")
    contacts = {QA_DEPARTMENT: _contact(QA_DEPARTMENT, qa_head_id=qa_head.id)}

    handlers = resolve_step_handlers(_ledger("101车间"), contacts, _directory(qa_head))

    assert handlers["qa_head_review"] == [qa_head.id]


def test_qa_head_review_own_legacy_array_before_qa_department() -> None:
    """本部门只有历史数组时按 [1] 兜底，仍优先于质量保证部。"""
    own_head = _ref("刘俊广")
    qa_dept_head = _ref("刘清清")
    contacts = {
        "AI创新部": _contact("AI创新部", qa_staff_ids=["someone-else", str(own_head.id)]),
        QA_DEPARTMENT: _contact(QA_DEPARTMENT, qa_head_id=qa_dept_head.id),
    }

    handlers = resolve_step_handlers(_ledger("AI创新部"), contacts, _directory(own_head, qa_dept_head))

    assert handlers["qa_head_review"] == [own_head.id]


def test_qa_head_review_falls_back_to_legacy_array_then_dept_head() -> None:
    """旧数组 [1] 优先于部门负责人；数组只有一个人时回退部门负责人。"""
    legacy_head = _ref("刘清清")
    qa_dept_head = _ref("何姗")
    contacts = {
        QA_DEPARTMENT: _contact(QA_DEPARTMENT, qa_staff_ids=["someone-else", str(legacy_head.id)]),
    }
    handlers = resolve_step_handlers(_ledger("101车间"), contacts, _directory(legacy_head, qa_dept_head))
    assert handlers["qa_head_review"] == [legacy_head.id]

    only_reviewer = {
        QA_DEPARTMENT: _contact(
            QA_DEPARTMENT,
            qa_staff_ids=["someone-else"],
            dept_head_id=qa_dept_head.id,
        ),
    }
    fallback = resolve_step_handlers(_ledger("101车间"), only_reviewer, _directory(legacy_head, qa_dept_head))
    assert fallback["qa_head_review"] == [qa_dept_head.id]


# ── 配置写入：新字段回写兼容数组 ────────────────────────────────────────


def test_create_payload_writes_qa_staff_snapshot() -> None:
    """新增配置时按新字段生成 [所属QA, QA负责人] 快照，历史读取方不失真。"""
    reviewer = uuid.uuid4()
    head = uuid.uuid4()
    row = DepartmentContact(department="101车间")
    payload = DepartmentContactCreateRequest(
        department="101车间",
        qa_reviewer_id=reviewer,
        qa_head_id=head,
        qa_staff_ids=["stale-token"],
    )

    DeviationConfigService._apply_payload(row, payload)

    assert row.qa_reviewer_id == reviewer
    assert row.qa_head_id == head
    assert row.qa_staff_ids == [str(reviewer), str(head)]


def test_create_payload_keeps_legacy_array_when_new_columns_empty() -> None:
    """新字段都为空时保留调用方传入的数组，兼容未升级的导入脚本。"""
    row = DepartmentContact(department="101车间")
    payload = DepartmentContactCreateRequest(department="101车间", qa_staff_ids=["ou_abc"])

    DeviationConfigService._apply_payload(row, payload)

    assert row.qa_reviewer_id is None
    assert row.qa_head_id is None
    assert row.qa_staff_ids == ["ou_abc"]


class _FakeResult:
    """只支持 scalar_one_or_none 与 all 两种取法。"""

    def __init__(self, row: Any = None, users: list[Any] | None = None) -> None:
        self._row = row
        self._users = users or []

    def scalar_one_or_none(self) -> Any:
        return self._row

    def all(self) -> list[Any]:
        return self._users


class _FakeDB:
    """update_contact 需要的最小 AsyncSession 替身。"""

    def __init__(self, row: DepartmentContact, existing_users: set[uuid.UUID] | None = None) -> None:
        self.row = row
        self.commits = 0
        self.existing_users = existing_users or set()

    async def execute(self, *args: Any, **kwargs: Any) -> _FakeResult:
        users = [
            SimpleNamespace(
                id=user_id,
                name="测试人员",
                feishu_open_id=None,
                feishu_user_id=None,
                avatar_thumb=None,
                avatar_url=None,
            )
            for user_id in self.existing_users
        ]
        return _FakeResult(self.row, users)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: Any) -> None:
        return None


async def test_update_contact_rewrites_snapshot_only_when_qa_fields_touched() -> None:
    """改了 QA 字段就重建快照；只改别的字段不要动历史数组。"""
    reviewer = uuid.uuid4()
    head = uuid.uuid4()
    quality_head = uuid.uuid4()
    row = _contact("101车间", qa_staff_ids=["legacy"])
    db = _FakeDB(row, existing_users={reviewer, head, quality_head})
    service = DeviationConfigService(cast(AsyncSession, db))

    await service.update_contact(
        row.id,
        DepartmentContactUpdateRequest(qa_reviewer_id=reviewer, qa_head_id=head),
    )
    assert row.qa_staff_ids == [str(reviewer), str(head)]

    await service.update_contact(row.id, DepartmentContactUpdateRequest(quality_head_id=quality_head))
    assert row.qa_staff_ids == [str(reviewer), str(head)]
    assert db.commits == 2
