"""偏差模块组织配置的请求 / 响应模型。

覆盖两块配置（均映射基线迁移里已存在的表，不产生新 DDL）：

- 部门联系人：审核各环节处理人的唯一来源；
- 部门周确认 + 通知设置：周提醒任务与飞书通知开关。

人员字段同时返回 ID 与姓名：ID 供表单回填，姓名供列表直接展示，避免前端二次查询。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

WEEKLY_PRODUCTION_STATUSES = ("production", "stopped")
WEEKLY_DEVIATION_STATUSES = ("submitted", "unsubmitted")


class DepartmentContactItem(BaseModel):
    """部门联系人行。"""

    id: uuid.UUID
    department: str
    dept_head_id: uuid.UUID | None = None
    dept_head_name: str | None = None
    dept_head_avatar: str | None = Field(None, description="部门负责人头像")
    production_head_id: uuid.UUID | None = None
    production_head_name: str | None = None
    production_head_avatar: str | None = Field(None, description="生产负责人头像")
    quality_head_id: uuid.UUID | None = None
    quality_head_name: str | None = None
    quality_head_avatar: str | None = Field(None, description="质量负责人头像")
    qa_reviewer_id: uuid.UUID | None = Field(None, description="所属 QA（所属QA审核节点处理人）")
    qa_reviewer_name: str | None = None
    qa_reviewer_avatar: str | None = Field(None, description="所属 QA 头像")
    qa_head_id: uuid.UUID | None = Field(None, description="QA 负责人（QA负责人审核节点处理人）")
    qa_head_name: str | None = None
    qa_head_avatar: str | None = Field(None, description="QA 负责人头像")
    qa_staff_ids: list[str] = Field(default_factory=list, description="兼容字段：历史 QA 人员数组")
    qa_staff_names: list[str] = Field(default_factory=list)
    qa_staff_avatars: list[str | None] = Field(default_factory=list, description="QA 人员头像，与姓名同序")
    gmp_staff_ids: list[str] = Field(default_factory=list)
    gmp_staff_names: list[str] = Field(default_factory=list)
    gmp_staff_avatars: list[str | None] = Field(default_factory=list, description="GMP 人员头像，与姓名同序")
    additional_contacts: list[str] = Field(default_factory=list)
    additional_contact_names: list[str] = Field(default_factory=list)
    additional_contact_avatars: list[str | None] = Field(default_factory=list, description="其他联系人头像，与姓名同序")
    is_production_workshop: bool = False
    updated_at: datetime | None = None


class DepartmentContactListData(BaseModel):
    """部门联系人列表数据。"""

    items: list[DepartmentContactItem]
    total: int


class DepartmentContactCreateRequest(BaseModel):
    """新增部门联系人。"""

    department: str = Field(min_length=1, max_length=255, description="部门名称（唯一）")
    dept_head_id: uuid.UUID | None = Field(None, description="部门负责人")
    production_head_id: uuid.UUID | None = Field(None, description="生产负责人")
    quality_head_id: uuid.UUID | None = Field(None, description="质量负责人")
    qa_reviewer_id: uuid.UUID | None = Field(None, description="所属 QA")
    qa_head_id: uuid.UUID | None = Field(None, description="QA 负责人")
    qa_staff_ids: list[str] = Field(
        default_factory=list,
        description="兼容字段（历史 [0]=所属QA、[1]=QA负责人）；流程以 qa_reviewer_id / qa_head_id 为准",
    )
    gmp_staff_ids: list[str] = Field(default_factory=list, description="GMP 人员")
    additional_contacts: list[str] = Field(default_factory=list, description="其他联系人")
    is_production_workshop: bool = Field(False, description="是否生产车间")


class DepartmentContactUpdateRequest(BaseModel):
    """编辑部门联系人。部门名称作为唯一键不允许修改。"""

    dept_head_id: uuid.UUID | None = None
    production_head_id: uuid.UUID | None = None
    quality_head_id: uuid.UUID | None = None
    qa_reviewer_id: uuid.UUID | None = None
    qa_head_id: uuid.UUID | None = None
    qa_staff_ids: list[str] | None = None
    gmp_staff_ids: list[str] | None = None
    additional_contacts: list[str] | None = None
    is_production_workshop: bool | None = None


class MemberOption(BaseModel):
    """人员候选（配置页下拉）。"""

    value: str
    label: str
    description: str | None = None


class MemberOptionListData(BaseModel):
    """人员候选列表。"""

    items: list[MemberOption]


class NotifyEvents(BaseModel):
    """各类通知开关。"""

    flow: bool = Field(True, description="流转即时通知（提交 / 通过 / 退回 / 关闭）")
    ai_done: bool = Field(True, description="AI 分析完成转调查")
    overdue: bool = Field(True, description="超期提醒")
    weekly: bool = Field(True, description="每周生产与偏差状态确认提醒")
    gmp_group: bool = Field(True, description="生产车间未提交偏差群通知")


class NotifySettingsItem(BaseModel):
    """通知设置。"""

    enabled: bool = True
    chat_id: str = ""
    events: NotifyEvents = Field(default_factory=NotifyEvents)


class NotifySettingsUpdateRequest(BaseModel):
    """更新通知设置。"""

    enabled: bool = True
    chat_id: str = Field("", max_length=128, description="群聊 chat_id，留空表示不发群消息")
    events: NotifyEvents = Field(default_factory=NotifyEvents)


class WeeklyConfirmationItem(BaseModel):
    """部门某一周的确认记录（未确认时 confirmed=false）。"""

    department: str
    is_production_workshop: bool = False
    week_key: str
    confirmed: bool = False
    production_status: Literal["production", "stopped"] | None = None
    deviation_status: Literal["submitted", "unsubmitted"] | None = None
    confirmed_by_id: uuid.UUID | None = None
    confirmed_by_name: str | None = None
    confirmed_at: datetime | None = None


class WeeklyConfirmationListData(BaseModel):
    """周确认列表数据。"""

    week_key: str
    items: list[WeeklyConfirmationItem]
    confirmed_count: int
    total: int


class WeeklyConfirmationUpsertRequest(BaseModel):
    """提交 / 更新本部门本周确认。"""

    department: str = Field(min_length=1, max_length=255)
    production_status: Literal["production", "stopped"]
    deviation_status: Literal["submitted", "unsubmitted"]
    week_key: str = Field("", max_length=20, description="留空表示当前周")


class DepartmentContactListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DepartmentContactListData
    meta: dict[str, Any] | None = None


class DepartmentContactApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DepartmentContactItem
    meta: dict[str, Any] | None = None


class MemberOptionListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: MemberOptionListData
    meta: dict[str, Any] | None = None


class NotifySettingsApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: NotifySettingsItem
    meta: dict[str, Any] | None = None


class NotifyTargetItem(BaseModel):
    """通知接收人自检项（不含 open_id，避免泄露敏感标识）。"""

    user_id: uuid.UUID
    name: str
    role: str = Field(description="环节角色，如 部门负责人 / 所属QA")
    department: str
    bound: bool = Field(description="是否已绑定飞书标识（未绑定的收不到通知）")


class NotifyTestResultData(BaseModel):
    """发送测试通知的结果与链路自检信息。"""

    platform_ready: bool = Field(description="平台飞书应用凭证是否就绪")
    self_bound: bool = Field(description="当前登录账号是否绑定飞书标识")
    sent: bool = Field(description="测试卡片是否发送成功")
    error: str | None = Field(None, description="失败原因（成功时为 null）")
    message: str = Field(description="给用户看的一句话结论")
    contacts: list[NotifyTargetItem] = Field(default_factory=list, description="各环节处理人的绑定情况")


class NotifyTestResultApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: NotifyTestResultData
    meta: dict[str, Any] | None = None


class WeeklyConfirmationListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WeeklyConfirmationListData
    meta: dict[str, Any] | None = None


class WeeklyConfirmationApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WeeklyConfirmationItem
    meta: dict[str, Any] | None = None


class ConfigDeleteResultData(BaseModel):
    """删除结果。"""

    id: uuid.UUID
    deleted: bool = True


class ConfigDeleteResultApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: ConfigDeleteResultData
    meta: dict[str, Any] | None = None
