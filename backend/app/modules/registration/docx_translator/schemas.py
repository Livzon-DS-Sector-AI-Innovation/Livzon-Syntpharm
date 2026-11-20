"""DOCX 翻译 —— 接口契约。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas import DataResponse, PaginationMeta

DocxTranslationMode = Literal["bilingual", "replace", "both"]
OutputKind = Literal["bilingual", "translated"]
JobStatus = Literal["running", "done", "failed"]


# ── 任务 ──────────────────────────────────────────────────


class DocxTranslationOutput(BaseModel):
    kind: OutputKind = Field(description="bilingual=双语对照版，translated=纯译文版")
    filename: str
    file_index: int = Field(description="下载用的文件索引（按任务内顺序）")


class DocxTranslationFileResult(BaseModel):
    filename: str
    success: bool
    outputs: list[DocxTranslationOutput] = []
    translated_units: int = 0
    total_units: int = 0
    success_rate: float = 0.0
    warnings: list[str] = []
    error: str | None = None
    skipped_units: int = 0


class DocxTranslationJobAccepted(BaseModel):
    job_id: str
    status: Literal["running"] = "running"


class DocxTranslationJobState(BaseModel):
    job_id: str
    status: JobStatus
    files_done: int = 0
    files_total: int = 0
    current_file: str | None = None
    files: list[DocxTranslationFileResult] = []
    error: str | None = None
    batch_done: int = 0
    batch_total: int = 0
    elapsed_seconds: int = 0


class DocxTranslationJobListData(BaseModel):
    items: list[DocxTranslationJobState]


DocxTranslationJobStateResponse = DataResponse[DocxTranslationJobState]
DocxTranslationJobListResponse = DataResponse[DocxTranslationJobListData]


# ── 术语表 ────────────────────────────────────────────────


class DocxGlossaryTermResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    term_en: str
    term_zh: str
    is_enabled: bool
    source: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocxGlossaryTermCreate(BaseModel):
    term_en: str = Field(min_length=1, max_length=300)
    term_zh: str = Field(min_length=1, max_length=300)
    is_enabled: bool = True


class DocxGlossaryTermUpdate(BaseModel):
    term_en: str | None = Field(default=None, min_length=1, max_length=300)
    term_zh: str | None = Field(default=None, min_length=1, max_length=300)
    is_enabled: bool | None = None


class DocxGlossaryTermListData(BaseModel):
    items: list[DocxGlossaryTermResponse]
    total: int
    meta: PaginationMeta | None = None


class DocxGlossaryImportData(BaseModel):
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    total: int = 0


DocxGlossaryTermItemResponse = DataResponse[DocxGlossaryTermResponse]
DocxGlossaryTermListResponse = DataResponse[DocxGlossaryTermListData]
DocxGlossaryImportResponse = DataResponse[DocxGlossaryImportData]


# ── 历史产出文件 ──────────────────────────────────────────


class DocxTranslationFileRecord(BaseModel):
    """历史译文记录（一行 = 一份可下载文件）。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_ref: str
    source_filename: str
    output_filename: str
    output_kind: OutputKind
    source_lang: str
    target_lang: str
    mode: str
    success_rate: float
    translated_units: int
    total_units: int
    file_size: int
    warnings: list[str] = []
    created_at: datetime | None = None
    created_by_name: str | None = None
    can_delete: bool = False


class DocxTranslationFileListData(BaseModel):
    items: list[DocxTranslationFileRecord]
    total: int
    meta: PaginationMeta | None = None


DocxTranslationFileListResponse = DataResponse[DocxTranslationFileListData]


# ── 任务级历史 ────────────────────────────────────────────


class DocxTranslationTaskRecord(BaseModel):
    """任务级历史（一行 = 一次翻译提交）。"""

    id: UUID
    job_ref: str
    status: str
    source_count: int
    success_count: int
    fail_count: int
    first_source_filename: str
    source_lang: str
    target_lang: str
    mode: str
    elapsed_seconds: int
    total_file_size: int = 0
    created_at: datetime | None = None
    created_by_name: str | None = None
    can_delete: bool = False
    can_retranslate: bool = False


class DocxTranslationTaskFile(BaseModel):
    """任务下的单个文件结果（成功带下载信息，失败带原因）。"""

    id: UUID
    source_filename: str
    output_filename: str
    output_kind: str
    success: bool
    success_rate: float
    translated_units: int
    total_units: int
    file_size: int
    error: str | None = None


class DocxTranslationTaskListData(BaseModel):
    items: list[DocxTranslationTaskRecord]
    total: int
    meta: PaginationMeta | None = None


class DocxTranslationTaskDetailData(BaseModel):
    task: DocxTranslationTaskRecord
    files: list[DocxTranslationTaskFile]
    warnings: list[str] = []


DocxTranslationTaskListResponse = DataResponse[DocxTranslationTaskListData]
DocxTranslationTaskDetailResponse = DataResponse[DocxTranslationTaskDetailData]
DocsTranslationRetranslateResponse = DataResponse[DocxTranslationJobAccepted]
