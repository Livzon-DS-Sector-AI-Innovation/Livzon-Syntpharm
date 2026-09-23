"""CAPA Service"""

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.capa_models import CapaWorkflowStatus
from app.modules.quality.qms.capa_repository import CapaRepository
from app.modules.quality.qms.capa_schemas import CapaCreate, CapaUpdate


class CapaService:
    """CAPA Service"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CapaRepository(session)

    async def create_capa(self, data: CapaCreate) -> dict[str, Any]:
        """创建 CAPA"""
        # 生成 CAPA 编号
        capa_code = await self.repo.get_next_capa_code()

        # 转换 capa_items 为 JSON
        capa_items_json = None
        if data.capa_items:
            capa_items_json = [item.model_dump() for item in data.capa_items]

        capa_data = {
            "capa_code": capa_code,
            "title": data.title,
            "source": data.source,
            "source_code": data.source_code,
            "category": data.category,
            "root_cause_category": data.root_cause_category,
            "non_conformity_description": data.non_conformity_description,
            "root_cause_analysis": data.root_cause_analysis,
            "capa_content": data.capa_content,
            "capa_items": capa_items_json,
            "executors": data.executors,
            "expected_completion_date": data.expected_completion_date,
            "deviation_id": data.deviation_id,
            "status": CapaWorkflowStatus.DRAFT,
        }

        capa = await self.repo.create(capa_data)
        return capa.__dict__

    async def get_capa(self, capa_id: UUID) -> dict[str, Any] | None:
        """获取 CAPA 详情"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None
        return capa.__dict__

    async def update_capa(self, capa_id: UUID, data: CapaUpdate) -> dict[str, Any] | None:
        """更新 CAPA"""
        update_data = data.model_dump(exclude_unset=True)

        # 转换 capa_items 为 JSON
        if "capa_items" in update_data and update_data["capa_items"]:
            update_data["capa_items"] = [item.model_dump() for item in data.capa_items]  # type: ignore[union-attr]

        capa = await self.repo.update(capa_id, update_data)
        if not capa:
            return None
        return capa.__dict__

    async def delete_capa(self, capa_id: UUID) -> bool:
        """删除 CAPA"""
        return await self.repo.delete(capa_id)

    async def list_capas(
        self,
        capa_code: str | None = None,
        source: str | None = None,
        category: str | None = None,
        status: str | None = None,
        deviation_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取 CAPA 列表"""
        capas, total = await self.repo.list_with_filter(
            capa_code=capa_code,
            source=source,
            category=category,
            status=status,
            deviation_id=deviation_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        return [capa.__dict__ for capa in capas], total

    async def submit_capa(self, capa_id: UUID) -> dict[str, Any] | None:
        """提交 CAPA"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        if capa.status != CapaWorkflowStatus.DRAFT:
            raise ValueError("只有草稿状态的 CAPA 可以提交")

        capa = await self.repo.update(
            capa_id,
            {
                "status": CapaWorkflowStatus.SUBMITTED,
                "status_updated_at": datetime.utcnow(),
            },
        )
        return capa.__dict__ if capa else None

    async def approve_capa(
        self,
        capa_id: UUID,
        approver_id: UUID,
        approver_name: str,
        opinion: str,
        approved: bool,
    ) -> dict[str, Any] | None:
        """审核 CAPA"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        if capa.status != CapaWorkflowStatus.SUBMITTED:
            raise ValueError("只有已提交的 CAPA 可以审核")

        update_data = {
            "qa_reviewer_id": approver_id,
            "qa_review_opinion": opinion,
            "qa_review_time": datetime.utcnow(),
            "status_updated_at": datetime.utcnow(),
        }

        if approved:
            update_data["status"] = CapaWorkflowStatus.PENDING_Q_HEAD_APPROVAL
        else:
            update_data["status"] = CapaWorkflowStatus.RETURNED
            update_data["returned_step"] = "qa_review"

        capa = await self.repo.update(capa_id, update_data)
        return capa.__dict__ if capa else None

    async def resubmit_capa(self, capa_id: UUID) -> dict[str, Any] | None:
        """重新提交 CAPA"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        if capa.status != CapaWorkflowStatus.RETURNED:
            raise ValueError("只有已退回的 CAPA 可以重新提交")

        capa = await self.repo.update(
            capa_id,
            {
                "status": CapaWorkflowStatus.SUBMITTED,
                "status_updated_at": datetime.utcnow(),
            },
        )
        return capa.__dict__ if capa else None

    async def add_execution_track(
        self,
        capa_id: UUID,
        execution_status: str,
        execution_date: str | None = None,
        execution_notes: str | None = None,
    ) -> dict[str, Any] | None:
        """添加执行跟踪"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        # 获取现有跟踪记录
        tracks = capa.execution_tracks or []

        # 添加新记录
        new_track = {
            "id": str(uuid.uuid4()),
            "executionStatus": execution_status,
            "execution_date": execution_date,
            "execution_notes": execution_notes,
        }
        tracks.append(new_track)

        capa = await self.repo.update(
            capa_id,
            {
                "execution_tracks": tracks,
                "execution_status": execution_status,
                "status_updated_at": datetime.utcnow(),
            },
        )
        return capa.__dict__ if capa else None

    async def delete_execution_track(self, capa_id: UUID, track_id: str) -> dict[str, Any] | None:
        """删除执行跟踪"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        tracks = capa.execution_tracks or []
        tracks = [t for t in tracks if t.get("id") != track_id]

        capa = await self.repo.update(
            capa_id,
            {
                "execution_tracks": tracks,
                "status_updated_at": datetime.utcnow(),
            },
        )
        return capa.__dict__ if capa else None

    async def confirm_execution(
        self,
        capa_id: UUID,
        qa_confirmer: str,
        qa_confirm_date: str,
    ) -> dict[str, Any] | None:
        """确认执行"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        # 更新最后一个跟踪记录的确认信息
        tracks = capa.execution_tracks or []
        if tracks:
            tracks[-1]["qaConfirmer"] = qa_confirmer
            tracks[-1]["qaConfirmDate"] = qa_confirm_date

        capa = await self.repo.update(
            capa_id,
            {
                "execution_tracks": tracks,
                "qa_confirmer": qa_confirmer,
                "qa_confirm_date": datetime.fromisoformat(qa_confirm_date.replace("Z", "+00:00")),
                "status_updated_at": datetime.utcnow(),
            },
        )
        return capa.__dict__ if capa else None

    async def evaluate_capa(
        self,
        capa_id: UUID,
        evaluation_result: str,
        evaluation_target: str,
        evaluation_deadline: datetime,
    ) -> dict[str, Any] | None:
        """评估 CAPA"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        capa = await self.repo.update(
            capa_id,
            {
                "evaluation_result": evaluation_result,
                "evaluation_target": evaluation_target,
                "evaluation_deadline": evaluation_deadline,
                "status": CapaWorkflowStatus.PENDING_EVALUATION,
                "status_updated_at": datetime.utcnow(),
            },
        )
        return capa.__dict__ if capa else None

    async def complete_part(self, capa_id: UUID, part: str) -> dict[str, Any] | None:
        """完成部分"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        # 根据部分更新状态
        status_map = {
            "part_a": CapaWorkflowStatus.PART_B,
            "part_b": CapaWorkflowStatus.PART_C,
            "part_c": CapaWorkflowStatus.PENDING_DEPT_HEAD_CONFIRM,
        }

        new_status = status_map.get(part)
        if not new_status:
            raise ValueError(f"无效的部分: {part}")

        capa = await self.repo.update(
            capa_id,
            {
                "status": new_status,
                "status_updated_at": datetime.utcnow(),
            },
        )
        return capa.__dict__ if capa else None

    async def confirm_dept_head(
        self,
        capa_id: UUID,
        department: str,
        dept_head_user_id: str,
        result: str,
        opinion: str,
    ) -> dict[str, Any] | None:
        """部门负责人确认"""
        capa = await self.repo.get_by_id(capa_id)
        if not capa:
            return None

        # 获取现有确认记录
        confirmations = capa.dept_head_confirmations or []

        # 添加新确认
        new_confirmation = {
            "department": department,
            "deptHeadUserId": dept_head_user_id,
            "result": result,
            "opinion": opinion,
            "confirmTime": datetime.utcnow().isoformat(),
        }
        confirmations.append(new_confirmation)

        capa = await self.repo.update(
            capa_id,
            {
                "dept_head_confirmations": confirmations,
                "status_updated_at": datetime.utcnow(),
            },
        )
        return capa.__dict__ if capa else None
