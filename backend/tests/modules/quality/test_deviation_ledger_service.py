"""偏差台账 service 层单元测试（不依赖真实数据库）。"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.deviation_department_models import DepartmentContact
from app.modules.quality.qms.deviation_flow import HandlerDirectory, HandlerRef
from app.modules.quality.qms.deviation_ledger_constants import LedgerStatus
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger
from app.modules.quality.qms.deviation_ledger_schemas import LedgerCreateRequest
from app.modules.quality.qms.deviation_ledger_service import DeviationLedgerService


class _EmptyScalars:
    """空查询结果：部门联系人表视为无配置。"""

    def scalars(self) -> _EmptyScalars:
        return self

    def all(self) -> list[Any]:
        return []


class _FakeDB:
    """最小 AsyncSession 替身：只记录 commit / rollback，查询返回空集。"""

    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        self.rolled_back += 1

    async def refresh(self, obj: Any) -> None:
        return None

    async def execute(self, *args: Any, **kwargs: Any) -> _EmptyScalars:
        return _EmptyScalars()

    async def scalar(self, *args: Any, **kwargs: Any) -> uuid.UUID:
        """发现人存在性校验返回一个存在的用户 id。"""
        return uuid.uuid4()


class _FakeRepo:
    """最小仓储替身：可配置编号与是否触发唯一冲突。"""

    def __init__(self, *, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.codes: list[str] = []
        self.created_payloads: list[dict[str, Any]] = []

    async def next_daily_code(self, today: date) -> str:
        code = f"PC{today:%Y%m%d}{len(self.codes) + 1:03d}"
        self.codes.append(code)
        return code

    async def create(self, **fields: Any) -> DeviationLedger:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise IntegrityError("insert", {}, Exception("duplicate key"))
        self.created_payloads.append(fields)
        now = datetime.now(UTC)
        return DeviationLedger(
            id=uuid.uuid4(),
            created_at=now,
            updated_at=now,
            is_deleted=False,
            **fields,
        )


class _StubService(DeviationLedgerService):
    """绕过数据库：人名与负责人配置由测试直接注入。"""

    names: dict[str, str] = {}


def _directory(*refs: HandlerRef) -> HandlerDirectory:
    return HandlerDirectory({ref.id: ref for ref in refs})


def _contact(department: str, **overrides: Any) -> DepartmentContact:
    return DepartmentContact(department=department, **overrides)


def _build_service(repo: _FakeRepo, db: _FakeDB | None = None) -> tuple[_StubService, _FakeDB]:
    database = db or _FakeDB()
    service = _StubService(database)  # type: ignore[arg-type]
    service.repo = repo  # type: ignore[assignment]
    return service, database


def _row(**overrides: Any) -> DeviationLedger:
    now = datetime.now(UTC)
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "code": "PC20261110001",
        "title": "偏差标题",
        "department": "101车间",
        "discovery_date": date(2026, 11, 10),
        "discovery_location": "洁净区",
        "discoverer_id": uuid.uuid4(),
        "affected_items": "某产品",
        "batch_number": "B001",
        "description": "描述",
        "status": LedgerStatus.PENDING_INVESTIGATION.value,
        "status_updated_at": now,
        "reporter_id": uuid.uuid4(),
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
    }
    base.update(overrides)
    return DeviationLedger(**base)


def _payload() -> LedgerCreateRequest:
    return LedgerCreateRequest(
        title="偏差标题",
        department="101车间",
        discovery_date=date(2026, 11, 10),
        discovery_time="9:5",
        discovery_location="洁净区",
        affected_items="某产品",
        batch_number="B001",
        handler_ids=[uuid.uuid4(), uuid.uuid4()],
        description="描述",
    )


# ── 超期判定 ──────────────────────────────────────────────────────────


def test_overdue_false_when_within_threshold() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    now = datetime.now(UTC)
    row = _row(status=LedgerStatus.PENDING_INVESTIGATION.value, status_updated_at=now - timedelta(days=3))
    assert service._overdue(row, now) == (False, 0)


def test_overdue_true_and_days_when_exceeded() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    now = datetime.now(UTC)
    row = _row(status=LedgerStatus.PENDING_INVESTIGATION.value, status_updated_at=now - timedelta(days=10))
    is_overdue, overdue_days = service._overdue(row, now)
    assert is_overdue is True
    assert overdue_days == 3


def test_overdue_ignored_for_closed_status() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    now = datetime.now(UTC)
    row = _row(status=LedgerStatus.CLOSED.value, status_updated_at=now - timedelta(days=100))
    assert service._overdue(row, now) == (False, 0)


# ── 处理人推导 ────────────────────────────────────────────────────────


def test_handler_prefers_investigator_names() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    handler_id = uuid.uuid4()
    row = _row(status=LedgerStatus.PENDING_INVESTIGATION.value, handler_ids=[handler_id])
    directory = _directory(HandlerRef(id=handler_id, name="张三"))
    assert service._resolve_handler(row, {}, directory) == "张三"


def test_handler_falls_back_to_role_label() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    row = _row(status=LedgerStatus.PENDING_QA_REVIEW.value, handler_ids=None)
    assert service._resolve_handler(row, {}, _directory()) == "所属QA"


def test_handler_role_label_for_ai_analysis() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    row = _row(status=LedgerStatus.PENDING_AI_ANALYSIS.value)
    assert service._resolve_handler(row, {}, _directory()) == "系统AI分析"


def test_handler_uses_leader_config_when_present() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    leader_id = uuid.uuid4()
    row = _row(status=LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value)
    contacts = {"101车间": _contact("101车间", dept_head_id=leader_id)}
    directory = _directory(HandlerRef(id=leader_id, name="李四"))
    assert service._resolve_handler(row, contacts, directory) == "李四"


def test_handler_none_for_terminal_status() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    row = _row(status=LedgerStatus.CLOSED.value)
    assert service._resolve_handler(row, {}, _directory()) is None


# ── 视图组装 ──────────────────────────────────────────────────────────


def test_to_item_prefers_final_code_and_maps_labels() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    row = _row(final_code="PC20261110-F", deviation_level="major")
    item = service._to_item(row, {}, {}, {}, _directory(), datetime.now(UTC))
    assert item.display_code == "PC20261110-F"
    assert item.level_label == "严重"
    assert item.status_label == "待调查"


def test_to_item_shows_returned_step_label() -> None:
    service = _StubService(_FakeDB())  # type: ignore[arg-type]
    row = _row(status=LedgerStatus.RETURNED.value, returned_step=LedgerStatus.PENDING_INVESTIGATION.value)
    item = service._to_item(row, {}, {}, {}, _directory(), datetime.now(UTC))
    assert item.returned_step_label == "待调查"


# ── 新建 ──────────────────────────────────────────────────────────────


async def test_create_sets_code_and_current_user() -> None:
    repo = _FakeRepo()
    service, db = _build_service(repo)
    user_id = uuid.uuid4()
    detail = await service.create(_payload(), user_id=user_id)

    assert detail.code.startswith("PC")
    assert detail.status == LedgerStatus.PENDING_AI_ANALYSIS.value
    assert db.committed == 1
    assert repo.created_payloads[0]["discoverer_id"] == user_id
    assert repo.created_payloads[0]["reporter_id"] == user_id


async def test_create_accepts_explicit_discoverer() -> None:
    """发现人可指定实际发现人，上报人仍是当前登录人。"""
    repo = _FakeRepo()
    service, _ = _build_service(repo)
    user_id = uuid.uuid4()
    discoverer = uuid.uuid4()
    payload = _payload().model_copy(update={"discoverer_id": discoverer})

    await service.create(payload, user_id=user_id)

    assert repo.created_payloads[0]["discoverer_id"] == discoverer
    assert repo.created_payloads[0]["reporter_id"] == user_id


async def test_create_retries_on_code_conflict() -> None:
    repo = _FakeRepo(fail_times=1)
    service, db = _build_service(repo)
    detail = await service.create(_payload(), user_id=uuid.uuid4())

    assert detail.code.endswith("002")
    assert db.rolled_back == 1
    assert db.committed == 1


async def test_create_raises_after_exhausting_retries() -> None:
    repo = _FakeRepo(fail_times=99)
    service, db = _build_service(repo)
    with pytest.raises(Exception):
        await service.create(_payload(), user_id=uuid.uuid4())
    assert db.rolled_back == 3
    assert db.committed == 0


class _Rows:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _UserRowsDB:
    """只回应 HandlerDirectory.load_for_ids 的用户查询。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    async def execute(self, *args: Any, **kwargs: Any) -> _Rows:
        return _Rows(self._rows)


