"""偏差流程管理 API

提供偏差的创建、编辑、提交、查询等完整流程管理功能。
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional
from dateutil import parser as date_parser

from fastapi import APIRouter, Depends, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.database import get_db_session
from app.core.config import get_settings
from app.platform.notification.feishu_client_config import FeishuClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deviation-flow", tags=["偏差流程管理"])

settings = get_settings()

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

STATUS_OPTIONS = [
    {"value": "draft", "label": "草稿"},
    {"value": "basic_completed", "label": "基础完成"},
    {"value": "detail_completed", "label": "详情完成"},
    {"value": "completed", "label": "已完成"},
]


def get_type_label(deviation_type: str) -> str:
    """获取偏差类型标签"""
    for t in DEVIATION_TYPES:
        if t["value"] == deviation_type:
            return t["label"]
    return deviation_type or "未知"


def get_level_label(urgency_level: str) -> str:
    """获取紧急等级标签"""
    for l in URGENCY_LEVELS:
        if l["value"] == urgency_level:
            return l["label"]
    return urgency_level or "未知"


async def get_template_content(session: AsyncSession, template_type: str, target_status: str) -> Optional[dict]:
    """获取模板内容并进行变量替换"""
    # 模板类型映射（备用查询）
    template_type_map = {
        "reporter_notification": ["reporter_notification", "reporter_reminder"],
        "qa_notification": ["qa_notification", "new_deviation"],
        "leader_notification": ["leader_notification"],
    }
    
    # 获取要查询的模板类型列表
    types_to_try = template_type_map.get(template_type, [template_type])
    
    for t in types_to_try:
        result = await session.execute(
            text("""
                SELECT title_template, content_template 
                FROM qms.qms_deviation_message_template 
                WHERE template_type = :template_type 
                  AND is_deleted = FALSE 
                  AND is_active = TRUE
                ORDER BY is_default DESC
                LIMIT 1
            """),
            {"template_type": t}
        )
        row = result.fetchone()
        if row:
            return {
                "title_template": row[0] or "",
                "content_template": row[1] or "",
            }
    
    return None


def render_template(template: str, variables: dict) -> str:
    """渲染模板，替换变量占位符"""
    if not template:
        return ""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
        result = result.replace(f"{{{key}}}", str(value))
    return result


# ============ 请求模型 ============

class DeviationCreateRequest(BaseModel):
    """创建偏差请求"""
    theme: Optional[str] = Field(None, description="偏差主题")
    occurred_date: Optional[str] = Field(None, description="偏差发生日期")
    discovered_date: Optional[str] = Field(None, description="发现日期")
    responsible_department: Optional[str] = Field(None, description="责任部门")
    occurred_area: Optional[str] = Field(None, description="发生区域/车间")
    deviation_type: Optional[str] = Field(None, description="偏差类型")
    urgency_level: Optional[str] = Field(None, description="紧急等级")
    
    # 详情信息
    product_name: Optional[str] = Field(None, description="涉及产品/物料")
    batch_no: Optional[str] = Field(None, description="批次号")
    equipment: Optional[str] = Field(None, description="涉及设备/仪器")
    standard_based_on: Optional[str] = Field(None, description="偏离标准依据")
    deviation_description: Optional[str] = Field(None, description="偏差完整经过描述")
    risk_assessment: Optional[str] = Field(None, description="初步风险影响评估")
    
    # 辅助信息
    temp_measures: Optional[str] = Field(None, description="临时处置措施")
    related_deviation_no: Optional[str] = Field(None, description="关联偏差单号")
    related_capa: Optional[str] = Field(None, description="关联CAPA")
    remarks: Optional[str] = Field(None, description="备注说明")
    
    # 提醒配置
    qa_feishu_open_id: Optional[str] = Field(None, description="QA人员飞书OpenID")
    qa_feishu_name: Optional[str] = Field(None, description="QA人员姓名")
    dept_leader_feishu_open_id: Optional[str] = Field(None, description="部门负责人飞书OpenID")
    dept_leader_feishu_name: Optional[str] = Field(None, description="部门负责人姓名")
    
    # 填报人信息
    reporter: Optional[str] = Field(None, description="填报人")
    reporter_department: Optional[str] = Field(None, description="填报部门")
    reporter_feishu_open_id: Optional[str] = Field(None, description="填报人飞书OpenID")


class DeviationUpdateRequest(BaseModel):
    """更新偏差请求"""
    theme: Optional[str] = None
    occurred_date: Optional[str] = None
    discovered_date: Optional[str] = None
    responsible_department: Optional[str] = None
    occurred_area: Optional[str] = None
    deviation_type: Optional[str] = None
    urgency_level: Optional[str] = None
    
    product_name: Optional[str] = None
    batch_no: Optional[str] = None
    equipment: Optional[str] = None
    standard_based_on: Optional[str] = None
    deviation_description: Optional[str] = None
    risk_assessment: Optional[str] = None
    
    temp_measures: Optional[str] = None
    related_deviation_no: Optional[str] = None
    related_capa: Optional[str] = None
    remarks: Optional[str] = None
    
    qa_feishu_open_id: Optional[str] = None
    qa_feishu_name: Optional[str] = None
    dept_leader_feishu_open_id: Optional[str] = None
    dept_leader_feishu_name: Optional[str] = None
    reporter: Optional[str] = None
    reporter_department: Optional[str] = None
    reporter_feishu_open_id: Optional[str] = None


class DeviationSubmitRequest(BaseModel):
    """提交偏差请求"""
    deviation_id: str = Field(..., description="偏差ID")
    target_status: str = Field(..., description="目标状态: basic_completed/detail_completed/completed")


class AttachmentResponse(BaseModel):
    """附件响应"""
    id: str
    deviation_id: str
    file_name: str
    file_path: str
    file_type: Optional[str]
    is_report: bool
    file_size: Optional[int]
    uploaded_by: Optional[str]
    uploaded_at: str


class DeviationResponse(BaseModel):
    """偏差响应"""
    id: str
    deviation_no: str
    theme: str
    occurred_date: str
    discovered_date: str
    responsible_department: Optional[str]
    occurred_area: Optional[str]
    deviation_type: Optional[str]
    deviation_type_label: Optional[str]
    urgency_level: Optional[str]
    urgency_level_label: Optional[str]
    status: str
    status_label: str
    
    product_name: Optional[str]
    batch_no: Optional[str]
    equipment: Optional[str]
    standard_based_on: Optional[str]
    deviation_description: Optional[str]
    risk_assessment: Optional[str]
    
    temp_measures: Optional[str]
    related_deviation_no: Optional[str]
    related_capa: Optional[str]
    remarks: Optional[str]
    
    qa_feishu_open_id: Optional[str]
    qa_feishu_name: Optional[str]
    dept_leader_feishu_open_id: Optional[str]
    dept_leader_feishu_name: Optional[str]
    
    reporter: Optional[str]
    reporter_department: Optional[str]
    report_time: Optional[str]
    
    attachments: list[AttachmentResponse]
    
    created_at: str
    updated_at: Optional[str]


# ============ 辅助函数 ============

def get_status_label(value: str) -> str:
    for s in STATUS_OPTIONS:
        if s["value"] == value:
            return s["label"]
    return value or ""


async def generate_deviation_no(session: AsyncSession) -> str:
    """生成偏差编号：年份+月份+流水号"""
    now = datetime.now()
    year_month = now.strftime("%Y%m")
    
    # 查询当月最大流水号
    query = text("""
        SELECT deviation_no FROM qms.qms_deviation 
        WHERE deviation_no LIKE :prefix
        ORDER BY deviation_no DESC
        LIMIT 1
    """)
    result = await session.execute(query, {"prefix": f"%{year_month}%"})
    row = result.fetchone()
    
    if row:
        last_no = row[0]
        # 提取流水号
        try:
            seq = int(last_no[-4:]) + 1
        except:
            seq = 1
    else:
        seq = 1
    
    return f"{year_month}{seq:04d}"


async def add_operation_log(
    session: AsyncSession,
    deviation_id: str,
    action: str,
    operator: str,
    operator_department: str,
    content: str = None
):
    """添加操作日志"""
    log_id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation_log 
            (id, deviation_id, action, operator, operator_department, content, created_at)
            VALUES (:id, :deviation_id, :action, :operator, :operator_department, :content, :created_at)
        """),
        {
            "id": log_id,
            "deviation_id": deviation_id,
            "action": action,
            "operator": operator,
            "operator_department": operator_department,
            "content": content,
            "created_at": datetime.now()
        }
    )


