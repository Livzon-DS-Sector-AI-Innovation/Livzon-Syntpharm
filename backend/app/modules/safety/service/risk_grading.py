"""风险分级管控台账 service：作业活动危险源（LEC）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.modules.safety.models import WorkActivityHazard
from app.modules.safety.repository import SafetyRepository
from app.modules.safety.risk_grading import (
    MIN_RISK_VALUE,
    RESIDUAL_RISK_LABELS,
    compute_risk_value,
    derive_evaluation_grade,
)
from app.modules.safety.schemas.risk_grading import WorkActivityHazardCreate
from app.modules.safety.service._helpers import audit_log


class WorkActivityHazardService:
    """作业活动危险源台账业务逻辑。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SafetyRepository(session)

    async def list_hazards(self, skip: int, limit: int) -> tuple[list[WorkActivityHazard], int]:
        return await self.repo.get_work_activity_hazards(skip, limit)

    async def create_hazard(self, data: WorkActivityHazardCreate) -> WorkActivityHazard:
        risk_value = compute_risk_value(data.likelihood_l, data.exposure_e, data.consequence_c)
        if risk_value <= MIN_RISK_VALUE:
            raise BadRequestException(f"风险值 D={risk_value} 必须大于 20，不允许提交")
        grade, grade_label = derive_evaluation_grade(risk_value)

        payload: dict[str, Any] = data.model_dump()
        payload.update(
            risk_value_d=risk_value,
            evaluation_grade=grade,
            evaluation_grade_label=grade_label,
            residual_risk_label=RESIDUAL_RISK_LABELS[data.residual_risk],
        )
        item = await self.repo.create_work_activity_hazard(payload)
        await audit_log(self.session, "create", "work_activity_hazard", resource_id=item.id)
        return item
