"""Sampling management repository"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.sampling_models import (
    SampleRetentionLedger,
    SamplingApprovalRecord,
    SamplingOrder,
    SamplingOrderItem,
)
from app.modules.quality.qms.sampling_schemas import (
    RetentionLedgerFilter,
    SamplingOrderFilter,
)


class SamplingOrderRepository:
    """取样单仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: UUID) -> SamplingOrder | None:
        """根据ID获取取样单"""
        result = await self.session.execute(
            select(SamplingOrder).where(
                and_(SamplingOrder.id == order_id, not SamplingOrder.is_deleted)  # type: ignore[arg-type]
            )
        )
        return result.scalar_one_or_none()

    async def get_by_order_no(self, order_no: str) -> SamplingOrder | None:
        """根据单号查询"""
        result = await self.session.execute(
            select(SamplingOrder).where(
                and_(
                    SamplingOrder.order_no == order_no,
                    not SamplingOrder.is_deleted,  # type: ignore[arg-type]
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        filters: SamplingOrderFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SamplingOrder], int]:
        """获取取样单列表"""
        query = select(SamplingOrder).where(not SamplingOrder.is_deleted)  # type: ignore[arg-type]

        if filters.material_code:
            query = query.where(SamplingOrder.material_code.ilike(f"%{filters.material_code}%"))
        if filters.material_name:
            query = query.where(SamplingOrder.material_name.ilike(f"%{filters.material_name}%"))
        if filters.sampling_source:
            query = query.where(SamplingOrder.sampling_source == filters.sampling_source)
        if filters.status:
            query = query.where(SamplingOrder.status == filters.status)
        if filters.sampling_result:
            query = query.where(SamplingOrder.sampling_result == filters.sampling_result)
        if filters.order_no:
            query = query.where(SamplingOrder.order_no.ilike(f"%{filters.order_no}%"))
        if filters.start_date:
            query = query.where(SamplingOrder.sampling_date >= filters.start_date)
        if filters.end_date:
            query = query.where(SamplingOrder.sampling_date <= filters.end_date)

        # Count
        count_query = select(SamplingOrder.id)
        if filters.material_code:
            count_query = count_query.where(SamplingOrder.material_code.ilike(f"%{filters.material_code}%"))
        if filters.material_name:
            count_query = count_query.where(SamplingOrder.material_name.ilike(f"%{filters.material_name}%"))
        if filters.sampling_source:
            count_query = count_query.where(SamplingOrder.sampling_source == filters.sampling_source)
        if filters.status:
            count_query = count_query.where(SamplingOrder.status == filters.status)
        if filters.sampling_result:
            count_query = count_query.where(SamplingOrder.sampling_result == filters.sampling_result)
        if filters.order_no:
            count_query = count_query.where(SamplingOrder.order_no.ilike(f"%{filters.order_no}%"))
        if filters.start_date:
            count_query = count_query.where(SamplingOrder.sampling_date >= filters.start_date)
        if filters.end_date:
            count_query = count_query.where(SamplingOrder.sampling_date <= filters.end_date)
        count_result = await self.session.execute(count_query)
        total = len(count_result.all())

        # Order and paginate
        query = query.order_by(SamplingOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def generate_order_no(self) -> str:
        """生成取样单号"""
        today = datetime.now()
        prefix = f"CY{today.strftime('%Y%m%d')}"
        # 查找今天最大的序号
        result = await self.session.execute(
            select(SamplingOrder.order_no)
            .where(
                and_(
                    SamplingOrder.order_no.like(f"{prefix}%"),
                    not SamplingOrder.is_deleted,  # type: ignore[arg-type]
                )
            )
            .order_by(SamplingOrder.order_no.desc())
            .limit(1)
        )
        last_no = result.scalar_one_or_none()
        if last_no:
            try:
                seq = int(last_no[-4:]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"


class SamplingOrderItemRepository:
    """取样明细仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: UUID) -> SamplingOrderItem | None:
        """根据ID获取明细"""
        result = await self.session.execute(
            select(SamplingOrderItem).where(
                and_(
                    SamplingOrderItem.id == item_id,
                    not SamplingOrderItem.is_deleted,  # type: ignore[arg-type]
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_sampling_order_id(self, sampling_order_id: UUID) -> list[SamplingOrderItem]:
        """根据取样单ID获取明细"""
        result = await self.session.execute(
            select(SamplingOrderItem)
            .where(
                and_(
                    SamplingOrderItem.sampling_order_id == sampling_order_id,
                    not SamplingOrderItem.is_deleted,  # type: ignore[arg-type]
                )
            )
            .order_by(SamplingOrderItem.item_no)
        )
        return list(result.scalars().all())

    async def generate_sample_no(self, order_no: str, item_no: int) -> str:
        """生成样品编号"""
        return f"{order_no}-YP{item_no:03d}"


class SampleRetentionLedgerRepository:
    """留样台账仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_list(
        self,
        filters: RetentionLedgerFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SampleRetentionLedger], int]:
        """获取留样台账列表"""
        query = select(SampleRetentionLedger).where(
            not SampleRetentionLedger.is_deleted  # type: ignore[arg-type]
        )

        if filters.material_code:
            query = query.where(SampleRetentionLedger.material_code.ilike(f"%{filters.material_code}%"))
        if filters.material_name:
            query = query.where(SampleRetentionLedger.material_name.ilike(f"%{filters.material_name}%"))
        if filters.retention_status:
            query = query.where(SampleRetentionLedger.retention_status == filters.retention_status)
        if filters.order_no:
            query = query.where(SampleRetentionLedger.order_no.ilike(f"%{filters.order_no}%"))
        if filters.sample_no:
            query = query.where(SampleRetentionLedger.sample_no.ilike(f"%{filters.sample_no}%"))

        # Count
        count_query = select(SampleRetentionLedger.id)
        if filters.material_code:
            count_query = count_query.where(SampleRetentionLedger.material_code.ilike(f"%{filters.material_code}%"))
        if filters.material_name:
            count_query = count_query.where(SampleRetentionLedger.material_name.ilike(f"%{filters.material_name}%"))
        if filters.retention_status:
            count_query = count_query.where(SampleRetentionLedger.retention_status == filters.retention_status)
        if filters.order_no:
            count_query = count_query.where(SampleRetentionLedger.order_no.ilike(f"%{filters.order_no}%"))
        if filters.sample_no:
            count_query = count_query.where(SampleRetentionLedger.sample_no.ilike(f"%{filters.sample_no}%"))
        count_result = await self.session.execute(count_query)
        total = len(count_result.all())

        query = query.order_by(SampleRetentionLedger.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_sampling_order_id(self, sampling_order_id: UUID) -> list[SampleRetentionLedger]:
        """根据取样单ID获取留样记录"""
        result = await self.session.execute(
            select(SampleRetentionLedger).where(
                and_(
                    SampleRetentionLedger.sampling_order_id == sampling_order_id,
                    not SampleRetentionLedger.is_deleted,  # type: ignore[arg-type]
                )
            )
        )
        return list(result.scalars().all())


class SamplingApprovalRecordRepository:
    """取样审批记录仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_sampling_order_id(self, sampling_order_id: UUID) -> list[SamplingApprovalRecord]:
        """根据取样单ID获取审批记录"""
        result = await self.session.execute(
            select(SamplingApprovalRecord)
            .where(
                and_(
                    SamplingApprovalRecord.sampling_order_id == sampling_order_id,
                    not SamplingApprovalRecord.is_deleted,  # type: ignore[arg-type]
                )
            )
            .order_by(SamplingApprovalRecord.approval_level)
        )
        return list(result.scalars().all())

    async def get_pending_approvals(self, approver_role: str) -> list[SamplingApprovalRecord]:
        """获取待审批记录"""
        result = await self.session.execute(
            select(SamplingApprovalRecord)
            .where(
                and_(
                    SamplingApprovalRecord.approver_role == approver_role,
                    SamplingApprovalRecord.approval_status == "pending",
                    not SamplingApprovalRecord.is_deleted,  # type: ignore[arg-type]
                )
            )
            .order_by(SamplingApprovalRecord.created_at)
        )
        return list(result.scalars().all())