async def send_feishu_notification(
    feishu_app_id: str,
    feishu_app_secret: str,
    chat_id: str,
    deviation_no: str,
    theme: str,
    deviation_type: str,
    urgency_level: str,
    recipient_name: str,
    recipient_type: str,
    reporter_name: str = None
):
    """发送飞书通知"""
    if not feishu_app_id or not feishu_app_secret or not chat_id:
        return False
    
    try:
        client = FeishuClient(feishu_app_id, feishu_app_secret)
        
        if recipient_type == "qa":
            title = "📋 新偏差通知 - 需要您跟进管控"
            content = f"""**新偏差单已提交，请及时跟进管控！**

**偏差编号：** {deviation_no}
**偏差主题：** {theme}
**偏差类型：** {get_type_label(deviation_type)}
**紧急等级：** {get_level_label(urgency_level)}

请登录系统查看详情并跟进管控措施。"""
        else:
            title = "📢 偏差通知 - 请尽快上传报告"
            content = f"""**您提交的偏差单已成功提交！**

**偏差编号：** {deviation_no}
**偏差主题：** {theme}

请尽快上传正式的偏差调查报告和整改报告。"""

        card_content = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content,
                    },
                }
            ],
        }
        
        await client.send_card_message(
            receive_id_type="chat_id",
            receive_id=chat_id,
            card_content=card_content,
        )
        return True
    except Exception as e:
        print(f"发送飞书通知失败: {e}")
        return False


