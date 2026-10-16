"""偏差报告自动化 Schemas"""

from datetime import date

from pydantic import BaseModel


class SOPRuleCreate(BaseModel):
    sop_code: str
    sop_full_name: str
    sop_version: str
    business_tag: str | None = None
    standard_limit: str | None = None
    standard_sentence: str | None = None
    sop_file_path: str | None = None


class SOPRuleUpdate(BaseModel):
    sop_code: str | None = None
    sop_full_name: str | None = None
    sop_version: str | None = None
    business_tag: str | None = None
    standard_limit: str | None = None
    standard_sentence: str | None = None
    status: int | None = None
    sop_file_path: str | None = None


class DevTaskCreate(BaseModel):
    deviation_no: str
    creator: str
    auditor: str | None = None
    report_date: date


class AIResultUpdate(BaseModel):
    ai_result: str


class ReportTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    is_active: int | None = 1


class ReportTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    file_path: str | None = None
    is_active: int | None = None
