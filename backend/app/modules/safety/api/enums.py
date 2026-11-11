"""Safety API — enums endpoints."""

from typing import Any

from fastapi import APIRouter

from app.core.deps import RequiredUser
from app.core.response import build_response
from app.modules.safety.risk_grading import (
    CONSEQUENCE_MAX,
    CONSEQUENCE_MIN,
    CONTROL_MEASURE_OPTIONS,
    EQUIPMENT_EVALUATION_GRADE_BANDS,
    EQUIPMENT_MEASURE_OPTIONS,
    EVALUATION_GRADE_THRESHOLDS,
    EXECUTION_LEVEL_OPTIONS,
    EXPOSURE_MAX,
    EXPOSURE_MIN,
    LIKELIHOOD_LEVELS,
    LIKELIHOOD_MAX,
    LIKELIHOOD_MIN,
    MIN_RISK_VALUE,
    RESIDUAL_RISK_OPTIONS,
    RISK_GRADING_DEPARTMENTS,
    SAFETY_RISK_MATRIX,
    SEVERITY_LEVELS,
)
from app.modules.safety.schemas import (
    ABNORMALITY_STATUS_OPTIONS,
    ACCIDENT_LEVEL_OPTIONS,
    ACCIDENT_STATUS_OPTIONS,
    ACCIDENT_TYPE_OPTIONS,
    ACTION_ITEM_STATUS_OPTIONS,
    APPROVAL_DECISION_OPTIONS,
    CHANGE_DURATION_OPTIONS,
    CHANGE_GRADE_OPTIONS,
    CHANGE_TYPE_OPTIONS,
    CHECK_TYPE_OPTIONS,
    COMPLETION_METHOD_OPTIONS,
    CONTRACTOR_STATUS_OPTIONS,
    CONTRACTOR_TRAINING_STATUS_OPTIONS,
    DETECTION_TYPE_OPTIONS,
    EHS_CHANGE_STATUS_OPTIONS,
    EXAM_CONCLUSION_OPTIONS,
    EXAM_STATUS_OPTIONS,
    EXAM_TYPE_OPTIONS,
    HAZARD_CATEGORY_OPTIONS,
    HAZARD_FACTOR_CATEGORY_OPTIONS,
    HAZARD_LEVEL_OPTIONS,
    HAZARD_TYPE_OPTIONS,
    INJURY_SEVERITY_OPTIONS,
    KNOWLEDGE_CATEGORY_OPTIONS,
    MONITOR_STATUS_OPTIONS,
    OEL_COMPLIANCE_STATUS_OPTIONS,
    OPERATION_LEVEL_OPTIONS,
    OPERATION_TYPE_OPTIONS,
    PERMIT_STATUS_OPTIONS,
    PERSONNEL_STATUS_OPTIONS,
    PSSR_RESULT_OPTIONS,
    QUALIFICATION_LEVEL_OPTIONS,
    QUALIFICATION_TYPE_OPTIONS,
    REPORT_STATUS_OPTIONS,
    REVIEW_OPINION_OPTIONS,
    REVISION_SCOPE_OPTIONS,
    REVISION_TYPE_OPTIONS,
    RISK_ASSESSMENT_METHOD_OPTIONS,
    RISK_LEVEL_OPTIONS,
    TRAINING_MODE_OPTIONS,
    TRAINING_TYPE_OPTIONS,
    WORK_RECORD_STATUS_OPTIONS,
    SafetyEnumsApiResponse,
)
from app.modules.safety.schemas.risk_grading import (
    EquipmentGradeBand,
    LecRange,
    RiskGradeThreshold,
    RiskGradingOptions,
    RiskGradingOptionsApiResponse,
    RiskGradingValueLabel,
)

enums_router = APIRouter()