# ============ API 接口 ============

@router.get("/options", summary="获取选项列表")
async def get_options():
    """获取偏差类型、紧急等级、状态等选项"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "deviation_types": DEVIATION_TYPES,
            "urgency_levels": URGENCY_LEVELS,
            "status_options": STATUS_OPTIONS,
        }
    }


@router.post("", summary="创建偏差")
async def create_deviation(
    request: DeviationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """创建新偏差（草稿状态）"""
    deviation_id = str(uuid.uuid4())
    deviation_no = await generate_deviation_no(session)
    now = datetime.now()
    
    # 转换日期字符串为 datetime 对象
    def parse_date(date_str):
        if date_str:
            try:
                return date_parser.parse(date_str)
            except:
                return None
        return None
    
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation (
                id, deviation_no, theme, occurred_date, discovered_date,
                responsible_department, occurred_area, deviation_type, urgency_level, status,
                product_name, batch_no, equipment, standard_based_on, deviation_description, risk_assessment,
                temp_measures, related_deviation_no, related_capa, remarks,
                qa_feishu_open_id, qa_feishu_name, dept_leader_feishu_open_id, dept_leader_feishu_name,
                reporter, reporter_department, reporter_feishu_open_id, report_time,
                created_at
            ) VALUES (
                :id, :deviation_no, :theme, :occurred_date, :discovered_date,
                :responsible_department, :occurred_area, :deviation_type, :urgency_level, 'draft',
                :product_name, :batch_no, :equipment, :standard_based_on, :deviation_description, :risk_assessment,
                :temp_measures, :related_deviation_no, :related_capa, :remarks,
                :qa_feishu_open_id, :qa_feishu_name, :dept_leader_feishu_open_id, :dept_leader_feishu_name,
                :reporter, :reporter_department, :reporter_feishu_open_id, :report_time,
                :created_at
            )
        """),
        {
            "id": deviation_id,
            "deviation_no": deviation_no,
            "theme": request.theme,
            "occurred_date": parse_date(request.occurred_date),
            "discovered_date": parse_date(request.discovered_date),
            "responsible_department": request.responsible_department,
            "occurred_area": request.occurred_area,
            "deviation_type": request.deviation_type,
            "urgency_level": request.urgency_level,
            "product_name": request.product_name,
            "batch_no": request.batch_no,
            "equipment": request.equipment,
            "standard_based_on": request.standard_based_on,
            "deviation_description": request.deviation_description,
            "risk_assessment": request.risk_assessment,
            "temp_measures": request.temp_measures,
            "related_deviation_no": request.related_deviation_no,
            "related_capa": request.related_capa,
            "remarks": request.remarks,
            "qa_feishu_open_id": request.qa_feishu_open_id,
            "qa_feishu_name": request.qa_feishu_name,
            "dept_leader_feishu_open_id": request.dept_leader_feishu_open_id,
            "dept_leader_feishu_name": request.dept_leader_feishu_name,
            "reporter": request.reporter,
            "reporter_department": request.reporter_department,
            "reporter_feishu_open_id": request.reporter_feishu_open_id,
            "report_time": now,
            "created_at": now,
        }
    )
    
    await add_operation_log(
        session, deviation_id, "创建", request.reporter, request.reporter_department,
        f"创建偏差单 {deviation_no}"
    )
    
    await session.commit()
    
    return {
        "code": 200,
        "message": "创建成功",
        "data": {"id": deviation_id, "deviation_no": deviation_no}
    }


