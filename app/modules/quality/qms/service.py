"""Quality business workflows live here."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.models import StandardStatus
from app.modules.quality.qms.repository import QualityRepository
from app.modules.quality.qms.schemas import (
    InspectionStandardCopy,
    InspectionStandardCreate,
    InspectionStandardUpdate,
    ObsoleteSubmit,
)


class QualityService:
    """Quality module service"""

    # 审批流程配置
    APPROVAL_FLOW = [
        {"level": 1, "role": "技术部门", "next_status": "qa_review"},
        {"level": 2, "role": "QA部门", "next_status": "approved"},
        {"level": 3, "role": "质量负责人", "next_status": "effective"},
    ]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = QualityRepository(session)

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
    ) -> tuple[list, int]:
        """获取检验标准列表"""
        return await self.repo.get_standards(
            skip=skip,
            limit=limit,
            status=status,
            material_code=material_code,
            material_name=material_name,
            material_category=material_category,
            pharmacopeia=pharmacopeia,
            version=version,
            is_effective=is_effective,
        )

    async def get_standard(self, standard_id: uuid.UUID) -> Any | None:
        """获取检验标准详情"""
        return await self.repo.get_standard_by_id(standard_id)

    async def get_effective_standards(
        self, material_code: str | None = None, material_category: str | None = None
    ) -> list:
        """获取已生效的标准列表(用于检验任务选择)"""
        standards, _ = await self.repo.get_standards(
            skip=0,
            limit=100,
            status="effective",
            material_code=material_code,
            material_category=material_category,
        )
        return standards

    async def create_standard(self, data: InspectionStandardCreate) -> Any:
        """创建检验标准"""
        # 生成标准编号
        standard_no = await self._generate_standard_no(data.material_code, data.version)

        # 构建主表数据
        standard_data = {
            "standard_no": standard_no,
            "material_code": data.material_code,
            "material_name": data.material_name,
            "cas_no": data.cas_no,
            "material_category": data.material_category.value,
            "pharmacopeia": data.pharmacopeia.value if data.pharmacopeia else None,
            "version": data.version,
            "status": StandardStatus.DRAFT.value,
            "effective_date": data.effective_date,
            "obsolete_date": data.obsolete_date,
            "sop_no": data.sop_no,
            "attachment_urls": data.attachment_urls,
            "notes": data.notes,
        }

        # 创建主表记录
        standard = await self.repo.create_standard(standard_data)

        # 创建检验项目明细
        if data.items:
            items_data = []
            for item in data.items:
                items_data.append(
                    {
                        "item_no": item.item_no,
                        "item_name": item.item_name,
                        "test_method": item.test_method,
                        "instrument_code": item.instrument_code,
                        "reference_materials": item.reference_materials,
                        "limit_type": item.limit_type.value,
                        "limit_value": item.limit_value,
                        "item_category": item.item_category.value
                        if item.item_category
                        else None,
                        "is_critical": item.is_critical,
                        "notes": item.notes,
                    }
                )
            await self.repo.create_items_bulk(standard.id, items_data)

        # 重新获取完整数据
        return await self.repo.get_standard_by_id(standard.id)

    async def update_standard(
        self, standard_id: uuid.UUID, data: InspectionStandardUpdate
    ) -> Any | None:
        """更新检验标准"""
        # 检查标准状态，只有草稿和驳回状态可以编辑
        standard = await self.repo.get_standard_by_id(standard_id)
        if not standard:
            return None

        if standard.status not in [
            StandardStatus.DRAFT.value,
            StandardStatus.REJECTED.value,
        ]:
            raise ValueError("只有草稿或驳回状态的标准才能编辑")

        # 构建更新数据
        update_data = {}
        if data.material_code is not None:
            update_data["material_code"] = data.material_code
        if data.material_name is not None:
            update_data["material_name"] = data.material_name
        if data.cas_no is not None:
            update_data["cas_no"] = data.cas_no
        if data.material_category is not None:
            update_data["material_category"] = data.material_category.value
        if data.pharmacopeia is not None:
            update_data["pharmacopeia"] = data.pharmacopeia.value
        if data.version is not None:
            update_data["version"] = data.version
        if data.effective_date is not None:
            update_data["effective_date"] = data.effective_date
        if data.obsolete_date is not None:
            update_data["obsolete_date"] = data.obsolete_date
        if data.sop_no is not None:
            update_data["sop_no"] = data.sop_no
        if data.attachment_urls is not None:
            update_data["attachment_urls"] = data.attachment_urls
        if data.notes is not None:
            update_data["notes"] = data.notes

        # 更新主表
        await self.repo.update_standard(standard_id, update_data)

        # 更新检验项目
        if data.items is not None:
            items_data = []
            for item in data.items:
                items_data.append(
                    {
                        "item_no": item.item_no,
                        "item_name": item.item_name,
                        "test_method": item.test_method,
                        "instrument_code": item.instrument_code,
                        "reference_materials": item.reference_materials,
                        "limit_type": item.limit_type.value,
                        "limit_value": item.limit_value,
                        "item_category": item.item_category.value
                        if item.item_category
                        else None,
                        "is_critical": item.is_critical,
                        "notes": item.notes,
                    }
                )
            await self.repo.update_standard_items(standard_id, items_data)

        return await self.repo.get_standard_by_id(standard_id)

    async def delete_standard(self, standard_id: uuid.UUID) -> bool:
        """删除检验标准"""
        standard = await self.repo.get_standard_by_id(standard_id)
        if not standard:
            return False

        # 只有草稿状态可以删除
        if standard.status != StandardStatus.DRAFT.value:
            raise ValueError("只有草稿状态的标准才能删除")

        return await self.repo.delete_standard(standard_id)

    async def submit_for_approval(self, standard_id: uuid.UUID) -> Any | None:
        """提交审批"""
        standard = await self.repo.get_standard_by_id(standard_id)
        if not standard:
            return None

        if standard.status != StandardStatus.DRAFT.value:
            raise ValueError("只有草稿状态的标准才能提交审批")

        # 创建审批记录
        for step in self.APPROVAL_FLOW:
            await self.repo.create_approval_record(
                {
                    "standard_id": standard_id,
                    "approval_level": step["level"],
                    "approval_status": "pending",
                    "approver_role": step["role"],
                }
            )

        return await self.repo.submit_for_approval(standard_id)

    async def approve_standard(
        self, standard_id: uuid.UUID, approver_id: uuid.UUID, approver_name: str
    ) -> Any | None:
        """审批标准"""
        standard = await self.repo.get_standard_by_id(standard_id)
        if not standard:
            return None

        # 获取当前应审批的层级
        current_level = self._get_current_approval_level(standard)
        if current_level is None:
            raise ValueError("该标准不在待审批状态")

        # 更新当前审批记录
        pending_records = await self.repo.get_pending_approvers(standard_id)
        if pending_records:
            current_record = pending_records[0]
            await self.repo.update_approval_record(
                current_record.id,
                {
                    "approval_status": "approved",
                    "approver_id": approver_id,
                    "approver_name": approver_name,
                    "approved_at": datetime.now(),
                },
            )

        # 获取下一状态
        next_status = self._get_next_status(current_level)
        if next_status:
            return await self.repo.approve_standard(standard_id, next_status)

        # 最终状态，设置生效日期
        standard = await self.repo.approve_standard(standard_id, "effective")
        if standard:
            await self.repo.update_standard(
                standard_id, {"effective_date": datetime.now()}
            )
        return await self.repo.get_standard_by_id(standard_id)

    async def reject_standard(
        self, standard_id: uuid.UUID, approver_id: uuid.UUID, comments: str
    ) -> Any | None:
        """驳回标准"""
        standard = await self.repo.get_standard_by_id(standard_id)
        if not standard:
            return None

        current_level = self._get_current_approval_level(standard)
        if current_level is None:
            raise ValueError("该标准不在待审批状态")

        # 更新当前审批记录
        pending_records = await self.repo.get_pending_approvers(standard_id)
        if pending_records:
            current_record = pending_records[0]
            await self.repo.update_approval_record(
                current_record.id,
                {
                    "approval_status": "rejected",
                    "approver_id": approver_id,
                    "approved_at": datetime.now(),
                    "comments": comments,
                },
            )

        return await self.repo.reject_standard(standard_id, comments)

    async def obsolete_standard(
        self, standard_id: uuid.UUID, data: ObsoleteSubmit
    ) -> Any | None:
        """作废标准"""
        standard = await self.repo.get_standard_by_id(standard_id)
        if not standard:
            return None

        if standard.status not in [
            StandardStatus.EFFECTIVE.value,
            StandardStatus.APPROVED.value,
        ]:
            raise ValueError("只有已生效或已批准的标准才能作废")

        return await self.repo.obsolete_standard(standard_id, data.obsolete_reason)

    async def copy_standard(self, data: InspectionStandardCopy) -> Any | None:
        """复制标准(基于旧版快速新建新标准)"""
        source = await self.repo.get_standard_by_id(data.source_id)
        if not source:
            return None

        # 生成新的标准编号
        standard_no = await self._generate_standard_no(
            source.material_code, data.new_version
        )

        # 复制主表数据
        new_data = {
            "standard_no": standard_no,
            "material_code": source.material_code,
            "material_name": source.material_name,
            "cas_no": source.cas_no,
            "material_category": source.material_category,
            "pharmacopeia": source.pharmacopeia,
            "version": data.new_version,
            "status": StandardStatus.DRAFT.value,
            "effective_date": None,
            "obsolete_date": None,
            "sop_no": source.sop_no,
            "attachment_urls": source.attachment_urls,
            "notes": source.notes,
            "source_version": source.version,
        }

        new_standard = await self.repo.create_standard(new_data)

        # 复制检验项目
        if source.items:
            items_data = []
            for item in source.items:
                items_data.append(
                    {
                        "item_no": item.item_no,
                        "item_name": item.item_name,
                        "test_method": item.test_method,
                        "instrument_code": item.instrument_code,
                        "reference_materials": item.reference_materials,
                        "limit_type": item.limit_type,
                        "limit_value": item.limit_value,
                        "item_category": item.item_category,
                        "is_critical": item.is_critical,
                        "notes": item.notes,
                    }
                )
            await self.repo.create_items_bulk(new_standard.id, items_data)

        return await self.repo.get_standard_by_id(new_standard.id)

    # ============ Helper Methods ============

    async def _generate_standard_no(self, material_code: str, version: str) -> str:
        """生成标准编号"""
        # 格式: STD-物料编码-版本号
        return f"STD-{material_code}-{version}"

    def _get_current_approval_level(self, standard) -> int | None:
        """获取当前待审批层级"""
        status_map = {
            "tech_review": 1,
            "qa_review": 2,
            "approved": 3,
        }
        return status_map.get(standard.status)

    def _get_next_status(self, current_level: int) -> str | None:
        """获取下一审批状态"""
        status_map = {
            1: "qa_review",
            2: "approved",
        }
        return status_map.get(current_level)
