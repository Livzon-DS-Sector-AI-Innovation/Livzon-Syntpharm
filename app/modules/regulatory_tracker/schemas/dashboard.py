"""Dashboard schemas V2 - 原料药企业影响评估。"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SourceStatusItem(BaseModel):
    code: str
    name: str
    status: str  # active / pending / future
    lastSyncTime: datetime | None = None
    todayNewCount: int = 0


class TrendItem(BaseModel):
    date: str
    count: int


class PriorityDocument(BaseModel):
    """重点关注法规。"""

    id: str
    title: str
    publishDate: str | None = None
    classification: str | None = None
    statusText: str | None = None
    sourceName: str | None = None
    channelName: str | None = None
    impact_level: str  # high / medium / low / none
    impact_score: float  # 0-1
    lifecycle_impact: list[str] = []
    departments: list[str] = []
    recommended_actions: list[str] = []
    ai_summary: str | None = None


class DashboardResponse(BaseModel):
    todayNewCount: int
    weekNewCount: int
    unreadCount: int
    aiAnalyzedCount: int
    highImpactCount: int = 0
    mediumImpactCount: int = 0
    unanalyzedCount: int = 0
    trend7Days: list[TrendItem]
    byClassification: dict[str, int]
    sourceStatus: list[SourceStatusItem]
    todayNewDocuments: list[dict]
    priorityDocuments: list[PriorityDocument] = []


class SyncTriggerRequest(BaseModel):
    sourceCode: str = "CDE"
    channelCode: str = "cde_domestic_guideline"
    startPage: int = 1
    endPage: int = 3
    autoAnalyze: bool = False  # 同步后自动分析新增法规


class BatchReadRequest(BaseModel):
    documentIds: list[uuid.UUID]