@router.get("/{deviation_id}", summary="获取偏差详情")
async def get_deviation(
    deviation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """获取偏差详情"""
    result = await session.execute(
        text("SELECT * FROM qms.qms_deviation WHERE id = :id AND is_deleted = FALSE"),
        {"id": deviation_id}
    )
    row = result.fetchone()
    
    if not row:
        return {"code": 404, "message": "偏差不存在", "data": None}
    
    columns = result.keys()
    deviation = dict(zip(columns, row))
    
    # 获取附件
    attach_result = await session.execute(
        text("SELECT * FROM qms.qms_deviation_attachment WHERE deviation_id = :id ORDER BY uploaded_at DESC"),
        {"id": deviation_id}
    )
    attachments = [dict(zip(attach_result.keys(), r)) for r in attach_result.fetchall()]
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            **deviation,
            "deviation_type_label": get_type_label(deviation.get("deviation_type")),
            "urgency_level_label": get_level_label(deviation.get("urgency_level")),
            "status_label": get_status_label(deviation.get("status")),
            "occurred_date": str(deviation.get("occurred_date")) if deviation.get("occurred_date") else None,
            "discovered_date": str(deviation.get("discovered_date")) if deviation.get("discovered_date") else None,
            "report_time": str(deviation.get("report_time")) if deviation.get("report_time") else None,
            "created_at": str(deviation.get("created_at")) if deviation.get("created_at") else None,
            "updated_at": str(deviation.get("updated_at")) if deviation.get("updated_at") else None,
            "attachments": [
                {
                    **a,
                    "uploaded_at": str(a.get("uploaded_at")) if a.get("uploaded_at") else None
                }
                for a in attachments
            ]
        }
    }


