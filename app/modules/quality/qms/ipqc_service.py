"""IPQC (In-Process Quality Control) inspection service"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.ipqc_models import (
    IPQCApprovalRecord,
    IPQCInspection,
)
from app.modules.quality.qms.ipqc_repository import (
    IPQCApprovalRecordRepository,
    IPQCInspectionItemRepository,
    IPQCInspectionRepository,
)
from app.modules.quality.qms.ipqc_schemas import (
    IPQCApprovalCreate,
    IPQCInspectionCreate,
    IPQCInspectionFilter,
    IPQCInspectionUpdate,
)


class IPQCInspectionService:
    """IPQC检验服务 - 过程检验/中间体检验"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IPQCInspectionRepository(session)
        self.item_repo = IPQCInspectionItemRepository(session)
        self.approval_repo = IPQCApprovalRecordRepository(session)

    async def get_inspection(self, inspection_id: UUID) -> IPQCInspection:
        """获取IPQC检验单"""
        inspection = await self.repo.get_by_id(inspection_id)
        if not inspection:
            raise ValueError("IPQC检验单不存在")
        return inspection

    async def get_inspection_list(
        self,
        filters: IPQCInspectionFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[IPQCInspection], int]:
        """获取IPQC检验单列表"""
        return await self.repo.get_list(filters, skip, limit)

    async def create_inspection(
        self,
        data: IPQCInspectionCreate,
        user_id: UUID | None = None,
    ) -> IPQCInspection:
        """创建IPQC检验单"""
        # 生成单号
        inspection_no = await self.repo.generate_inspection_no()

        # 创建主表记录
        inspection = IPQCInspection(
            inspection_no=inspection_no,
            batch_record_id=data.batch_record_id,
            batch_record_no=data.batch_record_no,
            batch_no=data.batch_no,
            product_code=data.product_code,
            product_name=data.product_name,
            product_specification=data.product_specification,
            process_stage=data.process_stage,
            sampling_point=data.sampling_point,
            sampling_no=data.sampling_no,
            sampling_time=data.sampling_time,
            sampling_quantity=data.sampling_quantity,
            sampling_unit=data.sampling_unit,
            sampling_location=data.sampling_location,
            production_date=data.production_date,
            inspection_date=data.inspection_date,
            inspector_id=data.inspector_id,
            inspector_name=data.inspector_name,
            standard_id=data.standard_id,
            standard_name=data.standard_name,
            standard_version=data.standard_version,
            inspection_conclusion=data.inspection_conclusion.value if data.inspection_conclusion else None,
            conclusion_reason=data.conclusion_reason,
            remark=data.remark,
            oos_report_no=data.oos_report_no,
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
                    "upper_limit": item.upper_limit,
                    "lower_limit": item.lower_limit,
                    "unit": item.unit,
                    "measured_value": item.measured_value,
                    "result": item.result.value if item.result else None,
                    "is_repeat_test": item.is_repeat_test,
                    "repeat_times": item.repeat_times,
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
        data: IPQCInspectionUpdate,
        user_id: UUID | None = None,
    ) -> IPQCInspection:
        """更新IPQC检验单"""
        inspection = await self.get_inspection(inspection_id)

        # 草稿状态才能编辑
        if inspection.status != "draft":
            raise ValueError("只有草稿状态的检验单可以编辑")

        # 更新主表字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "items":
                continue  # 明细单独处理
            # inspection_conclusion 从枚举转为字符串后直接使用
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
                    "upper_limit": item.upper_limit,
                    "lower_limit": item.lower_limit,
                    "unit": item.unit,
                    "measured_value": item.measured_value,
                    "result": item.result.value if item.result else None,
                    "is_repeat_test": item.is_repeat_test,
                    "repeat_times": item.repeat_times,
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
        """删除IPQC检验单"""
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

    async def submit_for_approval(self, inspection_id: UUID, user_id: UUID | None = None) -> IPQCInspection:
        """提交IPQC检验单审批"""
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

        # 创建第一级审批记录（车间工艺负责人）
        await self.approval_repo.create_approval_record(
            inspection_id=inspection_id,
            approval_level=1,
            approval_status="pending",
            approver_role="workshop_head",
            created_by=user_id,
        )

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def approve_inspection(
        self,
        inspection_id: UUID,
        data: IPQCApprovalCreate,
        user_id: UUID | None,
        user_name: str,
        approver_role: str,
    ) -> IPQCInspection:
        """审批IPQC检验单 - 4级审批流程"""
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
                # 车间工艺负责人审核通过，进入QC主管复核
                inspection.status = "workshop_approved"
                await self.approval_repo.create_approval_record(
                    inspection_id=inspection_id,
                    approval_level=2,
                    approval_status="pending",
                    approver_role="qc_supervisor",
                    created_by=user_id,
                )
            elif pending_record.approval_level == 2:
                # QC主管复核通过，进入QA终审
                inspection.status = "qc_supervisor_approved"
                await self.approval_repo.create_approval_record(
                    inspection_id=inspection_id,
                    approval_level=3,
                    approval_status="pending",
                    approver_role="qa",
                    created_by=user_id,
                )
            elif pending_record.approval_level == 3:
                # QA终审通过 - 完成审批流程
                inspection.status = "qa_final_approved"

                # 如果检验结论为不合格，需要锁定批次
                if inspection.inspection_conclusion == "unqualified":
                    inspection.batch_locked = True
                    inspection.batch_lock_reason = f"IPQC检验不合格，检验单号: {inspection.inspection_no}"

            inspection.updated_by = user_id
            inspection.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def get_approval_records(self, inspection_id: UUID) -> list[IPQCApprovalRecord]:
        """获取审批记录"""
        return await self.approval_repo.get_by_inspection_id(inspection_id)

    async def lock_batch(
        self,
        inspection_id: UUID,
        reason: str,
        user_id: UUID | None = None,
    ) -> IPQCInspection:
        """锁定批次"""
        inspection = await self.get_inspection(inspection_id)
        inspection.batch_locked = True
        inspection.batch_lock_reason = reason
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def unlock_batch(
        self,
        inspection_id: UUID,
        user_id: UUID | None = None,
    ) -> IPQCInspection:
        """解锁批次"""
        inspection = await self.get_inspection(inspection_id)
        inspection.batch_locked = False
        inspection.batch_lock_reason = None
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection
