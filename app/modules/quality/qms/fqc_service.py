"""FQC (Finished Product Quality Control) inspection service"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.fqc_models import (
    FQCApprovalRecord,
    FQCInspection,
)
from app.modules.quality.qms.fqc_repository import (
    FQCApprovalRecordRepository,
    FQCInspectionItemRepository,
    FQCInspectionRepository,
)
from app.modules.quality.qms.fqc_schemas import (
    FQCApprovalCreate,
    FQCInspectionCreate,
    FQCInspectionFilter,
    FQCInspectionUpdate,
)


class FQCInspectionService:
    """FQC检验服务 - 成品检验"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FQCInspectionRepository(session)
        self.item_repo = FQCInspectionItemRepository(session)
        self.approval_repo = FQCApprovalRecordRepository(session)

    async def get_inspection(self, inspection_id: UUID) -> FQCInspection:
        """获取FQC检验单"""
        inspection = await self.repo.get_by_id(inspection_id)
        if not inspection:
            raise ValueError("FQC检验单不存在")
        return inspection

    async def get_inspection_list(
        self,
        filters: FQCInspectionFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[FQCInspection], int]:
        """获取FQC检验单列表"""
        return await self.repo.get_list(filters, skip, limit)

    async def create_inspection(
        self,
        data: FQCInspectionCreate,
        user_id: UUID | None = None,
    ) -> FQCInspection:
        """创建FQC检验单"""
        # 生成单号
        inspection_no = await self.repo.generate_inspection_no()

        # 创建主表记录
        inspection = FQCInspection(
            inspection_no=inspection_no,
            batch_record_id=data.batch_record_id,
            batch_record_no=data.batch_record_no,
            batch_no=data.batch_no,
            product_code=data.product_code,
            product_name=data.product_name,
            sampling_order_id=data.sampling_order_id,
            sampling_order_no=data.sampling_order_no,
            batch_quantity=data.batch_quantity,
            production_workshop=data.production_workshop,
            cas_no=data.cas_no,
            manufacturing_date=data.manufacturing_date,
            expiry_date=data.expiry_date,
            manufacturer=data.manufacturer,
            specification=data.specification,
            inspection_date=data.inspection_date,
            inspector_id=data.inspector_id,
            inspector_name=data.inspector_name,
            standard_id=data.standard_id,
            standard_name=data.standard_name,
            standard_version=data.standard_version,
            inspection_conclusion=data.inspection_conclusion.value
            if data.inspection_conclusion
            else None,
            conclusion_reason=data.conclusion_reason,
            remark=data.remark,
            oos_report_no=data.oos_report_no,
            reinspection_applied=data.reinspection_applied,
            reinspection_reason=data.reinspection_reason,
            attachments=data.attachments,
            created_by=user_id,
        )
        self.session.add(inspection)
        await self.session.flush()

        # 创建明细记录
        if data.items:
            items_data = [
                {
                    "item_no": item.item_no,
                    "inspection_category": item.inspection_category.value
                    if item.inspection_category
                    else None,
                    "inspection_item": item.inspection_item,
                    "inspection_method": item.inspection_method,
                    "standard_value": item.standard_value,
                    "unit": item.unit,
                    "measured_value": item.measured_value,
                    "result": item.result.value if item.result else None,
                    "is_oos": item.is_oos,
                    "oos_description": item.oos_description,
                    "is_repeat_test": item.is_repeat_test,
                    "repeat_times": item.repeat_times,
                    "chromatogram_urls": item.chromatogram_urls,
                    "raw_record_url": item.raw_record_url,
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
        data: FQCInspectionUpdate,
        user_id: UUID | None = None,
    ) -> FQCInspection:
        """更新FQC检验单"""
        inspection = await self.get_inspection(inspection_id)

        # 草稿或驳回状态才能编辑
        if inspection.status not in ["draft", "rejected"]:
            raise ValueError("只有草稿或驳回状态的检验单可以编辑")

        # 更新主表字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "items":
                continue
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
                    "inspection_category": item.inspection_category.value
                    if item.inspection_category
                    else None,
                    "inspection_item": item.inspection_item,
                    "inspection_method": item.inspection_method,
                    "standard_value": item.standard_value,
                    "unit": item.unit,
                    "measured_value": item.measured_value,
                    "result": item.result.value if item.result else None,
                    "is_oos": item.is_oos,
                    "oos_description": item.oos_description,
                    "is_repeat_test": item.is_repeat_test,
                    "repeat_times": item.repeat_times,
                    "chromatogram_urls": item.chromatogram_urls,
                    "raw_record_url": item.raw_record_url,
                    "remark": item.remark,
                }
                for item in data.items
            ]
            await self.item_repo.create_bulk(inspection_id, items_data, user_id)

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def delete_inspection(
        self, inspection_id: UUID, user_id: UUID | None = None
    ) -> None:
        """删除FQC检验单"""
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

    async def submit_for_approval(
        self, inspection_id: UUID, user_id: UUID | None = None
    ) -> FQCInspection:
        """提交FQC检验单审批"""
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

        # 检查是否有超标项目
        has_oos = any(item.is_oos for item in items)
        if has_oos and not inspection.oos_report_no:
            raise ValueError("存在超标项目，请先填写OOS报告编号")

        # 更新状态为已提交
        inspection.status = "submitted"
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()

        # 创建第一级审批记录（QC主管）
        await self.approval_repo.create_approval_record(
            inspection_id=inspection_id,
            approval_level=1,
            approval_status="pending",
            approver_role="qc_supervisor",
            created_by=user_id,
        )

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def approve_inspection(
        self,
        inspection_id: UUID,
        data: FQCApprovalCreate,
        user_id: UUID | None,
        user_name: str,
        approver_role: str,
    ) -> FQCInspection:
        """审批FQC检验单 - 4级审批流程"""
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
                # QC主管审核通过，进入QA审核
                inspection.status = "qc_supervisor_approved"
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
                # 生成检验报告书编号
                inspection.report_no = await self.repo.generate_report_no()
                # 如果检验结论为合格，更新放行状态
                if inspection.inspection_conclusion == "qualified":
                    inspection.release_status = "pending_release"
                # 如果检验结论为不合格，锁定批次
                elif inspection.inspection_conclusion == "unqualified":
                    inspection.batch_locked = True
                    inspection.batch_lock_reason = (
                        f"FQC检验不合格，检验单号: {inspection.inspection_no}"
                    )
                    inspection.warehouse_isolation = True

            inspection.updated_by = user_id
            inspection.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def get_approval_records(
        self, inspection_id: UUID
    ) -> list[FQCApprovalRecord]:
        """获取审批记录"""
        return await self.approval_repo.get_by_inspection_id(inspection_id)

    async def apply_reinspection(
        self,
        inspection_id: UUID,
        reason: str,
        user_id: UUID | None = None,
    ) -> FQCInspection:
        """申请复检"""
        inspection = await self.get_inspection(inspection_id)

        if inspection.status not in ["final_approved", "locked"]:
            raise ValueError("只能对已审核或已锁定的检验单申请复检")

        if inspection.inspection_conclusion != "unqualified":
            raise ValueError("只能对不合格的检验单申请复检")

        inspection.reinspection_applied = True
        inspection.reinspection_reason = reason
        inspection.status = "draft"  # 回到草稿状态重新检验
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def release_inspection(
        self,
        inspection_id: UUID,
        release_reason: str | None = None,
        user_id: UUID | None = None,
    ) -> FQCInspection:
        """放行成品"""
        inspection = await self.get_inspection(inspection_id)

        if inspection.status != "final_approved":
            raise ValueError("只能对终审通过的检验单进行放行")

        if inspection.inspection_conclusion != "qualified":
            raise ValueError("只能对合格的成品进行放行")

        if inspection.batch_locked:
            raise ValueError("批次已锁定，无法放行")

        inspection.status = "released"
        inspection.release_status = "released"
        inspection.release_reason = release_reason
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def lock_batch(
        self,
        inspection_id: UUID,
        reason: str,
        user_id: UUID | None = None,
    ) -> FQCInspection:
        """锁定批次"""
        inspection = await self.get_inspection(inspection_id)
        inspection.batch_locked = True
        inspection.batch_lock_reason = reason
        inspection.status = "locked"
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def unlock_batch(
        self,
        inspection_id: UUID,
        user_id: UUID | None = None,
    ) -> FQCInspection:
        """解锁批次"""
        inspection = await self.get_inspection(inspection_id)
        inspection.batch_locked = False
        inspection.batch_lock_reason = None
        inspection.warehouse_isolation = False
        if inspection.inspection_conclusion == "qualified":
            inspection.release_status = "pending_release"
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection
