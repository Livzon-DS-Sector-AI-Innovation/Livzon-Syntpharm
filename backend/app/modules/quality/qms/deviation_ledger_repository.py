"""偏差台账数据访问层。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, cast

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from .deviation_ledger_constants import STEP_OVERDUE_DAYS, LedgerStatus
from .deviation_ledger_models import DeviationAttachmentComment, DeviationLedger

#: 当日取号的会话级咨询锁 key，保证并发创建不会撞号
_CODE_LOCK_KEY = "quality.deviation_ledger.code"


@dataclass(slots=True)
class LedgerStatisticsRow:
    """看盘统计聚合结果。"""

    total: int
    pending: int
    returned: int
    closed: int
    overdue: int
    department_distribution: list[tuple[str, int]]
    status_distribution: list[tuple[str, int]]


class DeviationLedgerRepository:
    """偏差台账仓储。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 查询 ──────────────────────────────────────────────────────────

    def _apply_filters(
        self,
        stmt: Select[Any],
        *,
        status: str | None,
        department: str | None,
        reason_category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Select[Any]:
        stmt = stmt.where(DeviationLedger.is_deleted.is_(False))
        if status == LedgerStatus.RETURNED.value:
            #: 新语义下退回不再落 returned 态，改按「存在未处理的退回标记」筛选
            stmt = stmt.where(
                DeviationLedger.returned_step.isnot(None),
                DeviationLedger.status.notin_((LedgerStatus.CLOSED.value, LedgerStatus.CANCELLED.value)),
            )
        elif status:
            stmt = stmt.where(DeviationLedger.status == status)
        if department:
            stmt = stmt.where(DeviationLedger.department == department)
        if reason_category:
            stmt = stmt.where(DeviationLedger.reason_category == reason_category)
        if start_date:
            stmt = stmt.where(DeviationLedger.discovery_date >= start_date)
        if end_date:
            stmt = stmt.where(DeviationLedger.discovery_date <= end_date)
        return stmt

    async def list_items(
        self,
        *,
        status: str | None = None,
        department: str | None = None,
        reason_category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DeviationLedger], int]:
        """台账分页查询，按发现日期倒序（同日按创建时间倒序）。"""
        base = self._apply_filters(
            select(DeviationLedger),
            status=status,
            department=department,
            reason_category=reason_category,
            start_date=start_date,
            end_date=end_date,
        )
        total = await self.db.scalar(
            self._apply_filters(
                select(func.count()).select_from(DeviationLedger),
                status=status,
                department=department,
                reason_category=reason_category,
                start_date=start_date,
                end_date=end_date,
            )
        )
        stmt = (
            base.options(
                load_only(
                    DeviationLedger.id,
                    DeviationLedger.code,
                    DeviationLedger.final_code,
                    DeviationLedger.title,
                    DeviationLedger.department,
                    DeviationLedger.discovery_date,
                    DeviationLedger.status,
                    DeviationLedger.status_updated_at,
                    DeviationLedger.returned_step,
                    DeviationLedger.deviation_level,
                    DeviationLedger.discoverer_id,
                    DeviationLedger.reporter_id,
                    DeviationLedger.handler_ids,
                    DeviationLedger.cross_dept_reviewers,
                    DeviationLedger.created_at,
                )
            )
            .order_by(
                DeviationLedger.discovery_date.desc().nullslast(),
                DeviationLedger.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.scalars(stmt)).all()
        return list(rows), int(total or 0)

    async def get_by_id(self, ledger_id: uuid.UUID) -> DeviationLedger | None:
        stmt = select(DeviationLedger).where(
            DeviationLedger.id == ledger_id,
            DeviationLedger.is_deleted.is_(False),
        )
        return cast(DeviationLedger | None, await self.db.scalar(stmt))

    async def get_by_id_for_update(self, ledger_id: uuid.UUID) -> DeviationLedger | None:
        """流转前加行锁，避免同一环节被两人并发通过导致状态跳变。"""
        stmt = (
            select(DeviationLedger)
            .where(
                DeviationLedger.id == ledger_id,
                DeviationLedger.is_deleted.is_(False),
            )
            .with_for_update()
        )
        return cast(DeviationLedger | None, await self.db.scalar(stmt))

    # ── 统计 ──────────────────────────────────────────────────────────

    async def statistics(self) -> LedgerStatisticsRow:
        """一次往返取四卡数值，另两次分组取部门 / 状态分布。"""
        active = DeviationLedger.is_deleted.is_(False)
        card_stmt = select(
            func.count().label("total"),
            func.count().filter(DeviationLedger.status.like("pending_%")).label("pending"),
            #: 「已退回」= 存在未处理退回标记（目标环节重新通过后服务端会清空）
            func.count()
            .filter(
                DeviationLedger.returned_step.isnot(None),
                DeviationLedger.status.notin_((LedgerStatus.CLOSED.value, LedgerStatus.CANCELLED.value)),
            )
            .label("pending_returned"),
            func.count().filter(DeviationLedger.status == LedgerStatus.CLOSED.value).label("closed"),
        ).where(active)
        card = (await self.db.execute(card_stmt)).one()

        dept_stmt = (
            select(DeviationLedger.department, func.count().label("cnt"))
            .where(active)
            .group_by(DeviationLedger.department)
            .order_by(func.count().desc(), DeviationLedger.department.asc())
            .limit(20)
        )
        dept_rows = (await self.db.execute(dept_stmt)).all()

        status_stmt = (
            select(DeviationLedger.status, func.count().label("cnt"))
            .where(active)
            .group_by(DeviationLedger.status)
            .order_by(func.count().desc())
        )
        status_rows = (await self.db.execute(status_stmt)).all()

        overdue_stmt = select(DeviationLedger.status, DeviationLedger.status_updated_at).where(
            active, DeviationLedger.status.like("pending_%")
        )
        overdue_rows = (await self.db.execute(overdue_stmt)).all()
        now = datetime.now(UTC)
        overdue = 0
        for status_value, updated_at in overdue_rows:
            threshold = STEP_OVERDUE_DAYS.get(str(status_value))
            if threshold is None or updated_at is None:
                continue
            moment = updated_at if updated_at.tzinfo is not None else updated_at.replace(tzinfo=UTC)
            if (now - moment).total_seconds() // 86400 > threshold:
                overdue += 1

        return LedgerStatisticsRow(
            total=int(card.total or 0),
            pending=int(card.pending or 0),
            returned=int(card.pending_returned or 0),
            closed=int(card.closed or 0),
            overdue=overdue,
            department_distribution=[(str(row.department), int(row.cnt)) for row in dept_rows],
            status_distribution=[(str(row.status), int(row.cnt)) for row in status_rows],
        )

    # ── 写入 ──────────────────────────────────────────────────────────

    async def next_daily_code(self, today: date) -> str:
        """生成当日下一个系统编号：PC + YYYYMMDD + 3 位序号。

        用事务级咨询锁串行化当日取号；跨进程并发由 ``uq_deviation_ledger_code``
        唯一索引兜底（service 层捕获并重试）。
        """
        await self.db.execute(select(func.pg_advisory_xact_lock(func.hashtext(_CODE_LOCK_KEY))))
        prefix = f"PC{today:%Y%m%d}"
        max_code = await self.db.scalar(
            select(func.max(DeviationLedger.code)).where(DeviationLedger.code.like(f"{prefix}%"))
        )
        sequence = 1
        if max_code:
            tail = str(max_code)[len(prefix) :]
            if tail.isdigit():
                sequence = int(tail) + 1
        return f"{prefix}{sequence:03d}"

    async def create(self, **fields: Any) -> DeviationLedger:
        item = DeviationLedger(**fields)
        self.db.add(item)
        await self.db.flush()
        return item


class DeviationAttachmentCommentRepository:
    """附件批注仓储（按 ledger_id + file_id 归集）。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_file(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> list[DeviationAttachmentComment]:
        """按时间正序返回某附件的批注。"""
        stmt = (
            select(DeviationAttachmentComment)
            .where(
                DeviationAttachmentComment.ledger_id == ledger_id,
                DeviationAttachmentComment.file_id == file_id,
                DeviationAttachmentComment.is_deleted.is_(False),
            )
            .order_by(
                DeviationAttachmentComment.created_at.asc(),
                DeviationAttachmentComment.id.asc(),
            )
        )
        rows = (await self.db.scalars(stmt)).all()
        return list(rows)

    async def get(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        comment_id: uuid.UUID,
    ) -> DeviationAttachmentComment | None:
        stmt = select(DeviationAttachmentComment).where(
            DeviationAttachmentComment.id == comment_id,
            DeviationAttachmentComment.ledger_id == ledger_id,
            DeviationAttachmentComment.file_id == file_id,
            DeviationAttachmentComment.is_deleted.is_(False),
        )
        return cast(DeviationAttachmentComment | None, await self.db.scalar(stmt))

    async def create(self, **fields: Any) -> DeviationAttachmentComment:
        item = DeviationAttachmentComment(**fields)
        self.db.add(item)
        await self.db.flush()
        return item

    async def summary_by_ledger(
        self,
        ledger_id: uuid.UUID,
    ) -> list[tuple[uuid.UUID, int, int]]:
        """按附件聚合批注数：返回 [(file_id, open_count, total_count)]。"""
        stmt = (
            select(
                DeviationAttachmentComment.file_id,
                func.count().label("total_count"),
                func.count().filter(DeviationAttachmentComment.status == "open").label("open_count"),
            )
            .where(
                DeviationAttachmentComment.ledger_id == ledger_id,
                DeviationAttachmentComment.is_deleted.is_(False),
            )
            .group_by(DeviationAttachmentComment.file_id)
        )
        rows = (await self.db.execute(stmt)).all()
        return [(row.file_id, int(row.open_count or 0), int(row.total_count or 0)) for row in rows]

    async def soft_delete_by_file(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        *,
        actor_id: uuid.UUID,
    ) -> int:
        """附件被删除时级联软删其全部批注，返回受影响行数。"""
        result = await self.db.execute(
            update(DeviationAttachmentComment)
            .where(
                DeviationAttachmentComment.ledger_id == ledger_id,
                DeviationAttachmentComment.file_id == file_id,
                DeviationAttachmentComment.is_deleted.is_(False),  # noqa: E712
            )
            .values(is_deleted=True, updated_by=actor_id)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
