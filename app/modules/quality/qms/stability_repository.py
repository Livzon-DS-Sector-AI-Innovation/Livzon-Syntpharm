"""Stability Study (稳定性试验) repository"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.stability_models import (
    StabilityApprovalRecord,
    StabilityInspection,
    StabilityInspectionItem,
    StabilitySampleNode,
    StabilityStudy,
)


class StabilityStudyRepository:
    """稳定性试验仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, study_id: UUID) -> Optional[StabilityStudy]:
        """根据ID获取稳定性试验"""
        result = await self.session.execute(
            select(StabilityStudy).where(
                and_(StabilityStudy.id == study_id, StabilityStudy.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_study_no(self, study_no: str) -> Optional[StabilityStudy]:
        """根据方案编号查询"""
        result = await self.session.execute(
            select(StabilityStudy).where(
                and_(StabilityStudy.study_no == study_no, StabilityStudy.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        filters: "StabilityStudyFilter",
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StabilityStudy], int]:
        """获取稳定性试验列表"""
        query = select(StabilityStudy).where(StabilityStudy.is_deleted == False)

        if filters.study_no:
            query = query.where(StabilityStudy.study_no.ilike(f"%{filters.study_no}%"))
        if filters.product_code:
            query = query.where(StabilityStudy.product_code.ilike(f"%{filters.product_code}%"))
        if filters.product_name:
            query = query.where(StabilityStudy.product_name.ilike(f"%{filters.product_name}%"))
        if filters.batch_no:
            query = query.where(StabilityStudy.batch_no.ilike(f"%{filters.batch_no}%"))
        if filters.study_type:
            query = query.where(StabilityStudy.study_type == filters.study_type.value)
        if filters.status:
            query = query.where(StabilityStudy.status == filters.status.value)
        if filters.start_date:
            query = query.where(StabilityStudy.start_date >= filters.start_date)
        if filters.end_date:
            query = query.where(StabilityStudy.end_date <= filters.end_date)

        # Count query
        count_query = select(StabilityStudy.id).where(StabilityStudy.is_deleted == False)
        if filters.study_no:
            count_query = count_query.where(StabilityStudy.study_no.ilike(f"%{filters.study_no}%"))
        if filters.product_code:
            count_query = count_query.where(StabilityStudy.product_code.ilike(f"%{filters.product_code}%"))
        if filters.product_name:
            count_query = count_query.where(StabilityStudy.product_name.ilike(f"%{filters.product_name}%"))
        if filters.batch_no:
            count_query = count_query.where(StabilityStudy.batch_no.ilike(f"%{filters.batch_no}%"))
        if filters.study_type:
            count_query = count_query.where(StabilityStudy.study_type == filters.study_type.value)
        if filters.status:
            count_query = count_query.where(StabilityStudy.status == filters.status.value)

        count_result = await self.session.execute(count_query)
        total = len(count_result.all())

        # Order and paginate
        query = query.order_by(StabilityStudy.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def generate_study_no(self) -> str:
        """生成方案编号"""
        today = datetime.now()
        prefix = f"STB{today.strftime('%Y%m%d')}"
        result = await self.session.execute(
            select(StabilityStudy.study_no).where(
                and_(
                    StabilityStudy.study_no.like(f"{prefix}%"),
                    StabilityStudy.is_deleted == False,
                )
            ).order_by(StabilityStudy.study_no.desc()).limit(1)
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


class StabilitySampleNodeRepository:
    """取样节点仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, node_id: UUID) -> Optional[StabilitySampleNode]:
        """根据ID获取节点"""
        result = await self.session.execute(
            select(StabilitySampleNode).where(
                and_(StabilitySampleNode.id == node_id, StabilitySampleNode.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_study_id(self, study_id: UUID) -> list[StabilitySampleNode]:
        """根据试验ID获取所有节点"""
        result = await self.session.execute(
            select(StabilitySampleNode).where(
                and_(
                    StabilitySampleNode.stability_study_id == study_id,
                    StabilitySampleNode.is_deleted == False,
                )
            ).order_by(StabilitySampleNode.node_no)
        )
        return list(result.scalars().all())

    async def get_upcoming_reminders(self, days: int = 7) -> list[StabilitySampleNode]:
        """获取即将到期的取样节点"""
        from datetime import timedelta
        future_date = datetime.now() + timedelta(days=days)
        result = await self.session.execute(
            select(StabilitySampleNode).where(
                and_(
                    StabilitySampleNode.planned_date <= future_date,
                    StabilitySampleNode.planned_date >= datetime.now(),
                    StabilitySampleNode.status == "pending",
                    StabilitySampleNode.reminder_sent == False,
                    StabilitySampleNode.is_deleted == False,
                )
            ).order_by(StabilitySampleNode.planned_date)
        )
        return list(result.scalars().all())

    async def create_bulk(self, study_id: UUID, nodes_data: list[dict], created_by: UUID | None = None) -> list[StabilitySampleNode]:
        """批量创建节点"""
        nodes = []
        for node_data in nodes_data:
            node = StabilitySampleNode(
                stability_study_id=study_id,
                node_no=node_data.get("node_no", 1),
                node_month=node_data.get("node_month", 0),
                node_name=node_data.get("node_name", f"{node_data.get('node_month', 0)}月"),
                planned_date=node_data.get("planned_date"),
                status="pending",
                created_by=created_by,
            )
            self.session.add(node)
            nodes.append(node)
        await self.session.flush()
        return nodes


class StabilityInspectionRepository:
    """稳定性检验记录仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, inspection_id: UUID) -> Optional[StabilityInspection]:
        """根据ID获取检验记录"""
        result = await self.session.execute(
            select(StabilityInspection).where(
                and_(StabilityInspection.id == inspection_id, StabilityInspection.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_inspection_no(self, inspection_no: str) -> Optional[StabilityInspection]:
        """根据单号查询"""
        result = await self.session.execute(
            select(StabilityInspection).where(
                and_(StabilityInspection.inspection_no == inspection_no, StabilityInspection.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_study_id(self, study_id: UUID) -> list[StabilityInspection]:
        """根据试验ID获取所有检验记录"""
        result = await self.session.execute(
            select(StabilityInspection).where(
                and_(
                    StabilityInspection.study_id == study_id,
                    StabilityInspection.is_deleted == False,
                )
            ).order_by(StabilityInspection.node_month)
        )
        return list(result.scalars().all())

    async def get_by_node_id(self, node_id: UUID) -> Optional[StabilityInspection]:
        """根据节点ID获取检验记录"""
        result = await self.session.execute(
            select(StabilityInspection).where(
                and_(
                    StabilityInspection.sample_node_id == node_id,
                    StabilityInspection.is_deleted == False,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        study_id: UUID | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StabilityInspection], int]:
        """获取检验记录列表"""
        query = select(StabilityInspection).where(StabilityInspection.is_deleted == False)

        if study_id:
            query = query.where(StabilityInspection.study_id == study_id)

        # Count query
        count_query = select(StabilityInspection.id).where(StabilityInspection.is_deleted == False)
        if study_id:
            count_query = count_query.where(StabilityInspection.study_id == study_id)

        count_result = await self.session.execute(count_query)
        total = len(count_result.all())

        # Order and paginate
        query = query.order_by(StabilityInspection.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def generate_inspection_no(self) -> str:
        """生成检验单号"""
        today = datetime.now()
        prefix = f"STI{today.strftime('%Y%m%d')}"
        result = await self.session.execute(
            select(StabilityInspection.inspection_no).where(
                and_(
                    StabilityInspection.inspection_no.like(f"{prefix}%"),
                    StabilityInspection.is_deleted == False,
                )
            ).order_by(StabilityInspection.inspection_no.desc()).limit(1)
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


class StabilityInspectionItemRepository:
    """稳定性检验明细仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: UUID) -> Optional[StabilityInspectionItem]:
        """根据ID获取明细"""
        result = await self.session.execute(
            select(StabilityInspectionItem).where(
                and_(StabilityInspectionItem.id == item_id, StabilityInspectionItem.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_inspection_id(self, inspection_id: UUID) -> list[StabilityInspectionItem]:
        """根据检验ID获取明细"""
        result = await self.session.execute(
            select(StabilityInspectionItem).where(
                and_(
                    StabilityInspectionItem.stability_inspection_id == inspection_id,
                    StabilityInspectionItem.is_deleted == False,
                )
            ).order_by(StabilityInspectionItem.item_no)
        )
        return list(result.scalars().all())

    async def create_bulk(self, inspection_id: UUID, items_data: list[dict], created_by: UUID | None = None) -> list[StabilityInspectionItem]:
        """批量创建明细"""
        items = []
        for item_data in items_data:
            item = StabilityInspectionItem(
                stability_inspection_id=inspection_id,
                item_no=item_data.get("item_no", 1),
                inspection_item=item_data.get("inspection_item", ""),
                inspection_method=item_data.get("inspection_method"),
                standard_value=item_data.get("standard_value"),
                unit=item_data.get("unit"),
                measured_value=item_data.get("measured_value"),
                result=item_data.get("result"),
                is_oos=item_data.get("is_oos", False),
                oos_description=item_data.get("oos_description"),
                data_point=item_data.get("data_point"),
                chromatogram_urls=item_data.get("chromatogram_urls"),
                remark=item_data.get("remark"),
                created_by=created_by,
            )
            self.session.add(item)
            items.append(item)
        return items


class StabilityApprovalRecordRepository:
    """稳定性审批记录仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_study_id(self, study_id: UUID) -> list[StabilityApprovalRecord]:
        """根据试验ID获取审批记录"""
        result = await self.session.execute(
            select(StabilityApprovalRecord).where(
                and_(
                    StabilityApprovalRecord.study_id == study_id,
                    StabilityApprovalRecord.is_deleted == False,
                )
            ).order_by(StabilityApprovalRecord.approval_level)
        )
        return list(result.scalars().all())

    async def get_by_inspection_id(self, inspection_id: UUID) -> list[StabilityApprovalRecord]:
        """根据检验ID获取审批记录"""
        result = await self.session.execute(
            select(StabilityApprovalRecord).where(
                and_(
                    StabilityApprovalRecord.inspection_id == inspection_id,
                    StabilityApprovalRecord.is_deleted == False,
                )
            ).order_by(StabilityApprovalRecord.approval_level)
        )
        return list(result.scalars().all())

    async def create_record(
        self,
        study_id: UUID | None,
        inspection_id: UUID | None,
        approval_type: str,
        approval_level: int,
        approval_status: str,
        approver_role: str | None = None,
        approver_id: UUID | None = None,
        approver_name: str | None = None,
        comments: str | None = None,
        created_by: UUID | None = None,
    ) -> StabilityApprovalRecord:
        """创建审批记录"""
        record = StabilityApprovalRecord(
            study_id=study_id,
            inspection_id=inspection_id,
            approval_type=approval_type,
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
