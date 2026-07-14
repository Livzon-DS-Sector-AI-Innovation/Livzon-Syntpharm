"""IQC (Incoming Quality Control) inspection repository"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.iqc_models import (
    IQCApprovalRecord,
    IQCInspection,
    IQCInspectionItem,
)
from app.modules.quality.qms.iqc_schemas import (
    IQCInspectionFilter,
)


class IQCInspectionRepository:
    """IQC检验单仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, inspection_id: UUID) -> IQCInspection | None:
        """根据ID获取IQC检验单"""
        result = await self.session.execute(
            select(IQCInspection).where(
                and_(
                    IQCInspection.id == inspection_id,
                    not IQCInspection.is_deleted,  # type: ignore[arg-type]
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_inspection_no(self, inspection_no: str) -> IQCInspection | None:
        """根据单号查询"""
        result = await self.session.execute(
            select(IQCInspection).where(
                and_(
                    IQCInspection.inspection_no == inspection_no,
                    not IQCInspection.is_deleted,  # type: ignore[arg-type]
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        filters: IQCInspectionFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[IQCInspection], int]:
        """获取IQC检验单列表"""
        query = select(IQCInspection).where(not IQCInspection.is_deleted)  # type: ignore[arg-type]

        if filters.material_code:
            query = query.where(IQCInspection.material_code.ilike(f"%{filters.material_code}%"))
        if filters.material_name:
            query = query.where(IQCInspection.material_name.ilike(f"%{filters.material_name}%"))
        if filters.material_category:
            query = query.where(IQCInspection.material_category == filters.material_category.value)
        if filters.supplier_name:
            query = query.where(IQCInspection.supplier_name.ilike(f"%{filters.supplier_name}%"))
        if filters.status:
            query = query.where(IQCInspection.status == filters.status.value)
        if filters.inspection_conclusion:
            query = query.where(IQCInspection.inspection_conclusion == filters.inspection_conclusion.value)
        if filters.inspection_no:
            query = query.where(IQCInspection.inspection_no.ilike(f"%{filters.inspection_no}%"))
        if filters.start_date:
            query = query.where(IQCInspection.inspection_date >= filters.start_date)
        if filters.end_date:
            query = query.where(IQCInspection.inspection_date <= filters.end_date)

        # Count query
        count_query = select(IQCInspection.id).where(not IQCInspection.is_deleted)  # type: ignore[arg-type]
        if filters.material_code:
            count_query = count_query.where(IQCInspection.material_code.ilike(f"%{filters.material_code}%"))
        if filters.material_name:
            count_query = count_query.where(IQCInspection.material_name.ilike(f"%{filters.material_name}%"))
        if filters.material_category:
            count_query = count_query.where(IQCInspection.material_category == filters.material_category.value)
        if filters.supplier_name:
            count_query = count_query.where(IQCInspection.supplier_name.ilike(f"%{filters.supplier_name}%"))
        if filters.status:
            count_query = count_query.where(IQCInspection.status == filters.status.value)
        if filters.inspection_conclusion:
            count_query = count_query.where(IQCInspection.inspection_conclusion == filters.inspection_conclusion.value)
        if filters.inspection_no:
            count_query = count_query.where(IQCInspection.inspection_no.ilike(f"%{filters.inspection_no}%"))
        if filters.start_date:
            count_query = count_query.where(IQCInspection.inspection_date >= filters.start_date)
        if filters.end_date:
            count_query = count_query.where(IQCInspection.inspection_date <= filters.end_date)

        count_result = await self.session.execute(count_query)
        total = len(count_result.all())

        # Order and paginate
        query = query.order_by(IQCInspection.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def generate_inspection_no(self) -> str:
        """生成检验单号"""
        today = datetime.now()
        prefix = f"IQC{today.strftime('%Y%m%d')}"
        # 查找今天最大的序号
        result = await self.session.execute(
            select(IQCInspection.inspection_no)
            .where(
                and_(
                    IQCInspection.inspection_no.like(f"{prefix}%"),
                    not IQCInspection.is_deleted,  # type: ignore[arg-type]
                )
            )
            .order_by(IQCInspection.inspection_no.desc())
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


class IQCInspectionItemRepository:
    """IQC检验明细仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: UUID) -> IQCInspectionItem | None:
        """根据ID获取明细"""
        result = await self.session.execute(
            select(IQCInspectionItem).where(
                and_(
                    IQCInspectionItem.id == item_id,
                    not IQCInspectionItem.is_deleted,  # type: ignore[arg-type]
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_inspection_id(self, inspection_id: UUID) -> list[IQCInspectionItem]:
        """根据检验单ID获取明细"""
        result = await self.session.execute(
            select(IQCInspectionItem)
            .where(
                and_(
                    IQCInspectionItem.iqc_inspection_id == inspection_id,
                    not IQCInspectionItem.is_deleted,  # type: ignore[arg-type]
                )
            )
            .order_by(IQCInspectionItem.item_no)
        )
        return list(result.scalars().all())

    async def create_bulk(
        self,
        inspection_id: UUID,
        items_data: list[dict[str, Any]],
        created_by: UUID | None = None,
    ) -> list[IQCInspectionItem]:
        """批量创建明细"""
        items = []
        for item_data in items_data:
            item = IQCInspectionItem(
                iqc_inspection_id=inspection_id,
                item_no=item_data.get("item_no", 1),
                inspection_item=item_data.get("inspection_item", ""),
                inspection_method=item_data.get("inspection_method"),
                standard_value=item_data.get("standard_value"),
                unit=item_data.get("unit"),
                measured_value=item_data.get("measured_value"),
                result=item_data.get("result"),
                is_repeat_test=item_data.get("is_repeat_test", False),
                raw_data=item_data.get("raw_data"),
                remark=item_data.get("remark"),
                created_by=created_by,
            )
            self.session.add(item)
            items.append(item)
        return items


class IQCApprovalRecordRepository:
    """IQC审批记录仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_inspection_id(self, inspection_id: UUID) -> list[IQCApprovalRecord]:
        """根据检验单ID获取审批记录"""
        result = await self.session.execute(
            select(IQCApprovalRecord)
            .where(
                and_(
                    IQCApprovalRecord.iqc_inspection_id == inspection_id,
                    not IQCApprovalRecord.is_deleted,  # type: ignore[arg-type]
                )
            )
            .order_by(IQCApprovalRecord.approval_level)
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
    ) -> IQCApprovalRecord:
        """创建审批记录"""
        record = IQCApprovalRecord(
            iqc_inspection_id=inspection_id,
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
