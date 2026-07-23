"""偏差提醒设置 Schemas"""

from pydantic import BaseModel, Field


class QAUserRequest(BaseModel):
    """QA人员请求"""

    open_id: str = Field(..., description="飞书OpenID")
    name: str = Field(..., description="姓名")
    department: str | None = Field(None, description="部门")


class LeaderRequest(BaseModel):
    """部门负责人请求"""

    open_id: str = Field(..., description="飞书OpenID")
    name: str = Field(..., description="姓名")
    department: str = Field(..., description="负责部门")


class ReminderRuleRequest(BaseModel):
    """提醒规则请求"""

    deviation_type: str | None = Field(None, description="偏差类型")
    urgency_level: str | None = Field(None, description="紧急等级")
    auto_reminder: bool = Field(True, description="是否自动提醒")
    reminder_time: str = Field("08:30", description="提醒时间")
    message_template: str | None = Field(None, description="消息模板")


class AutoTriggerRequest(BaseModel):
    """自动提醒触发请求"""

    trigger_type: str = Field(..., description="触发类型")
    trigger_condition: str | None = Field(None, description="触发条件")
    is_enabled: bool = Field(True, description="是否启用")
    notify_qa: bool = Field(True, description="通知QA")
    notify_leader: bool = Field(True, description="通知部门负责人")
    notify_reporter: bool = Field(False, description="通知填报人")
    custom_message: str | None = Field(None, description="自定义消息")


class MessageTemplateRequest(BaseModel):
    """消息模板请求"""

    template_type: str = Field(..., description="模板类型")
    template_name: str = Field(..., description="模板名称")
    title_template: str = Field(..., description="标题模板")
    content_template: str = Field(..., description="内容模板")
    is_default: bool = Field(False, description="是否默认模板")


class FeishuBotConfigRequest(BaseModel):
    """飞书机器人配置请求"""

    bot_name: str | None = Field(None, description="机器人名称")
    app_id: str = Field(..., description="App ID")
    app_secret: str = Field(..., description="App Secret")
    bot_token: str | None = Field(None, description="Bot Token")
    encrypt_key: str | None = Field(None, description="加密密钥")
    verification_token: str | None = Field(None, description="验证Token")


class FeishuUserRequest(BaseModel):
    """飞书用户查询请求"""

    mobile: str = Field(..., description="手机号")
    country_code: str = Field("86", description="国家码")
