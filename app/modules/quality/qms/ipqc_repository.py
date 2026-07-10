"""IPQC (In-Process Quality Control) inspection repository"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.ipqc_models import (
    IPQCApprovalRecord,
    IPQCInspection,
    IPQCInspectionItem,
)
from app.modules.quality.qms.ipqc_schemas import (
    IPQCInspectionFilter,
)


class IPQCInspectionRepository:
    """IPQC检验单仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, inspection_id: UUID) -> IPQCInspection | None:
        """根据ID获取IPQC检验单"""
        result = await self.session.execute(
            select(IPQCInspection).where(
                and_(
                    IPQCInspection.id == inspection_id,
                    IPQCInspection.is_deleted == False,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_inspection_no(self, inspection_no: str) -> IPQCInspection | None:
        """根据单号查询"""
        result = await self.session.execute(
            select(IPQCInspection).where(
                and_(
                    IPQCInspection.inspection_no == inspection_no,
                    IPQCInspection.is_deleted == False,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        filters: IPQCInspectionFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[IPQCInspection], int]:
        """获取IPQC检验单列表"""
        query = select(IPQCInspection).where(IPQCInspection.is_deleted == False)

        if filters.inspection_no:
            query = query.where(
                IPQCInspection.inspection_no.ilike(f"%{filters.inspection_no}%")
            )
        if filters.batch_no:
            query = query.where(IPQCInspection.batch_no.ilike(f"%{filters.batch_no}%"))
        if filters.product_code:
            query = query.where(
                IPQCInspection.product_code.ilike(f"%{filters.product_code}%")
            )
        if filters.product_name:
            query = query.where(
                IPQCInspection.product_name.ilike(f"%{filters.product_name}%")
            )
        if filters.process_stage:
            query = query.where(
                IPQCInspection.process_stage.ilike(f"%{filters.process_stage}%")
            )
        if filters.status:
            query = query.where(IPQCInspection.status == filters.status.value)
        if filters.inspection_conclusion:
            query = query.where(
                IPQCInspection.inspection_conclusion
                == filters.inspection_conclusion.value
            )
        if filters.batch_locked is not None:
            query = query.where(IPQCInspection.batch_locked == filters.batch_locked)
        if filters.start_date:
            query = query.where(IPQCInspection.inspection_date >= filters.start_date)
        if filters.end_date:
            query = query.where(IPQCInspection.inspection_date <= filters.end_date)

        # Count query
        count_query = select(IPQCInspection.id).where(
            IPQCInspection.is_deleted == False
        )
        if filters.inspection_no:
            count_query = count_query.where(
                IPQCInspection.inspection_no.ilike(f"%{filters.inspection_no}%")
            )
        if filters.batch_no:
            count_query = count_query.where(
                IPQCInspection.batch_no.ilike(f"%{filters.batch_no}%")
            )
        if filters.product_code:
            count_query = count_query.where(
                IPQCInspection.product_code.ilike(f"%{filters.product_code}%")
            )
        if filters.product_name:
            count_query = count_query.where(
                IPQCInspection.product_name.ilike(f"%{filters.product_name}%")
            )
        if filters.process_stage:
            count_query = count_query.where(
                IPQCInspection.process_stage.ilike(f"%{filters.process_stage}%")
            )
        if filters.status:
            count_query = count_query.where(
                IPQCInspection.status == filters.status.value
            )
        if filters.inspection_conclusion:
            count_query = count_query.where(
                IPQCInspection.inspection_conclusion
                == filters.inspection_conclusion.value
            )
        if filters.batch_locked is not None:
            count_query = count_query.where(
                IPQCInspection.batch_locked == filters.batch_locked
            )
        if filters.start_date:
            count_query = count_query.where(
                IPQCInspection.inspection_date >= filters.start_date
            )
        if filters.end_date:
            count_query = count_query.where(
                IPQCInspection.inspection_date <= filters.end_date
            )

        count_result = await self.session.execute(count_query)
        total = len(count_result.all())

        # Order and paginate
        query = (
            query.order_by(IPQCInspection.created_at.desc()).offset(skip).limit(limit)
        )
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def generate_inspection_no(self) -> str:
        """生成检验单号"""
        today = datetime.now()
        prefix = f"IPQC{today.strftime('%Y%m%d')}"
        # 查找今天最大的序号
        result = await self.session.execute(
            select(IPQCInspection.inspection_no)
            .where(
                and_(
                    IPQCInspection.inspection_no.like(f"{prefix}%"),
                    IPQCInspection.is_deleted == False,
                )
            )
            .order_by(IPQCInspection.inspection_no.desc())
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


class IPQCInspectionItemRepository:
    """IPQC检验明细仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: UUID) -> IPQCInspectionItem | None:
        """根据ID获取明细"""
        result = await self.session.execute(
            select(IPQCInspectionItem).where(
                and_(
                    IPQCInspectionItem.id == item_id,
                    IPQCInspectionItem.is_deleted == False,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_inspection_id(
        self, inspection_id: UUID
    ) -> list[IPQCInspectionItem]:
        """根据检验单ID获取明细"""
        result = await self.session.execute(
            select(IPQCInspectionItem)
            .where(
                and_(
                    IPQCInspectionItem.ipqc_inspection_id == inspection_id,
                    IPQCInspectionItem.is_deleted == False,
                )
            )
            .order_by(IPQCInspectionItem.item_no)
        )
        return list(result.scalars().all())

    async def create_bulk(
        self,
        inspection_id: UUID,
        items_data: list[dict],
        created_by: UUID | None = None,
    ) -> list[IPQCInspectionItem]:
        """批量创建明细"""
        items = []
        for item_data in items_data:
            item = IPQCInspectionItem(
                ipqc_inspection_id=inspection_id,
                item_no=item_data.get("item_no", 1),
                inspection_item=item_data.get("inspection_item", ""),
                inspection_method=item_data.get("inspection_method"),
                standard_value=item_data.get("standard_value"),
                upper_limit=item_data.get("upper_limit"),
                lower_limit=item_data.get("lower_limit"),
                unit=item_data.get("unit"),
                measured_value=item_data.get("measured_value"),
                result=item_data.get("result"),
                is_repeat_test=item_data.get("is_repeat_test", False),
                repeat_times=item_data.get("repeat_times", 0),
                raw_data=item_data.get("raw_data"),
                remark=item_data.get("remark"),
                created_by=created_by,
            )
            self.session.add(item)
            items.append(item)
        return items


class IPQCApprovalRecordRepository:
    """IPQC审批记录仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_inspection_id(
        self, inspection_id: UUID
    ) -> list[IPQCApprovalRecord]:
        """根据检验单ID获取审批记录"""
        result = await self.session.execute(
            select(IPQCApprovalRecord)
            .where(
                and_(
                    IPQCApprovalRecord.ipqc_inspection_id == inspection_id,
                    IPQCApprovalRecord.is_deleted == False,
                )
            )
            .order_by(IPQCApprovalRecord.approval_level)
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
    ) -> IPQCApprovalRecord:
        """创建审批记录"""
        record = IPQCApprovalRecord(
            ipqc_inspection_id=inspection_id,
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
