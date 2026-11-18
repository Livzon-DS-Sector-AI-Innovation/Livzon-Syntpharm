"""工作台聚合接口的响应模型。

字段命名遵循前端契约（snake_case），数值型计数一律给整数，前端只负责展示。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WorkbenchItemModel(BaseModel):
    """一条待办 / 流程事项。"""

    id: str
    source: str = Field(description="数据源标识，如 deviation / iqc / hazard")
    module_key: str = Field(description="模块码：quality / safety")
    module_label: str
    doc_type_label: str = Field(description="单据类型中文名，如「偏差台账」")
    title: str
    doc_no: str | None = None
    status: str = ""
    status_label: str = ""
    step_label: str | None = Field(default=None, description="当前环节中文")
    match_kind: str = Field(description="判定依据：person=待我审批 / role=同角色待办")
    match_kind_label: str = ""
    age_days: int | None = Field(default=None, description="停留天数")
    overdue: bool = False
    path: str | None = Field(default=None, description="前端跳转路径；空表示暂无页面")
    my_roles: list[str] = Field(default_factory=list, description="我在该流程中的角色")
    is_read: bool = Field(default=False, description="当前用户是否已读（按内容指纹判定，仅待办有效）")
    fingerprint: str = Field(default="", description="内容指纹；标记已读时原样回传，内容变化后自动失效")


class WorkbenchGroupModel(BaseModel):
    """按模块分组后的条目集合。"""

    module_key: str
    module_label: str
    count: int = 0
    has_more: bool = False
    items: list[WorkbenchItemModel] = Field(default_factory=list)


class TodoSectionModel(BaseModel):
    """审核待办区块。"""

    total: int = 0
    #: 未读条数（只有本次返回的条目参与计算，配合 ``has_more`` 用「N+」呈现）
    unread_total: int = 0
    has_more: bool = False
    person_total: int = 0
    role_total: int = 0
    groups: list[WorkbenchGroupModel] = Field(default_factory=list)


class ProcessSectionModel(BaseModel):
    """我参与的流程区块。"""

    total: int = 0
    has_more: bool = False
    groups: list[WorkbenchGroupModel] = Field(default_factory=list)


class WorkbenchOverviewData(BaseModel):
    todos: TodoSectionModel = Field(default_factory=TodoSectionModel)
    processes: ProcessSectionModel = Field(default_factory=ProcessSectionModel)
    generated_at: datetime
    degraded_sources: list[str] = Field(
        default_factory=list,
        description="取数失败被降级的数据源（前端可提示「部分数据暂不可用」）",
    )


class WorkbenchOverviewResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WorkbenchOverviewData


class TodoReadMark(BaseModel):
    """一条待办已读标记（客户端把 ``/overview`` 返回的指纹原样回传）。"""

    source: str = Field(min_length=1, max_length=100, description="数据源标识，如 quality.deviation.todos")
    item_id: str = Field(min_length=1, max_length=64, description="待办条目 ID")
    fingerprint: str = Field(min_length=1, max_length=255, description="内容指纹，来自 /overview")


class TodoReadBatchRequest(BaseModel):
    """一键已读：客户端传当前看到的全部未读项（受 todo_limit 影响，与用户所见一致）。"""

    items: list[TodoReadMark] = Field(default_factory=list, max_length=100)


class TodoReadResultData(BaseModel):
    marked: int = Field(default=0, description="本次写入（含更新）的已读记录数")


class TodoReadResultResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: TodoReadResultData
