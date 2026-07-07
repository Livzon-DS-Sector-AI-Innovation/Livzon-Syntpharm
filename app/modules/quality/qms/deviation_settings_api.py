"""偏差提醒设置 API"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.database import get_db_session
from app.modules.quality.qms.feishu_service import get_feishu_service

router = APIRouter(prefix="/deviation-settings", tags=["偏差提醒设置"])

# ============ 常量定义 ============

DEVIATION_TYPES = [
    {"value": "ipc_defect", "label": "过程控制（IPC）缺陷"},
    {"value": "foreign_object", "label": "外来异物（有形）"},
    {"value": "calibration_maintenance", "label": "校验/预防维修"},
    {"value": "mixup", "label": "混淆"},
    {"value": "material_quality_defect", "label": "物料质量缺陷"},
    {"value": "personnel_error", "label": "人员失误"},
    {"value": "oos_result", "label": "超标检验结果"},
    {"value": "documentation_defect", "label": "文件记录缺陷"},
    {"value": "equipment_failure", "label": "设备故障/过程中断"},
    {"value": "environment", "label": "环境"},
    {"value": "other", "label": "其它"},
]

URGENCY_LEVELS = [
    {"value": "normal", "label": "一般"},
    {"value": "important", "label": "重要"},
    {"value": "serious", "label": "严重"},
]


# ============ 请求模型 ============

class QAUserRequest(BaseModel):
    """QA人员请求"""
    open_id: str = Field(..., description="飞书OpenID")
    name: str = Field(..., description="姓名")
    department: Optional[str] = Field(None, description="部门")


class LeaderRequest(BaseModel):
    """部门负责人请求"""
    open_id: str = Field(..., description="飞书OpenID")
    name: str = Field(..., description="姓名")
    department: str = Field(..., description="负责部门")


class ReminderRuleRequest(BaseModel):
    """提醒规则请求"""
    deviation_type: Optional[str] = Field(None, description="偏差类型")
    urgency_level: Optional[str] = Field(None, description="紧急等级")
    auto_reminder: bool = Field(True, description="是否自动提醒")
    reminder_time: str = Field("08:30", description="提醒时间")
    message_template: Optional[str] = Field(None, description="消息模板")


class AutoTriggerRequest(BaseModel):
    """自动提醒触发请求"""
    trigger_type: str = Field(..., description="触发类型")
    trigger_condition: Optional[str] = Field(None, description="触发条件")
    is_enabled: bool = Field(True, description="是否启用")
    notify_qa: bool = Field(True, description="通知QA")
    notify_leader: bool = Field(True, description="通知部门负责人")
    notify_reporter: bool = Field(False, description="通知填报人")
    custom_message: Optional[str] = Field(None, description="自定义消息")


class MessageTemplateRequest(BaseModel):
    """消息模板请求"""
    template_type: str = Field(..., description="模板类型")
    template_name: str = Field(..., description="模板名称")
    title_template: str = Field(..., description="标题模板")
    content_template: str = Field(..., description="内容模板")
    is_default: bool = Field(False, description="是否默认模板")


class FeishuBotConfigRequest(BaseModel):
    """飞书机器人配置请求"""
    bot_name: Optional[str] = Field(None, description="机器人名称")
    app_id: str = Field(..., description="App ID")
    app_secret: str = Field(..., description="App Secret")
    bot_token: Optional[str] = Field(None, description="Bot Token")
    encrypt_key: Optional[str] = Field(None, description="加密密钥")
    verification_token: Optional[str] = Field(None, description="验证Token")


# ============ API 接口 ============

# ----- QA人员管理 -----

@router.get("/qa-users", summary="获取QA人员列表")
async def get_qa_users(session: AsyncSession = Depends(get_db_session)):
    """获取所有QA人员配置"""
    result = await session.execute(
        text("""
            SELECT id, open_id, name, department, is_active, created_at, updated_at
            FROM qms.qms_deviation_qa_config
            WHERE is_deleted = FALSE
            ORDER BY created_at DESC
        """)
    )
    rows = result.fetchall()
    columns = result.keys()
    
    items = []
    for row in rows:
        item = dict(zip(columns, row))
        item['created_at'] = str(item['created_at']) if item['created_at'] else None
        item['updated_at'] = str(item['updated_at']) if item['updated_at'] else None
        items.append(item)
    
    return {
        "code": 200,
        "message": "success",
        "data": items
    }


@router.post("/qa-users", summary="添加QA人员")
async def add_qa_user(
    request: QAUserRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """添加QA人员配置"""
    # 检查是否已存在
    check = await session.execute(
        text("SELECT id FROM qms.qms_deviation_qa_config WHERE open_id = :open_id AND is_deleted = FALSE"),
        {"open_id": request.open_id}
    )
    if check.fetchone():
        return {"code": 400, "message": "该QA人员已存在", "data": None}
    
    id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation_qa_config (id, open_id, name, department, created_at)
            VALUES (:id, :open_id, :name, :department, :created_at)
        """),
        {
            "id": id,
            "open_id": request.open_id,
            "name": request.name,
            "department": request.department,
            "created_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "添加成功", "data": {"id": id}}


@router.put("/qa-users/{id}", summary="更新QA人员")
async def update_qa_user(
    id: str,
    request: QAUserRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """更新QA人员配置"""
    await session.execute(
        text("""
            UPDATE qms.qms_deviation_qa_config 
            SET open_id = :open_id, name = :name, department = :department, updated_at = :updated_at
            WHERE id = :id AND is_deleted = FALSE
        """),
        {
            "id": id,
            "open_id": request.open_id,
            "name": request.name,
            "department": request.department,
            "updated_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "更新成功", "data": None}


@router.delete("/qa-users/{id}", summary="删除QA人员")
async def delete_qa_user(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """删除QA人员（软删除）"""
    await session.execute(
        text("UPDATE qms.qms_deviation_qa_config SET is_deleted = TRUE WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "删除成功", "data": None}


@router.put("/qa-users/{id}/toggle", summary="启用/禁用QA人员")
async def toggle_qa_user(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """切换QA人员启用状态"""
    await session.execute(
        text("UPDATE qms.qms_deviation_qa_config SET is_active = NOT is_active WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "状态切换成功", "data": None}


# ----- 部门负责人管理 -----

@router.get("/leaders", summary="获取部门负责人列表")
async def get_leaders(session: AsyncSession = Depends(get_db_session)):
    """获取所有部门负责人配置"""
    result = await session.execute(
        text("""
            SELECT id, open_id, name, department, is_active, created_at, updated_at
            FROM qms.qms_deviation_leader_config
            WHERE is_deleted = FALSE
            ORDER BY department, created_at DESC
        """)
    )
    rows = result.fetchall()
    columns = result.keys()
    
    items = []
    for row in rows:
        item = dict(zip(columns, row))
        item['created_at'] = str(item['created_at']) if item['created_at'] else None
        item['updated_at'] = str(item['updated_at']) if item['updated_at'] else None
        items.append(item)
    
    return {
        "code": 200,
        "message": "success",
        "data": items
    }


@router.post("/leaders", summary="添加部门负责人")
async def add_leader(
    request: LeaderRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """添加部门负责人配置"""
    # 检查是否已存在
    check = await session.execute(
        text("SELECT id FROM qms.qms_deviation_leader_config WHERE open_id = :open_id AND is_deleted = FALSE"),
        {"open_id": request.open_id}
    )
    if check.fetchone():
        return {"code": 400, "message": "该部门负责人已存在", "data": None}
    
    id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation_leader_config (id, open_id, name, department, created_at)
            VALUES (:id, :open_id, :name, :department, :created_at)
        """),
        {
            "id": id,
            "open_id": request.open_id,
            "name": request.name,
            "department": request.department,
            "created_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "添加成功", "data": {"id": id}}


@router.put("/leaders/{id}", summary="更新部门负责人")
async def update_leader(
    id: str,
    request: LeaderRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """更新部门负责人配置"""
    await session.execute(
        text("""
            UPDATE qms.qms_deviation_leader_config 
            SET open_id = :open_id, name = :name, department = :department, updated_at = :updated_at
            WHERE id = :id AND is_deleted = FALSE
        """),
        {
            "id": id,
            "open_id": request.open_id,
            "name": request.name,
            "department": request.department,
            "updated_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "更新成功", "data": None}


@router.delete("/leaders/{id}", summary="删除部门负责人")
async def delete_leader(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """删除部门负责人（软删除）"""
    await session.execute(
        text("UPDATE qms.qms_deviation_leader_config SET is_deleted = TRUE WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "删除成功", "data": None}


@router.put("/leaders/{id}/toggle", summary="启用/禁用部门负责人")
async def toggle_leader(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """切换部门负责人启用状态"""
    await session.execute(
        text("UPDATE qms.qms_deviation_leader_config SET is_active = NOT is_active WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "状态切换成功", "data": None}


# ----- 提醒规则管理 -----

@router.get("/rules", summary="获取提醒规则列表")
async def get_rules(session: AsyncSession = Depends(get_db_session)):
    """获取所有提醒规则配置"""
    result = await session.execute(
        text("""
            SELECT id, deviation_type, urgency_level, auto_reminder, reminder_time, 
                   message_template, is_active, created_at, updated_at
            FROM qms.qms_deviation_reminder_rules
            WHERE is_deleted = FALSE
            ORDER BY deviation_type, urgency_level
        """)
    )
    rows = result.fetchall()
    columns = result.keys()
    
    items = []
    for row in rows:
        item = dict(zip(columns, row))
        item['created_at'] = str(item['created_at']) if item['created_at'] else None
        item['updated_at'] = str(item['updated_at']) if item['updated_at'] else None
        items.append(item)
    
    return {
        "code": 200,
        "message": "success",
        "data": items
    }


@router.post("/rules", summary="添加提醒规则")
async def add_rule(
    request: ReminderRuleRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """添加提醒规则配置"""
    id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation_reminder_rules 
            (id, deviation_type, urgency_level, auto_reminder, reminder_time, message_template, created_at)
            VALUES (:id, :deviation_type, :urgency_level, :auto_reminder, :reminder_time, :message_template, :created_at)
        """),
        {
            "id": id,
            "deviation_type": request.deviation_type,
            "urgency_level": request.urgency_level,
            "auto_reminder": request.auto_reminder,
            "reminder_time": request.reminder_time,
            "message_template": request.message_template,
            "created_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "添加成功", "data": {"id": id}}


@router.put("/rules/{id}", summary="更新提醒规则")
async def update_rule(
    id: str,
    request: ReminderRuleRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """更新提醒规则配置"""
    await session.execute(
        text("""
            UPDATE qms.qms_deviation_reminder_rules 
            SET deviation_type = :deviation_type, urgency_level = :urgency_level,
                auto_reminder = :auto_reminder, reminder_time = :reminder_time, 
                message_template = :message_template, updated_at = :updated_at
            WHERE id = :id AND is_deleted = FALSE
        """),
        {
            "id": id,
            "deviation_type": request.deviation_type,
            "urgency_level": request.urgency_level,
            "auto_reminder": request.auto_reminder,
            "reminder_time": request.reminder_time,
            "message_template": request.message_template,
            "updated_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "更新成功", "data": None}


@router.delete("/rules/{id}", summary="删除提醒规则")
async def delete_rule(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """删除提醒规则（软删除）"""
    await session.execute(
        text("UPDATE qms.qms_deviation_reminder_rules SET is_deleted = TRUE WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "删除成功", "data": None}


@router.put("/rules/{id}/toggle", summary="启用/禁用提醒规则")
async def toggle_rule(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """切换提醒规则启用状态"""
    await session.execute(
        text("UPDATE qms.qms_deviation_reminder_rules SET is_active = NOT is_active WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "状态切换成功", "data": None}


# ----- 自动提醒触发管理 -----

TRIGGER_TYPES = [
    {"value": "report_uploaded", "label": "偏差报告上传后"},
    {"value": "basic_completed", "label": "基础信息提交后"},
    {"value": "detail_completed", "label": "偏差详情提交后"},
    {"value": "completed", "label": "偏差完成"},
    {"value": "capa_reminder", "label": "CAPA到期提醒"},
    {"value": "overdue_warning", "label": "逾期预警"},
]


@router.get("/auto-triggers", summary="获取自动提醒触发列表")
async def get_auto_triggers(session: AsyncSession = Depends(get_db_session)):
    """获取所有自动提醒触发配置"""
    result = await session.execute(
        text("""
            SELECT id, trigger_type, trigger_condition, is_enabled, 
                   notify_qa, notify_leader, notify_reporter, custom_message,
                   created_at, updated_at
            FROM qms.qms_deviation_auto_trigger
            WHERE is_deleted = FALSE
            ORDER BY created_at DESC
        """)
    )
    rows = result.fetchall()
    columns = result.keys()
    
    items = []
    for row in rows:
        item = dict(zip(columns, row))
        item['created_at'] = str(item['created_at']) if item['created_at'] else None
        item['updated_at'] = str(item['updated_at']) if item['updated_at'] else None
        items.append(item)
    
    return {
        "code": 200,
        "message": "success",
        "data": items
    }


@router.post("/auto-triggers", summary="添加自动提醒触发")
async def add_auto_trigger(
    request: AutoTriggerRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """添加自动提醒触发配置"""
    # 检查是否已存在相同触发类型
    check = await session.execute(
        text("SELECT id FROM qms.qms_deviation_auto_trigger WHERE trigger_type = :trigger_type AND is_deleted = FALSE"),
        {"trigger_type": request.trigger_type}
    )
    if check.fetchone():
        return {"code": 400, "message": "该触发类型已存在", "data": None}
    
    id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation_auto_trigger 
            (id, trigger_type, trigger_condition, is_enabled, notify_qa, notify_leader, notify_reporter, custom_message, created_at)
            VALUES (:id, :trigger_type, :trigger_condition, :is_enabled, :notify_qa, :notify_leader, :notify_reporter, :custom_message, :created_at)
        """),
        {
            "id": id,
            "trigger_type": request.trigger_type,
            "trigger_condition": request.trigger_condition,
            "is_enabled": request.is_enabled,
            "notify_qa": request.notify_qa,
            "notify_leader": request.notify_leader,
            "notify_reporter": request.notify_reporter,
            "custom_message": request.custom_message,
            "created_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "添加成功", "data": {"id": id}}


@router.put("/auto-triggers/{id}", summary="更新自动提醒触发")
async def update_auto_trigger(
    id: str,
    request: AutoTriggerRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """更新自动提醒触发配置"""
    await session.execute(
        text("""
            UPDATE qms.qms_deviation_auto_trigger 
            SET trigger_type = :trigger_type, trigger_condition = :trigger_condition,
                is_enabled = :is_enabled, notify_qa = :notify_qa, notify_leader = :notify_leader,
                notify_reporter = :notify_reporter, custom_message = :custom_message, updated_at = :updated_at
            WHERE id = :id AND is_deleted = FALSE
        """),
        {
            "id": id,
            "trigger_type": request.trigger_type,
            "trigger_condition": request.trigger_condition,
            "is_enabled": request.is_enabled,
            "notify_qa": request.notify_qa,
            "notify_leader": request.notify_leader,
            "notify_reporter": request.notify_reporter,
            "custom_message": request.custom_message,
            "updated_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "更新成功", "data": None}


@router.delete("/auto-triggers/{id}", summary="删除自动提醒触发")
async def delete_auto_trigger(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """删除自动提醒触发（软删除）"""
    await session.execute(
        text("UPDATE qms.qms_deviation_auto_trigger SET is_deleted = TRUE WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "删除成功", "data": None}


@router.put("/auto-triggers/{id}/toggle", summary="启用/禁用自动提醒触发")
async def toggle_auto_trigger(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """切换自动提醒触发启用状态"""
    await session.execute(
        text("UPDATE qms.qms_deviation_auto_trigger SET is_enabled = NOT is_enabled WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "状态切换成功", "data": None}


# ----- 消息模板管理 -----

TEMPLATE_TYPES = [
    {"value": "new_deviation", "label": "新建偏差通知"},
    {"value": "basic_completed", "label": "基础信息完成通知"},
    {"value": "detail_completed", "label": "偏差详情完成通知"},
    {"value": "completed", "label": "偏差完成通知"},
    {"value": "capa_reminder", "label": "CAPA到期提醒"},
    {"value": "overdue_warning", "label": "逾期预警"},
]


@router.get("/message-templates", summary="获取消息模板列表")
async def get_message_templates(session: AsyncSession = Depends(get_db_session)):
    """获取所有消息模板配置"""
    result = await session.execute(
        text("""
            SELECT id, template_type, template_name, title_template, content_template,
                   is_default, is_active, created_at, updated_at
            FROM qms.qms_deviation_message_template
            WHERE is_deleted = FALSE
            ORDER BY template_type, created_at DESC
        """)
    )
    rows = result.fetchall()
    columns = result.keys()
    
    items = []
    for row in rows:
        item = dict(zip(columns, row))
        item['created_at'] = str(item['created_at']) if item['created_at'] else None
        item['updated_at'] = str(item['updated_at']) if item['updated_at'] else None
        items.append(item)
    
    return {
        "code": 200,
        "message": "success",
        "data": items
    }


@router.post("/message-templates", summary="添加消息模板")
async def add_message_template(
    request: MessageTemplateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """添加消息模板配置"""
    # 如果设为默认模板，先取消其他默认
    if request.is_default:
        await session.execute(
            text("UPDATE qms.qms_deviation_message_template SET is_default = FALSE WHERE template_type = :template_type"),
            {"template_type": request.template_type}
        )
    
    id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation_message_template 
            (id, template_type, template_name, title_template, content_template, is_default, is_active, created_at)
            VALUES (:id, :template_type, :template_name, :title_template, :content_template, :is_default, TRUE, :created_at)
        """),
        {
            "id": id,
            "template_type": request.template_type,
            "template_name": request.template_name,
            "title_template": request.title_template,
            "content_template": request.content_template,
            "is_default": request.is_default,
            "created_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "添加成功", "data": {"id": id}}


@router.put("/message-templates/{id}", summary="更新消息模板")
async def update_message_template(
    id: str,
    request: MessageTemplateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """更新消息模板配置"""
    # 如果设为默认模板，先取消其他默认
    if request.is_default:
        await session.execute(
            text("UPDATE qms.qms_deviation_message_template SET is_default = FALSE WHERE template_type = :template_type AND id != :id"),
            {"template_type": request.template_type, "id": id}
        )
    
    await session.execute(
        text("""
            UPDATE qms.qms_deviation_message_template 
            SET template_type = :template_type, template_name = :template_name,
                title_template = :title_template, content_template = :content_template,
                is_default = :is_default, updated_at = :updated_at
            WHERE id = :id AND is_deleted = FALSE
        """),
        {
            "id": id,
            "template_type": request.template_type,
            "template_name": request.template_name,
            "title_template": request.title_template,
            "content_template": request.content_template,
            "is_default": request.is_default,
            "updated_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "更新成功", "data": None}


@router.delete("/message-templates/{id}", summary="删除消息模板")
async def delete_message_template(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """删除消息模板（软删除）"""
    await session.execute(
        text("UPDATE qms.qms_deviation_message_template SET is_deleted = TRUE WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "删除成功", "data": None}


@router.put("/message-templates/{id}/toggle", summary="启用/禁用消息模板")
async def toggle_message_template(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """切换消息模板启用状态"""
    await session.execute(
        text("UPDATE qms.qms_deviation_message_template SET is_active = NOT is_active WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "状态切换成功", "data": None}


@router.put("/message-templates/{id}/set-default", summary="设为默认模板")
async def set_default_template(
    id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """将模板设为默认"""
    # 先获取当前模板的template_type
    result = await session.execute(
        text("SELECT template_type FROM qms.qms_deviation_message_template WHERE id = :id"),
        {"id": id}
    )
    row = result.fetchone()
    if not row:
        return {"code": 404, "message": "模板不存在", "data": None}
    
    template_type = row[0]
    
    # 取消同类型的其他默认
    await session.execute(
        text("UPDATE qms.qms_deviation_message_template SET is_default = FALSE WHERE template_type = :template_type"),
        {"template_type": template_type}
    )
    
    # 设置当前为默认
    await session.execute(
        text("UPDATE qms.qms_deviation_message_template SET is_default = TRUE WHERE id = :id"),
        {"id": id}
    )
    await session.commit()
    
    return {"code": 200, "message": "设置成功", "data": None}


# ----- 飞书机器人配置 -----

@router.get("/feishu-bot", summary="获取飞书机器人配置")
async def get_feishu_bot_config(session: AsyncSession = Depends(get_db_session)):
    """获取飞书机器人配置（只返回一条）"""
    result = await session.execute(
        text("""
            SELECT id, bot_name, app_id, app_secret, bot_token, encrypt_key, 
                   verification_token, is_enabled, created_at, updated_at
            FROM qms.qms_deviation_feishu_bot_config
            WHERE is_deleted = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        """)
    )
    row = result.fetchone()
    columns = result.keys()
    
    if not row:
        return {"code": 200, "message": "success", "data": None}
    
    item = dict(zip(columns, row))
    item['created_at'] = str(item['created_at']) if item['created_at'] else None
    item['updated_at'] = str(item['updated_at']) if item['updated_at'] else None
    # 隐藏app_secret
    if item.get('app_secret'):
        item['app_secret'] = '**********'
    
    return {"code": 200, "message": "success", "data": item}


@router.post("/feishu-bot", summary="创建飞书机器人配置")
async def create_feishu_bot_config(
    request: FeishuBotConfigRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """创建飞书机器人配置（只允许一条）"""
    # 检查是否已存在
    check = await session.execute(
        text("SELECT id FROM qms.qms_deviation_feishu_bot_config WHERE is_deleted = FALSE LIMIT 1")
    )
    if check.fetchone():
        return {"code": 400, "message": "已存在机器人配置，如需修改请使用更新接口", "data": None}
    
    id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation_feishu_bot_config 
            (id, bot_name, app_id, app_secret, bot_token, encrypt_key, verification_token, created_at)
            VALUES (:id, :bot_name, :app_id, :app_secret, :bot_token, :encrypt_key, :verification_token, :created_at)
        """),
        {
            "id": id,
            "bot_name": request.bot_name,
            "app_id": request.app_id,
            "app_secret": request.app_secret,
            "bot_token": request.bot_token,
            "encrypt_key": request.encrypt_key,
            "verification_token": request.verification_token,
            "created_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "创建成功", "data": {"id": id}}


@router.put("/feishu-bot", summary="更新飞书机器人配置")
async def update_feishu_bot_config(
    request: FeishuBotConfigRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """更新飞书机器人配置"""
    # 获取当前配置
    result = await session.execute(
        text("SELECT id, app_secret FROM qms.qms_deviation_feishu_bot_config WHERE is_deleted = FALSE LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        return {"code": 404, "message": "机器人配置不存在", "data": None}
    
    current_id = row[0]
    current_secret = row[1]
    
    # 如果新密码是**********，保持原密码
    app_secret = request.app_secret
    if app_secret == '**********' or not app_secret:
        app_secret = current_secret
    
    await session.execute(
        text("""
            UPDATE qms.qms_deviation_feishu_bot_config 
            SET bot_name = :bot_name, app_id = :app_id, app_secret = :app_secret,
                bot_token = :bot_token, encrypt_key = :encrypt_key, 
                verification_token = :verification_token, updated_at = :updated_at
            WHERE id = :id AND is_deleted = FALSE
        """),
        {
            "id": current_id,
            "bot_name": request.bot_name,
            "app_id": request.app_id,
            "app_secret": app_secret,
            "bot_token": request.bot_token,
            "encrypt_key": request.encrypt_key,
            "verification_token": request.verification_token,
            "updated_at": datetime.now()
        }
    )
    await session.commit()
    
    return {"code": 200, "message": "更新成功", "data": None}


@router.put("/feishu-bot/toggle", summary="启用/禁用机器人")
async def toggle_feishu_bot(
    session: AsyncSession = Depends(get_db_session),
):
    """切换机器人启用状态"""
    result = await session.execute(
        text("SELECT id FROM qms.qms_deviation_feishu_bot_config WHERE is_deleted = FALSE LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        return {"code": 404, "message": "机器人配置不存在", "data": None}
    
    await session.execute(
        text("UPDATE qms.qms_deviation_feishu_bot_config SET is_enabled = NOT is_enabled WHERE is_deleted = FALSE"),
    )
    await session.commit()
    
    return {"code": 200, "message": "状态切换成功", "data": None}


@router.delete("/feishu-bot", summary="删除飞书机器人配置")
async def delete_feishu_bot_config(
    session: AsyncSession = Depends(get_db_session),
):
    """删除飞书机器人配置（软删除）"""
    result = await session.execute(
        text("SELECT id FROM qms.qms_deviation_feishu_bot_config WHERE is_deleted = FALSE LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        return {"code": 404, "message": "机器人配置不存在", "data": None}
    
    await session.execute(
        text("UPDATE qms.qms_deviation_feishu_bot_config SET is_deleted = TRUE WHERE is_deleted = FALSE"),
    )
    await session.commit()
    
    return {"code": 200, "message": "删除成功", "data": None}


# ----- 选项列表 -----

@router.get("/options", summary="获取选项列表")
async def get_options():
    """获取偏差类型、紧急等级等选项"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "deviation_types": DEVIATION_TYPES,
            "urgency_levels": URGENCY_LEVELS,
            "trigger_types": TRIGGER_TYPES,
            "template_types": TEMPLATE_TYPES,
            "departments": [
                {"value": "生产部", "label": "生产部"},
                {"value": "质量部", "label": "质量部"},
                {"value": "工程部", "label": "工程部"},
                {"value": "仓储部", "label": "仓储部"},
                {"value": "采购部", "label": "采购部"},
                {"value": "研发部", "label": "研发部"},
            ]
        }
    }


# ----- 飞书用户查询 -----

class FeishuUserRequest(BaseModel):
    """飞书用户查询请求"""
    mobile: str = Field(..., description="手机号")
    country_code: str = Field("86", description="国家码")


@router.get("/feishu-user/by-mobile", summary="根据手机号查询飞书用户")
async def get_feishu_user_by_mobile(
    mobile: str = Query(..., description="手机号"),
    country_code: str = Query("86", description="国家码"),
):
    """根据手机号查询飞书用户信息，返回open_id和姓名"""
    feishu_service = get_feishu_service()
    user_info = await feishu_service.get_user_by_mobile(mobile, country_code)
    
    if user_info:
        return {
            "code": 200,
            "message": "success",
            "data": user_info
        }
    else:
        return {
            "code": 404,
            "message": "未找到对应用户，请确认手机号是否正确或用户是否在飞书通讯录中",
            "data": None
        }


@router.post("/reminder/trigger", summary="手动触发偏差提醒")
async def trigger_deviation_reminder(session: AsyncSession = Depends(get_db_session)):
    """手动触发偏差填报人提醒检查并发送飞书消息"""
    from app.modules.quality.qms.deviation_reporter_reminder_service import DeviationReporterReminderService
    service = DeviationReporterReminderService(session)
    result = await service.check_and_remind()
    return {
        "code": 200,
        "message": "提醒已触发",
        "data": result,
    }