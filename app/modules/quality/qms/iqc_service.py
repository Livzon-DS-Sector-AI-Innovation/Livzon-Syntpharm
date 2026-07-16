"""IQC (Incoming Quality Control) inspection service"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.iqc_models import (
    IQCApprovalRecord,
    IQCInspection,
)
from app.modules.quality.qms.iqc_repository import (
    IQCApprovalRecordRepository,
    IQCInspectionItemRepository,
    IQCInspectionRepository,
)
from app.modules.quality.qms.iqc_schemas import (
    IQCApprovalCreate,
    IQCInspectionCreate,
    IQCInspectionFilter,
    IQCInspectionUpdate,
)


class IQCInspectionService:
    """IQC检验服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IQCInspectionRepository(session)
        self.item_repo = IQCInspectionItemRepository(session)
        self.approval_repo = IQCApprovalRecordRepository(session)

    async def get_inspection(self, inspection_id: UUID) -> IQCInspection:
        """获取IQC检验单"""
        inspection = await self.repo.get_by_id(inspection_id)
        if not inspection:
            raise ValueError("IQC检验单不存在")
        return inspection

    async def get_inspection_list(
        self,
        filters: IQCInspectionFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[IQCInspection], int]:
        """获取IQC检验单列表"""
        return await self.repo.get_list(filters, skip, limit)

    async def create_inspection(
        self,
        data: IQCInspectionCreate,
        user_id: UUID | None = None,
    ) -> IQCInspection:
        """创建IQC检验单"""
        # 生成单号
        inspection_no = await self.repo.generate_inspection_no()

        # 创建主表记录
        inspection = IQCInspection(
            inspection_no=inspection_no,
            source_type=data.source_type.value,
            source_no=data.source_no,
            sampling_order_id=data.sampling_order_id,
            sampling_order_no=data.sampling_order_no,
            material_code=data.material_code,
            material_name=data.material_name,
            material_category=data.material_category.value if data.material_category else None,
            specification=data.specification,
            batch_no=data.batch_no,
            supplier_code=data.supplier_code,
            supplier_name=data.supplier_name,
            manufacturing_date=data.manufacturing_date,
            expiry_date=data.expiry_date,
            quantity_received=data.quantity_received,
            unit=data.unit,
            inspection_date=data.inspection_date,
            inspector_id=data.inspector_id,
            inspector_name=data.inspector_name,
            standard_id=data.standard_id,
            standard_name=data.standard_name,
            standard_version=data.standard_version,
            inspection_conclusion=data.inspection_conclusion.value if data.inspection_conclusion else None,
            remark=data.remark,
            created_by=user_id,
        )
        self.session.add(inspection)
        await self.session.flush()

        # 创建明细记录
        if data.items:
            items_data = [
                {
                    "item_no": item.item_no,
                    "inspection_item": item.inspection_item,
                    "inspection_method": item.inspection_method,
                    "standard_value": item.standard_value,
                    "unit": item.unit,
                    "measured_value": item.measured_value,
                    "result": item.result.value if item.result else None,
                    "is_repeat_test": item.is_repeat_test,
                    "raw_data": item.raw_data,
                    "remark": item.remark,
                }
                for item in data.items
            ]
            await self.item_repo.create_bulk(inspection.id, items_data, user_id)

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def update_inspection(
        self,
        inspection_id: UUID,
        data: IQCInspectionUpdate,
        user_id: UUID | None = None,
    ) -> IQCInspection:
        """更新IQC检验单"""
        inspection = await self.get_inspection(inspection_id)

        # 草稿状态才能编辑
        if inspection.status != "draft":
            raise ValueError("只有草稿状态的检验单可以编辑")

        # 更新主表字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "items":
                continue  # 明细单独处理
            if key == "material_category" and value:
                value = value.value
            if key == "inspection_conclusion" and value:
                value = value.value
            if hasattr(inspection, key):
                setattr(inspection, key, value)

        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()

        # 更新明细
        if data.items is not None:
            # 删除旧的明细
            old_items = await self.item_repo.get_by_inspection_id(inspection_id)
            for item in old_items:
                item.is_deleted = True

            # 创建新的明细
            items_data = [
                {
                    "item_no": item.item_no,
                    "inspection_item": item.inspection_item,
                    "inspection_method": item.inspection_method,
                    "standard_value": item.standard_value,
                    "unit": item.unit,
                    "measured_value": item.measured_value,
                    "result": item.result.value if item.result else None,
                    "is_repeat_test": item.is_repeat_test,
                    "raw_data": item.raw_data,
                    "remark": item.remark,
                }
                for item in data.items
            ]
            await self.item_repo.create_bulk(inspection_id, items_data, user_id)

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def delete_inspection(self, inspection_id: UUID, user_id: UUID | None = None) -> None:
        """删除IQC检验单"""
        inspection = await self.get_inspection(inspection_id)

        # 草稿状态才能删除
        if inspection.status != "draft":
            raise ValueError("只有草稿状态的检验单可以删除")

        inspection.is_deleted = True
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()

        # 软删除明细
        items = await self.item_repo.get_by_inspection_id(inspection_id)
        for item in items:
            item.is_deleted = True

        await self.session.commit()

    async def submit_for_approval(self, inspection_id: UUID, user_id: UUID | None = None) -> IQCInspection:
        """提交IQC检验单审批"""
        inspection = await self.get_inspection(inspection_id)

        # 只有草稿状态才能提交
        if inspection.status != "draft":
            raise ValueError("只有草稿状态的检验单可以提交")

        # 检查是否至少有一条明细
        items = await self.item_repo.get_by_inspection_id(inspection_id)
        if not items:
            raise ValueError("请先添加检验明细")

        # 检查是否已填写检验结论
        if not inspection.inspection_conclusion:
            raise ValueError("请先填写检验结论")

        # 更新状态为已提交
        inspection.status = "submitted"
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()

        # 创建第一级审批记录（部门负责人）
        await self.approval_repo.create_approval_record(
            inspection_id=inspection_id,
            approval_level=1,
            approval_status="pending",
            approver_role="department_head",
            created_by=user_id,
        )

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def approve_inspection(
        self,
        inspection_id: UUID,
        data: IQCApprovalCreate,
        user_id: UUID | None,
        user_name: str,
        approver_role: str,
    ) -> IQCInspection:
        """审批IQC检验单"""
        inspection = await self.get_inspection(inspection_id)

        # 获取当前待审批的记录
        approval_records = await self.approval_repo.get_by_inspection_id(inspection_id)
        pending_record = None
        for record in approval_records:
            if record.approval_status == "pending":
                pending_record = record
                break

        if not pending_record:
            raise ValueError("没有待审批的记录")

        # 更新审批记录
        pending_record.approval_status = data.approval_status.value
        pending_record.approver_id = user_id
        pending_record.approver_name = user_name
        pending_record.approved_at = datetime.now()
        pending_record.comments = data.comments
        pending_record.updated_by = user_id
        pending_record.updated_at = datetime.now()

        if data.approval_status.value == "rejected":
            # 驳回
            inspection.status = "rejected"
            inspection.updated_by = user_id
            inspection.updated_at = datetime.now()
        else:
            # 通过，更新状态到下一级
            if pending_record.approval_level == 1:
                # 部门负责人审核通过，进入QA审核
                inspection.status = "department_approved"
                await self.approval_repo.create_approval_record(
                    inspection_id=inspection_id,
                    approval_level=2,
                    approval_status="pending",
                    approver_role="qa",
                    created_by=user_id,
                )
            elif pending_record.approval_level == 2:
                # QA审核通过，进入质量负责人终审
                inspection.status = "qa_approved"
                await self.approval_repo.create_approval_record(
                    inspection_id=inspection_id,
                    approval_level=3,
                    approval_status="pending",
                    approver_role="quality_head",
                    created_by=user_id,
                )
            elif pending_record.approval_level == 3:
                # 质量负责人终审通过
                inspection.status = "final_approved"

            inspection.updated_by = user_id
            inspection.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def get_approval_records(self, inspection_id: UUID) -> list[IQCApprovalRecord]:
        """获取审批记录"""
        return await self.approval_repo.get_by_inspection_id(inspection_id)
