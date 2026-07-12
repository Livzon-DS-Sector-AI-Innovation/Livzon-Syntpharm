"""Stability Study (稳定性试验) service"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.stability_models import (
    StabilityInspection,
    StabilitySampleNode,
    StabilityStudy,
)
from app.modules.quality.qms.stability_repository import (
    StabilityApprovalRecordRepository,
    StabilityInspectionItemRepository,
    StabilityInspectionRepository,
    StabilitySampleNodeRepository,
    StabilityStudyRepository,
)
from app.modules.quality.qms.stability_schemas import (
    StabilityApprovalCreate,
    StabilityInspectionCreate,
    StabilityInspectionUpdate,
    StabilitySampleNodeUpdate,
    StabilityStudyCreate,
    StabilityStudyFilter,
    StabilityStudyUpdate,
)


class StabilityStudyService:
    """稳定性试验服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.study_repo = StabilityStudyRepository(session)
        self.node_repo = StabilitySampleNodeRepository(session)
        self.inspection_repo = StabilityInspectionRepository(session)
        self.item_repo = StabilityInspectionItemRepository(session)
        self.approval_repo = StabilityApprovalRecordRepository(session)

    # ========== Stability Study ==========

    async def get_study(self, study_id: UUID) -> StabilityStudy:
        """获取稳定性试验"""
        study = await self.study_repo.get_by_id(study_id)
        if not study:
            raise ValueError("稳定性试验不存在")
        return study

    async def get_study_list(
        self,
        filters: StabilityStudyFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StabilityStudy], int]:
        """获取稳定性试验列表"""
        return await self.study_repo.get_list(filters, skip, limit)

    async def create_study(
        self,
        data: StabilityStudyCreate,
        user_id: UUID | None = None,
    ) -> StabilityStudy:
        """创建稳定性试验"""
        # 生成方案编号
        study_no = await self.study_repo.generate_study_no()

        # 创建主表记录
        study = StabilityStudy(
            study_no=study_no,
            product_code=data.product_code,
            product_name=data.product_name,
            product_category=data.product_category,
            batch_no=data.batch_no,
            batch_quantity=data.batch_quantity,
            packaging_spec=data.packaging_spec,
            study_type=data.study_type.value,
            temperature=data.temperature,
            humidity=data.humidity,
            start_date=data.start_date,
            end_date=data.end_date,
            expiry_date=data.expiry_date,
            sample_intervals=",".join(map(str, data.sample_intervals)) if data.sample_intervals else None,
            standard_id=data.standard_id,
            standard_name=data.standard_name,
            standard_version=data.standard_version,
            developer_id=data.developer_id,
            developer_name=data.developer_name,
            remark=data.remark,
            attachments=data.attachments,
            created_by=user_id,
        )
        self.session.add(study)
        await self.session.flush()

        # 创建取样节点
        intervals = data.sample_intervals if isinstance(data.sample_intervals, list) else []
        if data.sample_nodes:
            nodes_data = [
                {
                    "node_no": node.node_no,
                    "node_month": node.node_month,
                    "node_name": node.node_name or f"{node.node_month}月",
                    "planned_date": node.planned_date,
                }
                for node in data.sample_nodes
            ]
            await self.node_repo.create_bulk(study.id, nodes_data, user_id)
        elif intervals and data.start_date:
            # 从 sample_intervals 自动生成节点
            nodes_data = []
            for i, month in enumerate(intervals):
                planned_date = data.start_date
                if month > 0:
                    from datetime import timedelta

                    planned_date = data.start_date + timedelta(days=month * 30)
                nodes_data.append(
                    {
                        "node_no": i + 1,
                        "node_month": month,
                        "node_name": f"{month}月",
                        "planned_date": planned_date,
                    }
                )
            await self.node_repo.create_bulk(study.id, nodes_data, user_id)

        await self.session.commit()
        await self.session.refresh(study)
        return study

    async def update_study(
        self,
        study_id: UUID,
        data: StabilityStudyUpdate,
        user_id: UUID | None = None,
    ) -> StabilityStudy:
        """更新稳定性试验"""
        study = await self.get_study(study_id)

        # 草稿或驳回状态才能编辑
        if study.status not in ["draft", "rejected"]:
            raise ValueError("只有草稿或驳回状态的方案可以编辑")

        # 更新主表字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key in ["sample_nodes"]:
                continue
            if hasattr(study, key):
                if key == "study_type" and value:
                    value = value.value
                elif key == "sample_intervals" and value:
                    if isinstance(value, list):
                        value = ",".join(map(str, value))
                setattr(study, key, value)

        study.updated_by = user_id
        study.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(study)
        return study

    async def delete_study(self, study_id: UUID, user_id: UUID | None = None) -> None:
        """删除稳定性试验"""
        study = await self.get_study(study_id)

        if study.status not in ["draft", "rejected"]:
            raise ValueError("只有草稿或驳回状态的方案可以删除")

        study.is_deleted = True
        study.updated_by = user_id
        study.updated_at = datetime.now()

        await self.session.commit()

    async def submit_study(self, study_id: UUID, user_id: UUID | None = None) -> StabilityStudy:
        """提交稳定性试验"""
        study = await self.get_study(study_id)

        if study.status != "draft":
            raise ValueError("只有草稿状态的方案可以提交")

        study.status = "submitted"
        study.updated_by = user_id
        study.updated_at = datetime.now()

        # 创建审批记录
        await self.approval_repo.create_record(
            study_id=study_id,
            inspection_id=None,
            approval_type="study",
            approval_level=1,
            approval_status="pending",
            approver_role="developer_supervisor",
            created_by=user_id,
        )

        await self.session.commit()
        await self.session.refresh(study)
        return study

    async def approve_study(
        self,
        study_id: UUID,
        approval_data: StabilityApprovalCreate,
        user_id: UUID | None = None,
        user_name: str | None = None,
        role: str | None = None,
    ) -> StabilityStudy:
        """审批稳定性试验"""
        study = await self.get_study(study_id)

        # 根据当前状态更新
        current_status = study.status
        if current_status == "submitted":
            next_status = "developer_approved"
        elif current_status == "developer_approved":
            next_status = "qc_supervisor_approved"
        elif current_status == "qc_supervisor_approved":
            next_status = "qa_approved"
        elif current_status == "qa_approved":
            next_status = "final_approved"
        elif current_status == "final_approved":
            next_status = "active"
        else:
            raise ValueError(f"当前状态 {current_status} 不允许审批")

        if approval_data.approval_status.value == "approved":
            study.status = next_status
        elif approval_data.approval_status.value == "rejected":
            study.status = "rejected"

        study.updated_by = user_id
        study.updated_at = datetime.now()

        # 创建审批记录
        approval_level = {
            "submitted": 1,
            "developer_approved": 2,
            "qc_supervisor_approved": 3,
            "qa_approved": 4,
            "final_approved": 5,
        }.get(current_status, 1)

        await self.approval_repo.create_record(
            study_id=study_id,
            inspection_id=None,
            approval_type="study",
            approval_level=approval_level,
            approval_status=approval_data.approval_status.value,
            approver_role=role,
            approver_id=user_id,
            approver_name=user_name,
            comments=approval_data.comments,
            created_by=user_id,
        )

        await self.session.commit()
        await self.session.refresh(study)
        return study

    # ========== Sample Node ==========

    async def get_sample_nodes(self, study_id: UUID) -> list[StabilitySampleNode]:
        """获取取样节点列表"""
        return await self.node_repo.get_by_study_id(study_id)

    async def update_sample_node(
        self,
        node_id: UUID,
        data: "StabilitySampleNodeUpdate",
        user_id: UUID | None = None,
    ) -> StabilitySampleNode:
        """更新取样节点"""
        node = await self.node_repo.get_by_id(node_id)
        if not node:
            raise ValueError("取样节点不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(node, key):
                if key == "status" and value:
                    value = value.value
                setattr(node, key, value)

        node.updated_by = user_id
        node.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(node)
        return node

    # ========== Stability Inspection ==========

    async def get_inspection(self, inspection_id: UUID) -> StabilityInspection:
        """获取检验记录"""
        inspection = await self.inspection_repo.get_by_id(inspection_id)
        if not inspection:
            raise ValueError("检验记录不存在")
        return inspection

    async def get_inspection_list(
        self,
        study_id: UUID | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StabilityInspection], int]:
        """获取检验记录列表"""
        return await self.inspection_repo.get_list(study_id, skip, limit)

    async def create_inspection(
        self,
        data: StabilityInspectionCreate,
        user_id: UUID | None = None,
    ) -> StabilityInspection:
        """创建检验记录"""
        # 获取试验信息
        study = await self.get_study(data.study_id)

        # 获取节点信息
        node = await self.node_repo.get_by_id(data.sample_node_id)
        if not node:
            raise ValueError("取样节点不存在")

        # 生成单号
        inspection_no = await self.inspection_repo.generate_inspection_no()

        # 创建检验记录
        inspection = StabilityInspection(
            study_id=data.study_id,
            study_no=study.study_no,
            sample_node_id=data.sample_node_id,
            node_month=node.node_month,
            inspection_no=inspection_no,
            product_code=study.product_code,
            product_name=study.product_name,
            batch_no=study.batch_no,
            specification=study.packaging_spec,
            inspection_date=data.inspection_date,
            inspector_id=data.inspector_id,
            inspector_name=data.inspector_name,
            sample_quantity=data.sample_quantity,
            sample_no=data.sample_no,
            sample_condition=data.sample_condition,
            standard_id=data.standard_id or study.standard_id,
            standard_name=data.standard_name or study.standard_name,
            inspection_conclusion=data.inspection_conclusion.value if data.inspection_conclusion else None,
            conclusion_reason=data.conclusion_reason,
            remark=data.remark,
            oos_report_no=data.oos_report_no,
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
                    "inspection_item": item.inspection_item,
                    "inspection_method": item.inspection_method,
                    "standard_value": item.standard_value,
                    "unit": item.unit,
                    "measured_value": item.measured_value,
                    "result": item.result.value if item.result else None,
                    "is_oos": item.is_oos,
                    "oos_description": item.oos_description,
                    "data_point": item.data_point,
                    "chromatogram_urls": item.chromatogram_urls,
                    "remark": item.remark,
                }
                for item in data.items
            ]
            await self.item_repo.create_bulk(inspection.id, items_data, user_id)

        # 更新节点状态
        node.status = "inspection_done"
        node.inspection_id = inspection.id
        node.inspection_no = inspection_no
        node.inspection_status = "draft"
        node.updated_by = user_id
        node.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def update_inspection(
        self,
        inspection_id: UUID,
        data: StabilityInspectionUpdate,
        user_id: UUID | None = None,
    ) -> StabilityInspection:
        """更新检验记录"""
        inspection = await self.get_inspection(inspection_id)

        # 草稿或驳回状态才能编辑
        if inspection.status not in ["draft", "rejected"]:
            raise ValueError("只有草稿或驳回状态的检验记录可以编辑")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "items":
                continue
            if hasattr(inspection, key):
                if key == "inspection_conclusion" and value:
                    value = value.value
                setattr(inspection, key, value)

        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()

        # 更新明细
        if data.items is not None:
            old_items = await self.item_repo.get_by_inspection_id(inspection_id)
            for item in old_items:
                item.is_deleted = True

            items_data = [
                {
                    "item_no": item.item_no,
                    "inspection_item": item.inspection_item,
                    "inspection_method": item.inspection_method,
                    "standard_value": item.standard_value,
                    "unit": item.unit,
                    "measured_value": item.measured_value,
                    "result": item.result.value if item.result else None,
                    "is_oos": item.is_oos,
                    "oos_description": item.oos_description,
                    "data_point": item.data_point,
                    "chromatogram_urls": item.chromatogram_urls,
                    "remark": item.remark,
                }
                for item in data.items
            ]
            await self.item_repo.create_bulk(inspection_id, items_data, user_id)

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def submit_inspection(self, inspection_id: UUID, user_id: UUID | None = None) -> StabilityInspection:
        """提交检验记录"""
        inspection = await self.get_inspection(inspection_id)

        if inspection.status != "draft":
            raise ValueError("只有草稿状态的检验记录可以提交")

        inspection.status = "submitted"
        inspection.updated_by = user_id
        inspection.updated_at = datetime.now()

        # 更新节点状态
        node = await self.node_repo.get_by_id(inspection.sample_node_id)
        if node:
            node.inspection_status = "submitted"
            node.updated_by = user_id
            node.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    # ========== Trend Analysis ==========

    async def get_trend_data(self, study_id: UUID) -> dict[str, Any]:
        """获取趋势分析数据"""
        study = await self.get_study(study_id)
        inspections = await self.inspection_repo.get_by_study_id(study_id)

        # 按检验项目分组
        trend_data = {}  # type: ignore[var-annotated]
        for inspection in inspections:
            items = await self.item_repo.get_by_inspection_id(inspection.id)
            for item in items:
                if item.inspection_item not in trend_data:
                    trend_data[item.inspection_item] = []
                trend_data[item.inspection_item].append(
                    {
                        "node_month": inspection.node_month,
                        "measured_value": item.measured_value,
                        "result": item.result,
                        "inspection_date": inspection.inspection_date,
                    }
                )

        # 排序
        for item_name in trend_data:
            trend_data[item_name].sort(key=lambda x: x["node_month"])

        return {
            "study_no": study.study_no,
            "product_code": study.product_code,
            "product_name": study.product_name,
            "batch_no": study.batch_no,
            "study_type": study.study_type,
            "trend_data": trend_data,
        }