@router.put("/{deviation_id}", summary="更新偏差")
async def update_deviation(
    deviation_id: str,
    request: DeviationUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """更新偏差（草稿状态和基础完成状态可编辑）"""
    # 检查状态
    result = await session.execute(
        text("SELECT status, reporter FROM qms.qms_deviation WHERE id = :id AND is_deleted = FALSE"),
        {"id": deviation_id}
    )
    row = result.fetchone()
    
    if not row:
        return {"code": 404, "message": "偏差不存在", "data": None}
    
    # 允许草稿状态和基础完成状态编辑
    editable_statuses = ["draft", "basic_completed", "detail_completed"]
    if row[0] not in editable_statuses:
        return {"code": 400, "message": "当前状态不允许编辑", "data": None}
    
    # 构建更新语句
    updates = []
    params = {"id": deviation_id}
    
    # 需要转换为datetime的字段
    datetime_fields = ['occurred_date', 'discovered_date', 'report_time']
    
    for field, value in request.model_dump(exclude_unset=True).items():
        if value is not None:
            updates.append(f"{field} = :{field}")
            # 转换日期字符串为datetime对象
            if field in datetime_fields and isinstance(value, str):
                try:
                    params[field] = date_parser.parse(value)
                except Exception:
                    params[field] = value
            else:
                params[field] = value
    
    updates.append("updated_at = :updated_at")
    params["updated_at"] = datetime.now()
    
    if updates:
        await session.execute(
            text(f"UPDATE qms.qms_deviation SET {', '.join(updates)} WHERE id = :id"),
            params
        )
    
    await session.commit()
    
    return {"code": 200, "message": "更新成功", "data": None}


@router.delete("/{deviation_id}", summary="删除偏差")
async def delete_deviation(
    deviation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """删除偏差（仅草稿状态可删除）"""
    result = await session.execute(
        text("SELECT status FROM qms.qms_deviation WHERE id = :id AND is_deleted = FALSE"),
        {"id": deviation_id}
    )
    row = result.fetchone()
    
    if not row:
        return {"code": 404, "message": "偏差不存在", "data": None}
    
    if row[0] != "draft":
        return {"code": 400, "message": "只有草稿状态可以删除", "data": None}
    
    await session.execute(
        text("UPDATE qms.qms_deviation SET is_deleted = TRUE WHERE id = :id"),
        {"id": deviation_id}
    )
    await session.commit()
    
    return {"code": 200, "message": "删除成功", "data": None}


@router.post("/{deviation_id}/submit", summary="提交偏差（分阶段）")
async def submit_deviation(
    deviation_id: str,
    target_status: str = Query(..., description="目标状态: basic_completed/detail_completed/completed"),
    session: AsyncSession = Depends(get_db_session),
):
    """分阶段提交偏差，触发飞书通知"""
    result = await session.execute(
        text("""
            SELECT deviation_no, theme, deviation_type, urgency_level, status,
                   qa_feishu_open_id, qa_feishu_name,
                   dept_leader_feishu_open_id, dept_leader_feishu_name,
                   reporter, reporter_feishu_open_id, deviation_description, temp_measures, related_capa,
                   created_at, updated_at, occurred_date
            FROM qms.qms_deviation 
            WHERE id = :id AND is_deleted = FALSE
        """),
        {"id": deviation_id}
    )
    row = result.fetchone()
    
    if not row:
        return {"code": 404, "message": "偏差不存在", "data": None}
    
    deviation_no, theme, deviation_type, urgency_level, current_status, \
    qa_open_id, qa_name, leader_open_id, leader_name, reporter, reporter_open_id, \
    deviation_description, temp_measures, related_capa, created_at, updated_at, occurred_date = row
    
    # 检查状态流转是否有效
    valid_transitions = {
        "draft": ["basic_completed"],
        "basic_completed": ["detail_completed"],
        "detail_completed": ["completed"],
    }
    
    if current_status not in valid_transitions:
        return {"code": 400, "message": "当前状态不允许提交", "data": None}
    
    if target_status not in valid_transitions.get(current_status, []):
        return {"code": 400, "message": f"状态流转无效: {current_status} -> {target_status}", "data": None}
    
    # 检查各阶段必填字段
    # draft -> basic_completed: 需要基础信息（theme等已在表单验证）
    # basic_completed -> detail_completed: 需要偏差详情
    # detail_completed -> completed: 需要辅助信息
    if target_status == "detail_completed":
        if not deviation_description:
            return {"code": 400, "message": "请先填写偏差详情", "data": None}
    elif target_status == "completed":
        if not temp_measures or not related_capa:
            return {"code": 400, "message": "请先填写辅助信息", "data": None}
    
    # 更新状态
    await session.execute(
        text("UPDATE qms.qms_deviation SET status = :status, updated_at = :updated_at WHERE id = :id"),
        {"id": deviation_id, "status": target_status, "updated_at": datetime.now()}
    )
    
    status_labels = {
        "basic_completed": "基础完成",
        "detail_completed": "详情完成", 
        "completed": "已完成"
    }
    
    # 添加日志
    await add_operation_log(
        session, deviation_id, "提交", reporter or "系统", "",
        f"偏差单 {deviation_no} 状态变更为「{status_labels.get(target_status, target_status)}」"
    )
    
    await session.commit()
    
    # 发送飞书通知（所有提交阶段都发送）
    try:
        # 从数据库获取飞书配置
        from app.modules.quality.qms.feishu_service import get_feishu_config_from_db
        feishu_config = await get_feishu_config_from_db()
        
        if feishu_config and feishu_config.get("app_id"):
            client = FeishuClient(feishu_config["app_id"], feishu_config["app_secret"])
            
            # 获取状态对应的中文标签
            status_label = status_labels.get(target_status, target_status)
            
            # 计算剩余完成天数
            from datetime import datetime, timedelta
            now = datetime.now()
            deadline_days = 30
            remaining_days = 0
            completed_days = 0
            
            if created_at:
                if target_status == "completed":
                    # 已完成：计算从创建到完成的实际天数
                    completed_at = updated_at or created_at
                    delta = completed_at - created_at
                    completed_days = delta.days
                else:
                    # 未完成：计算剩余天数
                    deadline = created_at + timedelta(days=deadline_days)
                    remaining_days = max(0, (deadline - now).days)
            
            # 通用变量
            common_vars = {
                "deviation_no": deviation_no,
                "theme": theme or "",
                "deviation_type": get_type_label(deviation_type),
                "urgency_level": get_level_label(urgency_level),
                "reporter": reporter or "未知",
                "status": status_label,
                "remaining_days": remaining_days,
                "completed_days": completed_days,
                "occurred_date": str(occurred_date)[:10] if occurred_date else "",
                "reporter_name": reporter or "",
            }
            
            # 获取模板
            qa_template = await get_template_content(session, "qa_notification", target_status)
            leader_template = await get_template_content(session, "leader_notification", target_status)
            reporter_template = await get_template_content(session, "reporter_notification", target_status)
            
            # 通知QA人员
            if qa_open_id:
                if qa_template:
                    title = render_template(qa_template["title_template"], common_vars)
                    content = render_template(qa_template["content_template"], common_vars)
                else:
                    title = f"📋 偏差通知 - 偏差单 {deviation_no} 已提交"
                    content = f"**偏差单 {deviation_no} 已提交「{status_label}」状态，请及时跟进！**\n\n**偏差主题：** {theme}\n**偏差类型：** {get_type_label(deviation_type)}\n**紧急等级：** {get_level_label(urgency_level)}\n**填报人：** {reporter or '未知'}\n\n请登录系统查看详情并跟进。"
                
                card_content = {
                    "config": {"wide_screen_mode": True},
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": content}
                    }]
                }
                
                try:
                    await client.send_card_message(
                        receive_id_type="open_id",
                        receive_id=qa_open_id,
                        card_content=card_content,
                    )
                    logger.info(f"✅ 飞书通知发送给QA成功: {qa_open_id}")
                except Exception as e:
                    logger.error(f"❌ 发送飞书通知给QA失败: {e}")
            
            # 通知部门负责人
            if leader_open_id:
                if leader_template:
                    title = render_template(leader_template["title_template"], common_vars)
                    content = render_template(leader_template["content_template"], common_vars)
                else:
                    title = f"📢 偏差通知 - 偏差单 {deviation_no} 已提交"
                    content = f"**偏差单 {deviation_no} 已提交「{status_label}」状态，请知悉！**\n\n**偏差主题：** {theme}\n**偏差类型：** {get_type_label(deviation_type)}\n**紧急等级：** {get_level_label(urgency_level)}\n**填报人：** {reporter or '未知'}\n\n请登录系统查看详情。"
                
                card_content = {
                    "config": {"wide_screen_mode": True},
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": content}
                    }]
                }
                
                try:
                    await client.send_card_message(
                        receive_id_type="open_id",
                        receive_id=leader_open_id,
                        card_content=card_content,
                    )
                    logger.info(f"✅ 飞书通知发送给部门负责人成功: {leader_open_id}")
                except Exception as e:
                    logger.error(f"❌ 发送飞书通知给部门负责人失败: {e}")
            
            # 通知填报人
            if reporter_open_id:
                if reporter_template:
                    title = render_template(reporter_template["title_template"], common_vars)
                    content = render_template(reporter_template["content_template"], common_vars)
                else:
                    title = f"📋 偏差通知 - 偏差单 {deviation_no} 已提交"
                    content = f"**您提交的偏差单 {deviation_no} 已提交「{status_label}」状态！**\n\n**偏差主题：** {theme}\n**偏差类型：** {get_type_label(deviation_type)}\n**紧急等级：** {get_level_label(urgency_level)}\n\n请登录系统查看进度。"
                
                card_content = {
                    "config": {"wide_screen_mode": True},
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": content}
                    }]
                }
                
                try:
                    await client.send_card_message(
                        receive_id_type="open_id",
                        receive_id=reporter_open_id,
                        card_content=card_content,
                    )
                    logger.info(f"✅ 飞书通知发送给填报人成功: {reporter_open_id}")
                except Exception as e:
                    logger.error(f"❌ 发送飞书通知给填报人失败: {e}")
    except Exception as e:
        logger.error(f"发送飞书通知异常: {e}")
    
    # 如果提交到"已完成"状态，发送完成通知给填报人
    if target_status == "completed" and reporter_open_id:
        try:
            from app.modules.quality.qms.deviation_reporter_reminder_service import send_completion_notification
            send_completion_notification(session, reporter_open_id, deviation_no, theme or "")
            logger.info(f"已触发完成通知发送给填报人: {reporter_open_id}")
        except Exception as e:
            logger.error(f"发送完成通知失败: {e}")
    
    return {"code": 200, "message": f"提交成功，已进入「{status_labels.get(target_status, target_status)}」状态", "data": {"status": target_status}}