async def test_handler_directory_resolves_uuid_tokens_from_contacts() -> None:
    """配置页把 qa_staff_ids 存成用户 UUID：directory 必须能按主键解析，否则 QA 环节永远无处理人。"""
    qa_id = uuid.uuid4()
    contact = _contact("101车间", qa_staff_ids=[str(qa_id)])
    db = _UserRowsDB(
        [
            SimpleNamespace(
                id=qa_id,
                name="张三",
                feishu_open_id=None,
                feishu_user_id=None,
                avatar_thumb=None,
                avatar_url="https://cdn/x.png",
            )
        ]
    )

    directory = await HandlerDirectory.load_for_ids(cast(AsyncSession, db), {"101车间": contact})

    assert directory.resolve([str(qa_id)]) == [qa_id]
    assert directory.name(qa_id) == "张三"
    ref = directory.ref(qa_id)
    assert ref is not None
    assert ref.avatar_url == "https://cdn/x.png"


async def test_handler_directory_resolves_feishu_tokens_from_contacts() -> None:
    """历史数据里 qa_staff_ids 存飞书 open_id：按 feishu_open_id 解析，并带出可用发送标识。"""
    user_id = uuid.uuid4()
    contact = _contact("101车间", qa_staff_ids=["ou_abc"])
    db = _UserRowsDB(
        [
            SimpleNamespace(
                id=user_id,
                name="李四",
                feishu_open_id="ou_abc",
                feishu_user_id=None,
                avatar_thumb=None,
                avatar_url=None,
            )
        ]
    )

    directory = await HandlerDirectory.load_for_ids(cast(AsyncSession, db), {"101车间": contact})

    assert directory.resolve(["ou_abc"]) == [user_id]
    ref = directory.ref(user_id)
    assert ref is not None
    assert ref.feishu_id == "ou_abc"
    assert ref.feishu_id_type == "open_id"


async def test_handler_directory_falls_back_to_legacy_feishu_user_id() -> None:
    """历史把 open_id 存进了 feishu_user_id：仍要能解析并发送。"""
    user_id = uuid.uuid4()
    contact = _contact("101车间", qa_staff_ids=["ou_legacy"])
    db = _UserRowsDB(
        [
            SimpleNamespace(
                id=user_id,
                name="王五",
                feishu_open_id=None,
                feishu_user_id="ou_legacy",
                avatar_thumb=None,
                avatar_url=None,
            )
        ]
    )

    directory = await HandlerDirectory.load_for_ids(cast(AsyncSession, db), {"101车间": contact})

    assert directory.resolve(["ou_legacy"]) == [user_id]
    ref = directory.ref(user_id)
    assert ref is not None
    assert ref.feishu_id == "ou_legacy"
    assert ref.feishu_id_type == "user_id"
