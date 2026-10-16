"""FQC (Finished Product Quality Control) inspection repository"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.fqc_models import (
    FQCApprovalRecord,
    FQCInspection,
    FQCInspectionItem,
)
from app.modules.quality.qms.fqc_schemas import (
    FQCInspectionFilter,
)


class FQCInspectionRepository:
    """FQC检验单仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, inspection_id: UUID) -> FQCInspection | None:
        """根据ID获取FQC检验单"""
        result = await self.session.execute(
            select(FQCInspection).where(
                and_(
                    FQCInspection.id == inspection_id,
                    ~FQCInspection.is_deleted,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_inspection_no(self, inspection_no: str) -> FQCInspection | None:
        """根据单号查询"""
        result = await self.session.execute(
            select(FQCInspection).where(
                and_(
                    FQCInspection.inspection_no == inspection_no,
                    ~FQCInspection.is_deleted,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        filters: FQCInspectionFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[FQCInspection], int]:
        """获取FQC检验单列表"""
        query = select(FQCInspection).where(~FQCInspection.is_deleted)

        if filters.inspection_no:
            query = query.where(FQCInspection.inspection_no.ilike(f"%{filters.inspection_no}%"))
        if filters.batch_no:
            query = query.where(FQCInspection.batch_no.ilike(f"%{filters.batch_no}%"))
        if filters.product_code:
            query = query.where(FQCInspection.product_code.ilike(f"%{filters.product_code}%"))
        if filters.product_name:
            query = query.where(FQCInspection.product_name.ilike(f"%{filters.product_name}%"))
        if filters.production_workshop:
            query = query.where(FQCInspection.production_workshop.ilike(f"%{filters.production_workshop}%"))
        if filters.status:
            query = query.where(FQCInspection.status == filters.status.value)
        if filters.inspection_conclusion:
            query = query.where(FQCInspection.inspection_conclusion == filters.inspection_conclusion.value)
        if filters.release_status:
            query = query.where(FQCInspection.release_status == filters.release_status.value)
        if filters.batch_locked is not None:
            query = query.where(FQCInspection.batch_locked == filters.batch_locked)
        if filters.start_date:
            query = query.where(FQCInspection.inspection_date >= filters.start_date)
        if filters.end_date:
            query = query.where(FQCInspection.inspection_date <= filters.end_date)

        # Count query
        count_query = select(FQCInspection.id).where(~FQCInspection.is_deleted)
        if filters.inspection_no:
            count_query = count_query.where(FQCInspection.inspection_no.ilike(f"%{filters.inspection_no}%"))
        if filters.batch_no:
            count_query = count_query.where(FQCInspection.batch_no.ilike(f"%{filters.batch_no}%"))
        if filters.product_code:
            count_query = count_query.where(FQCInspection.product_code.ilike(f"%{filters.product_code}%"))
        if filters.product_name:
            count_query = count_query.where(FQCInspection.product_name.ilike(f"%{filters.product_name}%"))
        if filters.production_workshop:
            count_query = count_query.where(FQCInspection.production_workshop.ilike(f"%{filters.production_workshop}%"))
        if filters.status:
            count_query = count_query.where(FQCInspection.status == filters.status.value)
        if filters.inspection_conclusion:
            count_query = count_query.where(FQCInspection.inspection_conclusion == filters.inspection_conclusion.value)
        if filters.release_status:
            count_query = count_query.where(FQCInspection.release_status == filters.release_status.value)
        if filters.batch_locked is not None:
            count_query = count_query.where(FQCInspection.batch_locked == filters.batch_locked)
        if filters.start_date:
            count_query = count_query.where(FQCInspection.inspection_date >= filters.start_date)
        if filters.end_date:
            count_query = count_query.where(FQCInspection.inspection_date <= filters.end_date)

        count_result = await self.session.execute(count_query)
        total = len(count_result.all())

        # Order and paginate
        query = query.order_by(FQCInspection.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def generate_inspection_no(self) -> str:
        """生成检验单号"""
        today = datetime.now()
        prefix = f"FQC{today.strftime('%Y%m%d')}"
        # 查找今天最大的序号
        result = await self.session.execute(
            select(FQCInspection.inspection_no)
            .where(
                and_(
                    FQCInspection.inspection_no.like(f"{prefix}%"),
                    ~FQCInspection.is_deleted,
                )
            )
            .order_by(FQCInspection.inspection_no.desc())
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

    async def generate_report_no(self) -> str:
        """生成检验报告书编号"""
        today = datetime.now()
        prefix = f"COA{today.strftime('%Y%m%d')}"
        result = await self.session.execute(
            select(FQCInspection.report_no)
            .where(
                and_(
                    FQCInspection.report_no.like(f"{prefix}%"),
                    ~FQCInspection.is_deleted,
                    FQCInspection.report_no.isnot(None),
                )
            )
            .order_by(FQCInspection.report_no.desc())
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


class FQCInspectionItemRepository:
    """FQC检验明细仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: UUID) -> FQCInspectionItem | None:
        """根据ID获取明细"""
        result = await self.session.execute(
            select(FQCInspectionItem).where(
                and_(
                    FQCInspectionItem.id == item_id,
                    ~FQCInspectionItem.is_deleted,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_inspection_id(self, inspection_id: UUID) -> list[FQCInspectionItem]:
        """根据检验单ID获取明细"""
        result = await self.session.execute(
            select(FQCInspectionItem)
            .where(
                and_(
                    FQCInspectionItem.fqc_inspection_id == inspection_id,
                    ~FQCInspectionItem.is_deleted,
                )
            )
            .order_by(FQCInspectionItem.item_no)
        )
        return list(result.scalars().all())

    async def create_bulk(
        self,
        inspection_id: UUID,
        items_data: list[dict[str, Any]],
        created_by: UUID | None = None,
    ) -> list[FQCInspectionItem]:
        """批量创建明细"""
        items = []
        for item_data in items_data:
            item = FQCInspectionItem(
                fqc_inspection_id=inspection_id,
                item_no=item_data.get("item_no", 1),
                inspection_category=item_data.get("inspection_category"),
                inspection_item=item_data.get("inspection_item", ""),
                inspection_method=item_data.get("inspection_method"),
                standard_value=item_data.get("standard_value"),
                unit=item_data.get("unit"),
                measured_value=item_data.get("measured_value"),
                result=item_data.get("result"),
                is_oos=item_data.get("is_oos", False),
                oos_description=item_data.get("oos_description"),
                is_repeat_test=item_data.get("is_repeat_test", False),
                repeat_times=item_data.get("repeat_times", 0),
                chromatogram_urls=item_data.get("chromatogram_urls"),
                raw_record_url=item_data.get("raw_record_url"),
                remark=item_data.get("remark"),
                created_by=created_by,
            )
            self.session.add(item)
            items.append(item)
        return items


class FQCApprovalRecordRepository:
    """FQC审批记录仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_inspection_id(self, inspection_id: UUID) -> list[FQCApprovalRecord]:
        """根据检验单ID获取审批记录"""
        result = await self.session.execute(
            select(FQCApprovalRecord)
            .where(
                and_(
                    FQCApprovalRecord.fqc_inspection_id == inspection_id,
                    ~FQCApprovalRecord.is_deleted,
                )
            )
            .order_by(FQCApprovalRecord.approval_level)
        )
        return list(result.scalars().all())

    async def create_approval_record(
        self,
        inspection_id: UUID,
        approval_level: int,
        approval_status: str,
        approver_role: str | None = None,
        approver_id: UUID | None = None,
        approver_name: str | None = None,
        comments: str | None = None,
        created_by: UUID | None = None,
    ) -> FQCApprovalRecord:
        """创建审批记录"""
        record = FQCApprovalRecord(
            fqc_inspection_id=inspection_id,
            approval_level=approval_level,
            approval_status=approval_status,
            approver_role=approver_role,
            approver_id=approver_id,
            approver_name=approver_name,
            comments=comments,
            created_by=created_by,
        )
        self.session.add(record)
        return record