@router.get("", summary="偏差列表")
async def list_deviations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(None, description="搜索关键词"),
    status: str = Query(None, description="状态筛选"),
    deviation_type: str = Query(None, description="偏差类型筛选"),
    urgency_level: str = Query(None, description="紧急等级筛选"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    session: AsyncSession = Depends(get_db_session),
):
    """获取偏差列表"""
    conditions = ["is_deleted = FALSE"]
    params = {}
    
    if keyword:
        conditions.append("(theme LIKE :keyword OR deviation_no LIKE :keyword)")
        params["keyword"] = f"%{keyword}%"
    
    if status:
        conditions.append("status = :status")
        params["status"] = status
    
    if deviation_type:
        conditions.append("deviation_type = :deviation_type")
        params["deviation_type"] = deviation_type
    
    if urgency_level:
        conditions.append("urgency_level = :urgency_level")
        params["urgency_level"] = urgency_level
    
    if start_date:
        conditions.append("occurred_date >= :start_date")
        params["start_date"] = start_date
    
    if end_date:
        conditions.append("occurred_date <= :end_date")
        params["end_date"] = end_date
    
    where_clause = " AND ".join(conditions)
    
    # 计数
    count_result = await session.execute(
        text(f"SELECT COUNT(*) FROM qms.qms_deviation WHERE {where_clause}"),
        params
    )
    total = count_result.scalar()
    
    # 分页查询
    offset = (page - 1) * page_size
    result = await session.execute(
        text(f"""
            SELECT id, deviation_no, theme, occurred_date, discovered_date,
                   responsible_department, occurred_area, deviation_type, urgency_level, status,
                   reporter, reporter_department, report_time, created_at
            FROM qms.qms_deviation 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": page_size, "offset": offset}
    )
    
    items = []
    from datetime import datetime
    now = datetime.now()
    deadline_days = 30  # 倒计时天数
    
    for row in result.fetchall():
        columns = result.keys()
        item = dict(zip(columns, row))
        
        # 计算剩余完成天数
        created_at = item.get("created_at")
        status = item.get("status")
        remaining_days = None
        completed_days = None
        
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            if status == "completed":
                # 已完成：计算从创建到完成的实际天数
                completed_at = item.get("updated_at") or created_at
                if isinstance(completed_at, str):
                    completed_at = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                delta = completed_at - created_at
                completed_days = delta.days
            else:
                # 未完成：计算剩余天数
                deadline = created_at.replace(hour=0, minute=0, second=0, microsecond=0)
                deadline = deadline + timedelta(days=deadline_days)
                remaining = (deadline - now).days
                remaining_days = max(0, remaining)
        
        items.append({
            **item,
            "deviation_type_label": get_type_label(item.get("deviation_type")),
            "urgency_level_label": get_level_label(item.get("urgency_level")),
            "status_label": get_status_label(item.get("status")),
            "occurred_date": str(item.get("occurred_date"))[:10] if item.get("occurred_date") else None,
            "created_at": str(item.get("created_at"))[:19] if item.get("created_at") else None,
            "remaining_days": remaining_days,
            "completed_days": completed_days,
            "deadline_days": deadline_days,
        })
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }


# ============ 附件管理 API ============

@router.get("/{deviation_id}/attachments", summary="获取偏差附件列表")
async def list_attachments(
    deviation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """获取偏差的附件列表"""
    # 检查偏差是否存在
    result = await session.execute(
        text("SELECT deviation_no FROM qms.qms_deviation WHERE id = :id AND is_deleted = FALSE"),
        {"id": deviation_id}
    )
    if not result.fetchone():
        return {"code": 404, "message": "偏差不存在", "data": []}
    
    # 获取附件列表
    result = await session.execute(
        text("""
            SELECT id, file_name, file_path, file_type, file_size, is_report, uploaded_at
            FROM qms.qms_deviation_attachment 
            WHERE deviation_id = :deviation_id 
            ORDER BY uploaded_at DESC
        """),
        {"deviation_id": deviation_id}
    )
    rows = result.fetchall()
    
    attachments = []
    for row in rows:
        attachments.append({
            "id": row[0],
            "file_name": row[1],
            "file_path": row[2],
            "file_type": row[3],
            "file_size": row[4],
            "is_report": row[5],
            "uploaded_at": str(row[6]) if row[6] else None,
        })
    
    return {"code": 200, "message": "success", "data": attachments}


@router.post("/{deviation_id}/attachments", summary="上传偏差附件")
async def upload_attachment(
    deviation_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
):
    """上传偏差附件（仅 detail_completed 状态可上传）"""
    # 检查偏差是否存在且状态为 detail_completed
    result = await session.execute(
        text("SELECT status, deviation_no FROM qms.qms_deviation WHERE id = :id AND is_deleted = FALSE"),
        {"id": deviation_id}
    )
    row = result.fetchone()
    
    if not row:
        return {"code": 404, "message": "偏差不存在", "data": None}
    
    if row[0] != "detail_completed":
        return {"code": 400, "message": "当前状态不允许上传附件", "data": None}
    
    # 保存文件
    import os
    import uuid
    from datetime import datetime
    
    upload_dir = os.path.join(settings.UPLOAD_DIR, "deviation_attachments", deviation_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    # 获取文件扩展名
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    stored_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(upload_dir, stored_filename)
    
    # 保存文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 获取文件大小
    file_size = len(content)
    
    # 获取文件类型
    file_type = file.content_type or "application/octet-stream"
    
    # 判断是否为报告类型（根据文件名或类型判断）
    is_report = "report" in (file.filename or "").lower() or "报告" in (file.filename or "")
    
    # 保存附件记录
    attachment_id = str(uuid.uuid4())
    now = datetime.now()
    
    await session.execute(
        text("""
            INSERT INTO qms.qms_deviation_attachment (
                id, deviation_id, file_name, file_path, file_type, file_size, is_report, uploaded_at
            ) VALUES (
                :id, :deviation_id, :file_name, :file_path, :file_type, :file_size, :is_report, :uploaded_at
            )
        """),
        {
            "id": attachment_id,
            "deviation_id": deviation_id,
            "file_name": file.filename,
            "file_path": file_path,
            "file_type": file_type,
            "file_size": file_size,
            "is_report": is_report,
            "uploaded_at": now,
        }
    )
    await session.commit()
    
    return {
        "code": 200,
        "message": "上传成功",
        "data": {
            "id": attachment_id,
            "file_name": file.filename,
            "file_path": file_path,
            "file_size": file_size,
        }
    }


@router.get("/attachments/{attachment_id}/download", summary="下载偏差附件")
async def download_attachment(
    attachment_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """下载偏差附件"""
    # 获取附件信息
    result = await session.execute(
        text("""
            SELECT file_name, file_path, file_type, file_size 
            FROM qms.qms_deviation_attachment 
            WHERE id = :id
        """),
        {"id": attachment_id}
    )
    row = result.fetchone()
    
    if not row:
        return {"code": 404, "message": "附件不存在", "data": None}
    
    file_name, file_path, file_type, file_size = row
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {"code": 404, "message": "文件不存在", "data": None}
    
    # 读取文件
    with open(file_path, "rb") as f:
        file_content = f.read()
    
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    
    return StreamingResponse(
        BytesIO(file_content),
        media_type=file_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Length": str(file_size),
        }
    )