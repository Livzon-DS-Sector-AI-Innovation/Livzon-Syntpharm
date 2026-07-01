"""AI platform request and response schemas."""

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
    filters: dict[str, str | None] | None = Field(None, description="当前筛选条件")
    selected_ids: list[str] | None = Field(None, description="选中的行ID")
    data_summary: dict[str, str | int | None] | None = Field(
        None, description="数据摘要"
    )


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="对话历史")
    page_context: HrPageContext | None = Field(None, description="页面上下文")


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
