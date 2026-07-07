"""Quality database queries live here."""

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.quality.qms.models import (
    InspectionStandard,
    InspectionStandardItem,
    StandardApprovalRecord,
)


class QualityRepository:
    """Quality module repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============ InspectionStandard Operations ============

    async def get_standards(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        material_code: str | None = None,
        material_name: str | None = None,
        material_category: str | None = None,
        pharmacopeia: str | None = None,
        version: str | None = None,
        is_effective: bool | None = None,
    ) -> tuple[list[InspectionStandard], int]:
        """获取检验标准列表"""
        query = select(InspectionStandard).where(InspectionStandard.is_deleted == False)

        if status:
            query = query.where(InspectionStandard.status == status)
        if material_code:
            query = query.where(
                InspectionStandard.material_code.contains(material_code)
            )
        if material_name:
            query = query.where(
                InspectionStandard.material_name.contains(material_name)
            )
        if material_category:
            query = query.where(
                InspectionStandard.material_category == material_category
            )
        if pharmacopeia:
            query = query.where(InspectionStandard.pharmacopeia == pharmacopeia)
        if version:
            query = query.where(InspectionStandard.version == version)
        if is_effective is not None:
            query = (
                query.where(InspectionStandard.status == "effective")
                if is_effective
                else query
            )

        count_query = select(func.count(InspectionStandard.id)).where(
            InspectionStandard.is_deleted == False
        )
        if status:
            count_query = count_query.where(InspectionStandard.status == status)
        if material_code:
            count_query = count_query.where(
                InspectionStandard.material_code.contains(material_code)
            )
        if material_name:
            count_query = count_query.where(
                InspectionStandard.material_name.contains(material_name)
            )
        if material_category:
            count_query = count_query.where(
                InspectionStandard.material_category == material_category
            )
        if pharmacopeia:
            count_query = count_query.where(
                InspectionStandard.pharmacopeia == pharmacopeia
            )

        total = await self.session.scalar(count_query)
        query = (
            query.offset(skip)
            .limit(limit)
            .order_by(InspectionStandard.created_at.desc())
        )
        result = await self.session.execute(query)
        standards = list(result.scalars().all())
        return standards, total or 0

    async def get_standard_by_id(
        self, standard_id: uuid.UUID
    ) -> InspectionStandard | None:
        """获取检验标准详情"""
        query = (
            select(InspectionStandard)
            .options(
                selectinload(InspectionStandard.items),
                selectinload(InspectionStandard.approval_records),
            )
            .where(
                InspectionStandard.id == standard_id,
                InspectionStandard.is_deleted == False,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_standard_by_material_version(
        self, material_code: str, version: str
    ) -> InspectionStandard | None:
        """根据物料编码和版本获取检验标准"""
        query = (
            select(InspectionStandard)
            .options(selectinload(InspectionStandard.items))
            .where(
                InspectionStandard.material_code == material_code,
                InspectionStandard.version == version,
                InspectionStandard.is_deleted == False,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_version(self, material_code: str) -> str | None:
        """获取某物料的最新版本号"""
        query = (
            select(InspectionStandard.version)
            .where(
                InspectionStandard.material_code == material_code,
                InspectionStandard.is_deleted == False,
            )
            .order_by(InspectionStandard.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_standard(self, data: dict[str, Any]) -> InspectionStandard:
        """创建检验标准"""
        standard = InspectionStandard(**data)
        self.session.add(standard)
        await self.session.flush()
        await self.session.refresh(standard)
        return standard

    async def update_standard(
        self, standard_id: uuid.UUID, data: dict[str, Any]
    ) -> InspectionStandard | None:
        """更新检验标准"""
        query = (
            update(InspectionStandard)
            .where(
                InspectionStandard.id == standard_id,
                InspectionStandard.is_deleted == False,
            )
            .values(**data)
            .returning(InspectionStandard)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete_standard(self, standard_id: uuid.UUID) -> bool:
        """删除检验标准(软删除)"""
        query = (
            update(InspectionStandard)
            .where(
                InspectionStandard.id == standard_id,
                InspectionStandard.is_deleted == False,
            )
            .values(is_deleted=True)
        )
        result = await self.session.execute(query)
        return result.rowcount > 0

    async def submit_for_approval(
        self, standard_id: uuid.UUID
    ) -> InspectionStandard | None:
        """提交审批"""
        return await self.update_standard(standard_id, {"status": "tech_review"})

    async def approve_standard(
        self, standard_id: uuid.UUID, next_status: str
    ) -> InspectionStandard | None:
        """审批通过"""
        return await self.update_standard(standard_id, {"status": next_status})

    async def reject_standard(
        self, standard_id: uuid.UUID, comments: str | None = None
    ) -> InspectionStandard | None:
        """驳回标准"""
        return await self.update_standard(standard_id, {"status": "rejected"})

    async def obsolete_standard(
        self, standard_id: uuid.UUID, obsolete_reason: str
    ) -> InspectionStandard | None:
        """作废标准"""
        return await self.update_standard(
            standard_id,
            {
                "is_obsolete": True,
                "obsolete_reason": obsolete_reason,
                "status": "obsolete",
            },
        )

    # ============ InspectionStandardItem Operations ============

    async def get_items_by_standard(
        self, standard_id: uuid.UUID
    ) -> list[InspectionStandardItem]:
        """获取检验项目列表"""
        query = (
            select(InspectionStandardItem)
            .where(
                InspectionStandardItem.standard_id == standard_id,
                InspectionStandardItem.is_deleted == False,
            )
            .order_by(InspectionStandardItem.item_no)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_items_bulk(
        self, standard_id: uuid.UUID, items_data: list[dict[str, Any]]
    ) -> list[InspectionStandardItem]:
        """批量创建检验项目"""
        items = []
        for item_data in items_data:
            item = InspectionStandardItem(standard_id=standard_id, **item_data)
            self.session.add(item)
            items.append(item)
        await self.session.flush()
        for item in items:
            await self.session.refresh(item)
        return items

    async def delete_items_by_standard(self, standard_id: uuid.UUID) -> bool:
        """删除标准下的所有检验项目"""
        query = (
            update(InspectionStandardItem)
            .where(InspectionStandardItem.standard_id == standard_id)
            .values(is_deleted=True)
        )
        await self.session.execute(query)
        return True

    async def update_standard_items(
        self, standard_id: uuid.UUID, items_data: list[dict[str, Any]]
    ) -> list[InspectionStandardItem]:
        """更新检验项目(先删后增)"""
        await self.delete_items_by_standard(standard_id)
        return await self.create_items_bulk(standard_id, items_data)

    # ============ ApprovalRecord Operations ============

    async def get_approval_records(
        self, standard_id: uuid.UUID
    ) -> list[StandardApprovalRecord]:
        """获取审批记录列表"""
        query = (
            select(StandardApprovalRecord)
            .where(
                StandardApprovalRecord.standard_id == standard_id,
                StandardApprovalRecord.is_deleted == False,
            )
            .order_by(StandardApprovalRecord.approval_level)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_approval_record(
        self, data: dict[str, Any]
    ) -> StandardApprovalRecord:
        """创建审批记录"""
        record = StandardApprovalRecord(**data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get_pending_approvers(
        self, standard_id: uuid.UUID
    ) -> list[StandardApprovalRecord]:
        """获取待审批记录"""
        query = (
            select(StandardApprovalRecord)
            .where(
                StandardApprovalRecord.standard_id == standard_id,
                StandardApprovalRecord.approval_status == "pending",
                StandardApprovalRecord.is_deleted == False,
            )
            .order_by(StandardApprovalRecord.approval_level)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_approval_record(
        self, record_id: uuid.UUID, data: dict[str, Any]
    ) -> StandardApprovalRecord | None:
        """更新审批记录"""
        query = (
            update(StandardApprovalRecord)
            .where(
                StandardApprovalRecord.id == record_id,
                StandardApprovalRecord.is_deleted == False,
            )
            .values(**data)
            .returning(StandardApprovalRecord)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