@enums_router.get("/enums", response_model=SafetyEnumsApiResponse, summary="获取枚举值列表")
async def get(current_user: RequiredUser) -> Any:
    """获取安全模块的所有枚举值选项"""

    return SafetyEnumsApiResponse(
        data={
            "check_types": CHECK_TYPE_OPTIONS,
            "hazard_types": HAZARD_TYPE_OPTIONS,
            "hazard_levels": HAZARD_LEVEL_OPTIONS,
            "hazard_categories": HAZARD_CATEGORY_OPTIONS,
            "accident_types": ACCIDENT_TYPE_OPTIONS,
            "accident_levels": ACCIDENT_LEVEL_OPTIONS,
            "accident_statuses": ACCIDENT_STATUS_OPTIONS,
            "injury_severities": INJURY_SEVERITY_OPTIONS,
            "training_types": TRAINING_TYPE_OPTIONS,
            "training_modes": TRAINING_MODE_OPTIONS,
            "revision_types": REVISION_TYPE_OPTIONS,
            "revision_scopes": REVISION_SCOPE_OPTIONS,
            "review_opinions": REVIEW_OPINION_OPTIONS,
            "operation_types": OPERATION_TYPE_OPTIONS,
            "operation_levels": OPERATION_LEVEL_OPTIONS,
            "personnel_statuses": PERSONNEL_STATUS_OPTIONS,
            "permit_statuses": PERMIT_STATUS_OPTIONS,
            "completion_methods": COMPLETION_METHOD_OPTIONS,
            "knowledge_categories": KNOWLEDGE_CATEGORY_OPTIONS,
            "report_statuses": REPORT_STATUS_OPTIONS,
            "contractor_statuses": CONTRACTOR_STATUS_OPTIONS,
            "qualification_types": QUALIFICATION_TYPE_OPTIONS,
            "qualification_levels": QUALIFICATION_LEVEL_OPTIONS,
            "contractor_training_statuses": CONTRACTOR_TRAINING_STATUS_OPTIONS,
            "work_record_statuses": WORK_RECORD_STATUS_OPTIONS,
            "ehs_change_types": CHANGE_TYPE_OPTIONS,
            "ehs_change_grades": CHANGE_GRADE_OPTIONS,
            "ehs_change_durations": CHANGE_DURATION_OPTIONS,
            "ehs_change_statuses": EHS_CHANGE_STATUS_OPTIONS,
            "risk_levels": RISK_LEVEL_OPTIONS,
            "risk_assessment_methods": RISK_ASSESSMENT_METHOD_OPTIONS,
            "approval_decisions": APPROVAL_DECISION_OPTIONS,
            "action_item_statuses": ACTION_ITEM_STATUS_OPTIONS,
            "pssr_results": PSSR_RESULT_OPTIONS,
            "oh_detection_types": DETECTION_TYPE_OPTIONS,
            "oh_hazard_factor_categories": HAZARD_FACTOR_CATEGORY_OPTIONS,
            "oh_oel_compliance_statuses": OEL_COMPLIANCE_STATUS_OPTIONS,
            "oh_monitor_statuses": MONITOR_STATUS_OPTIONS,
            "oh_exam_types": EXAM_TYPE_OPTIONS,
            "oh_exam_conclusions": EXAM_CONCLUSION_OPTIONS,
            "oh_exam_statuses": EXAM_STATUS_OPTIONS,
            "oh_abnormality_statuses": ABNORMALITY_STATUS_OPTIONS,
        }
    )


def _value_label_options(options: tuple[dict[str, str], ...]) -> list[RiskGradingValueLabel]:
    return [RiskGradingValueLabel(value=item["key"], label=item["label"]) for item in options]


@enums_router.get(
    "/enums/risk-grading",
    response_model=RiskGradingOptionsApiResponse,
    summary="获取风险分级管控台账的选项、矩阵与分级阈值",
)
async def get_risk_grading_options(current_user: RequiredUser) -> Any:
    """风险分级管控台账的权威选项字典；前端不得再手写这些常量。"""

    return build_response(
        data=RiskGradingOptions(
            departments=list(RISK_GRADING_DEPARTMENTS),
            control_measures=_value_label_options(CONTROL_MEASURE_OPTIONS),
            equipment_measures=_value_label_options(EQUIPMENT_MEASURE_OPTIONS),
            residual_risks=_value_label_options(RESIDUAL_RISK_OPTIONS),
            execution_levels=_value_label_options(EXECUTION_LEVEL_OPTIONS),
            likelihood_levels=list(LIKELIHOOD_LEVELS),
            severity_levels=list(SEVERITY_LEVELS),
            safety_risk_matrix={key: list(row) for key, row in SAFETY_RISK_MATRIX.items()},
            grade_thresholds=[
                RiskGradeThreshold(grade=grade, lower_bound_exclusive=lower_bound)
                for grade, lower_bound in EVALUATION_GRADE_THRESHOLDS
            ],
            equipment_grade_bands=[
                EquipmentGradeBand(grade=grade, label=label, min_r=min_r)
                for grade, label, min_r in EQUIPMENT_EVALUATION_GRADE_BANDS
            ],
            likelihood_range=LecRange(min=LIKELIHOOD_MIN, max=LIKELIHOOD_MAX),
            exposure_range=LecRange(min=EXPOSURE_MIN, max=EXPOSURE_MAX),
            consequence_range=LecRange(min=CONSEQUENCE_MIN, max=CONSEQUENCE_MAX),
            min_risk_value=MIN_RISK_VALUE,
        )
    )
