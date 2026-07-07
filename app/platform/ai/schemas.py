"""AI platform request and response schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatAttachment(BaseModel):
    type: str = Field(..., description="附件类型: image")
    mime_type: str = Field(..., description="MIME 类型, 如 image/png")
    data: str = Field(..., description="Base64 编码的文件数据(不含 data URL 前缀)")


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息内容")
    attachments: list[ChatAttachment] | None = Field(
        None, description="附件列表(图片等)"
    )


class HrPageContext(BaseModel):
    page: str = Field(..., description="当前页面标识")
    filters: dict[str, str | None] | None = Field(
        None, description="当前筛选条件"
    )
    selected_ids: list[str] | None = Field(None, description="选中的行ID")
    data_summary: dict[str, str | int | None] | None = Field(
        None, description="数据摘要"
    )


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="对话历史")
    page_context: HrPageContext | None = Field(
        None, description="页面上下文"
    )


# ─── AI 出题相关 Schema ───

class ChoiceOption(BaseModel):
    label: str = Field(..., description="选项标签，如 A/B/C/D")
    text: str = Field(..., description="选项内容")


class ChoiceQuestion(BaseModel):
    number: int = Field(..., description="题号")
    question: str = Field(..., description="题目内容")
    options: list[ChoiceOption] = Field(default_factory=list, description="选项列表")
    answer: str | None = Field(None, description="答案")


class TrueFalseQuestion(BaseModel):
    number: int = Field(..., description="题号")
    question: str = Field(..., description="题目内容")
    answer: str | None = Field(None, description="答案")


class ExamGenerateResponse(BaseModel):
    choice_questions: list[ChoiceQuestion] = Field(
        default_factory=list, description="选择题列表"
    )
    true_false_questions: list[TrueFalseQuestion] = Field(
        default_factory=list, description="判断题列表"
    )


class ExamExportRequest(BaseModel):
    title: str = Field(..., description="试卷标题")
    examiner: str = Field(..., description="出卷人")
    exam_date: str = Field(..., description="出卷时间")
    assessment_date: str = Field(..., description="考核时间")
    choice_questions: list[ChoiceQuestion] = Field(
        default_factory=list, description="选择题列表"
    )
    true_false_questions: list[TrueFalseQuestion] = Field(
        default_factory=list, description="判断题列表"
    )


# ─── AI 查询规划相关 Schema ───

class SubQuery(BaseModel):
    """Single parallel-executable query within a plan step."""

    action: Literal["query", "count", "group_count", "get_distinct"] = Field(
        ..., description="查询操作类型"
    )
    description: str = Field(..., description="查询描述（用于生成上下文）")
    filters: dict[str, Any] = Field(default_factory=dict, description="过滤条件")
    group_by: str | None = Field(
        None, description="分组字段（group_count/get_distinct 用）"
    )
    limit: int | None = Field(None, description="列表查询条数上限（query 用）")


class PlanStep(BaseModel):
    """A single step in the query execution plan."""

    step: int = Field(..., description="步骤序号")
    mode: Literal["static", "dynamic"] = Field(
        ..., description="static=预定义查询, dynamic=运行时由AI生成"
    )
    description: str = Field(..., description="步骤意图描述")
    parallel_queries: list[SubQuery] | None = Field(
        None, description="static 模式下预填充的并行查询列表"
    )
    reasoning: str = Field(default="", description="为什么需要这一步")


class QueryPlan(BaseModel):
    """Generated execution plan for answering a user question."""

    needs_data: bool = Field(..., description="是否需要查询数据")
    steps: list[PlanStep] = Field(default_factory=list, description="执行步骤列表")
    reasoning: str = Field(default="", description="计划总体说明")
