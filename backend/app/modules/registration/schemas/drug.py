"""Drug schemas."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class DrugNodeCreate(BaseModel):
    node_index: int = Field(ge=1, le=10)
    actual_date: date | None = None


class DrugNodeUpdate(BaseModel):
    node_index: int = Field(ge=1, le=10)
    actual_date: date | None = None
    skipped: bool | None = None


class DrugCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: Literal["仿制药", "创新药", "原料药"]
    acceptance_date: date
    acceptance_number: str | None = Field(None, max_length=128)


class DrugUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    type: Literal["仿制药", "创新药", "原料药"] | None = None
    acceptance_date: date | None = None
    acceptance_number: str | None = Field(None, max_length=128)
    nodes: list[DrugNodeUpdate] | None = None


class DrugNodeResponse(BaseModel):
    id: uuid.UUID
    drug_id: uuid.UUID
    node_index: int
    actual_date: date | None
    skipped: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DrugResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    acceptance_date: date
    acceptance_number: str | None = None
    current_node: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DrugWithNodesResponse(DrugResponse):
    nodes: list[DrugNodeResponse]


class NodePrediction(BaseModel):
    """单个节点的预测信息"""

    node_index: int
    node_name: str
    status: Literal["completed", "in_progress", "pending", "skipped"]
    actual_date: date | None = None
    estimated_date: date | None = None
    estimated_range: tuple[date, date] | None = None
    delta_days: int | None = None


class DrugPredictionResponse(BaseModel):
    """药品审评进度预测"""

    drug_id: uuid.UUID
    total_nodes: int
    completed_nodes: int
    current_node_index: int | None = None
    days_in_current_node: int | None = None
    estimated_approval_date: date | None = None
    nodes: list[NodePrediction]
