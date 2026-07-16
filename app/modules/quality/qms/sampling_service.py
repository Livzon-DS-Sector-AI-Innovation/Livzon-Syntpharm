"""Sampling management service"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.sampling_models import (
    SampleRetentionLedger,
    SamplingApprovalRecord,
    SamplingOrder,
    SamplingOrderItem,
)
from app.modules.quality.qms.sampling_repository import (
    SampleRetentionLedgerRepository,
    SamplingApprovalRecordRepository,
    SamplingOrderItemRepository,
    SamplingOrderRepository,
)
from app.modules.quality.qms.sampling_schemas import (
    ApprovalStatus,
    RetentionLedgerFilter,
    RetentionStatus,
    SampleStatus,
    SamplingApprovalCreate,
    SamplingOrderCreate,
    SamplingOrderFilter,
    SamplingOrderUpdate,
    SamplingResult,
    SamplingStatus,
)


class SamplingService:
    """取样管理服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = SamplingOrderRepository(session)
        self.item_repo = SamplingOrderItemRepository(session)
        self.retention_repo = SampleRetentionLedgerRepository(session)
        self.approval_repo = SamplingApprovalRecordRepository(session)

    async def create_order(self, data: SamplingOrderCreate, user_id: UUID | None = None) -> SamplingOrder:
        """创建取样单"""
        # 生成单号
        order_no = await self.order_repo.generate_order_no()

        # 创建主表
        order = SamplingOrder(
            order_no=order_no,
            source_type=data.source_type,
            source_no=data.source_no,
            material_code=data.material_code,
            material_name=data.material_name,
            material_category=data.material_category,
            batch_no=data.batch_no,
            specification=data.specification,
            unit=data.unit,
            quantity=data.quantity,
            sampling_source=data.sampling_source,
            sampling_quantity=data.sampling_quantity,
            sampling_location=data.sampling_location,
            sampling_date=data.sampling_date,
            sampler_id=data.sampler_id,
            sampler_name=data.sampler_name,
            sampling_result=data.sampling_result,
            exception_reasons=data.exception_reasons,
            remark=data.remark,
            status=SamplingStatus.DRAFT,
            created_by=user_id,
            updated_by=user_id,
        )
        self.session.add(order)
        await self.session.flush()

        # 创建明细
        for i, item_data in enumerate(data.items or [], 1):
            sample_no = await self.item_repo.generate_sample_no(order_no, i)
            item = SamplingOrderItem(
                sampling_order_id=order.id,
                item_no=item_data.item_no or i,
                sample_no=sample_no,
                sampling_count=item_data.sampling_count,
                retention_count=item_data.retention_count,
                retention_location=item_data.retention_location,
                sample_status=item_data.sample_status or SampleStatus.PENDING,
                retention_date=item_data.retention_date,
                expiry_date=item_data.expiry_date,
                remark=item_data.remark,
                created_by=user_id,
                updated_by=user_id,
            )
            self.session.add(item)

        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def update_order(
        self, order_id: UUID, data: SamplingOrderUpdate, user_id: UUID | None = None
    ) -> SamplingOrder:
        """更新取样单"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("取样单不存在")

        if order.status not in [SamplingStatus.DRAFT, SamplingStatus.REJECTED]:
            raise ValueError("当前状态不允许编辑")

        # 更新主表字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key != "items":
                setattr(order, key, value)

        # 更新明细
        if data.items is not None:
            # 删除旧的明细
            old_items = await self.item_repo.get_by_sampling_order_id(order_id)
            for item in old_items:
                item.is_deleted = True

            # 创建新明细
            for i, item_data in enumerate(data.items, 1):
                sample_no = await self.item_repo.generate_sample_no(order.order_no, i)
                item = SamplingOrderItem(
                    sampling_order_id=order.id,
                    item_no=item_data.item_no or i,
                    sample_no=sample_no,
                    sampling_count=item_data.sampling_count,
                    retention_count=item_data.retention_count,
                    retention_location=item_data.retention_location,
                    sample_status=item_data.sample_status or SampleStatus.PENDING,
                    retention_date=item_data.retention_date,
                    expiry_date=item_data.expiry_date,
                    remark=item_data.remark,
                    created_by=user_id,
                    updated_by=user_id,
                )
                self.session.add(item)

        order.updated_by = user_id
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def submit_for_approval(self, order_id: UUID, user_id: UUID | None = None) -> SamplingOrder:
        """提交审批"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("取样单不存在")

        if order.status != SamplingStatus.DRAFT:
            raise ValueError("只有草稿状态可以提交审批")

        # 检查是否异常
        if order.sampling_result == SamplingResult.ABNORMAL and order.exception_reasons:
            # 异常情况：自动生成偏差草稿（此处标记，后续偏差模块实现）
            # TODO: 调用偏差模块API创建偏差草稿
            pass

        # 更新状态为待仓储/生产审核
        order.status = SamplingStatus.PENDING_WAREHOUSE
        order.updated_by = user_id

        # 创建审批记录
        approval = SamplingApprovalRecord(
            sampling_order_id=order.id,
            approval_level=1,
            approval_status=ApprovalStatus.PENDING,
            approver_role="warehouse_production",
            created_by=user_id,
            updated_by=user_id,
        )
        self.session.add(approval)

        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def approve_order(
        self,
        order_id: UUID,
        data: SamplingApprovalCreate,
        approver_id: UUID,
        approver_name: str,
        approver_role: str,
    ) -> SamplingOrder:
        """审批取样单"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("取样单不存在")

        # 确定审批级别
        if order.status == SamplingStatus.PENDING_WAREHOUSE:
            approval_level = 1
            next_status = SamplingStatus.PENDING_QA
        elif order.status == SamplingStatus.PENDING_QA:
            approval_level = 2
            next_status = SamplingStatus.EFFECTIVE
        else:
            raise ValueError("当前状态不允许审批")

        # 更新审批记录
        approval = SamplingApprovalRecord(
            sampling_order_id=order.id,
            approval_level=approval_level,
            approval_status=data.approval_status,
            approver_role=approver_role,
            approver_id=approver_id,
            approver_name=approver_name,
            approved_at=order.updated_at,
            comments=data.comments,
            created_by=approver_id,
            updated_by=approver_id,
        )
        self.session.add(approval)

        if data.approval_status == ApprovalStatus.REJECTED:
            order.status = SamplingStatus.REJECTED
        else:
            order.status = next_status

            # 如果审批通过且是最终审批，则同步留样台账
            if order.status == SamplingStatus.EFFECTIVE:
                await self._sync_to_retention_ledger(order)

                # TODO: 推送QC生成检验任务

        order.updated_by = approver_id
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def _sync_to_retention_ledger(self, order: SamplingOrder) -> None:
        """同步到留样台账"""
        items = await self.item_repo.get_by_sampling_order_id(order.id)
        for item in items:
            if item.retention_count and item.retention_count > 0:
                ledger = SampleRetentionLedger(
                    sampling_item_id=item.id,
                    sampling_order_id=order.id,
                    order_no=order.order_no,
                    sample_no=item.sample_no,
                    material_code=order.material_code,
                    material_name=order.material_name,
                    batch_no=order.batch_no,
                    retention_count=item.retention_count,
                    retention_location=item.retention_location,
                    retention_date=item.retention_date,
                    expiry_date=item.expiry_date,
                    retention_status=RetentionStatus.RETAINED,
                    created_by=order.created_by,
                    updated_by=order.updated_by,
                )
                self.session.add(ledger)

                # 更新明细状态
                item.sample_status = SampleStatus.RETAINED

    async def get_order(self, order_id: UUID) -> SamplingOrder:
        """获取取样单详情"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("取样单不存在")
        return order

    async def get_order_list(
        self, filters: SamplingOrderFilter, skip: int = 0, limit: int = 20
    ) -> tuple[list[SamplingOrder], int]:
        """获取取样单列表"""
        return await self.order_repo.get_list(filters, skip, limit)

    async def delete_order(self, order_id: UUID, user_id: UUID | None = None) -> bool:
        """删除取样单（软删除）"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("取样单不存在")

        if order.status not in [SamplingStatus.DRAFT, SamplingStatus.REJECTED]:
            raise ValueError("只有草稿或驳回状态可以删除")

        order.is_deleted = True
        order.updated_by = user_id
        await self.session.commit()
        return True

    async def get_retention_ledger(
        self, filters: RetentionLedgerFilter, skip: int = 0, limit: int = 20
    ) -> tuple[list[SampleRetentionLedger], int]:
        """获取留样台账列表"""
        return await self.retention_repo.get_list(filters, skip, limit)

    async def get_retention_by_order_id(self, order_id: UUID) -> list[SampleRetentionLedger]:
        """根据取样单ID获取留样记录"""
        return await self.retention_repo.get_by_sampling_order_id(order_id)

    async def get_approval_records(self, order_id: UUID) -> list[SamplingApprovalRecord]:
        """获取审批记录"""
        return await self.approval_repo.get_by_sampling_order_id(order_id)
