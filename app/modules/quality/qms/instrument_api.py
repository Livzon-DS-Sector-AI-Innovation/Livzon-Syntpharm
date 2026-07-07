"""Instrument Calibration API (仪器校准管理API路由)

仪器设备台账、校准规则配置、校准记录的API接口
"""

import logging
from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.quality.qms.instrument_schemas import (
    # Approval
    CalibrationRecordCreate,
    CalibrationRecordResponse,
    CalibrationRecordUpdate,
    # CalibrationRule
    CalibrationRuleCreate,
    CalibrationRuleResponse,
    CalibrationRuleUpdate,
    # Instrument
    InstrumentCreate,
    InstrumentResponse,
    InstrumentUpdate,
    # ReminderConfig
    ReminderConfigCreate,
    ReminderConfigUpdate,
)
from app.modules.quality.qms.instrument_service import (
    CalibrationRecordService,
    CalibrationRuleService,
    InstrumentService,
    ReminderConfigService,
)


class ApiResponse(BaseModel):
    """统一响应格式"""

    code: int = 200
    message: str = "Success"
    data: dict | list | None = None


router = APIRouter(prefix="/instrument", tags=["仪器校准管理"])


def get_instrument_service(session=Depends(get_db)) -> InstrumentService:
    return InstrumentService(session)


def get_rule_service(session=Depends(get_db)) -> CalibrationRuleService:
    return CalibrationRuleService(session)


def get_record_service(session=Depends(get_db)) -> CalibrationRecordService:
    return CalibrationRecordService(session)


def get_reminder_config_service(session=Depends(get_db)) -> ReminderConfigService:
    return ReminderConfigService(session)


# ========== 飞书通讯录 API ==========


@router.post("/feishu-contacts/resolve-user", response_model=ApiResponse)
async def resolve_feishu_user(
    mobile: str = Body(None, description="手机号"),
    email: str = Body(None, description="邮箱"),
    service: ReminderConfigService = Depends(get_reminder_config_service),
):
    """通过手机号或邮箱获取飞书用户的 open_id"""
    import logging

    logger = logging.getLogger(__name__)

    if not mobile and not email:
        return ApiResponse(message="请提供手机号或邮箱", data={"open_id": None})

    # 获取第一个启用的提醒配置的飞书凭证
    configs = await service.list_active_configs()
    if not configs:
        return ApiResponse(message="无可用的飞书配置", data={"open_id": None})

    config = configs[0]
    if not config.feishu_app_id or not config.feishu_app_secret:
        return ApiResponse(message="飞书应用未配置", data={"open_id": None})

    try:
        from app.platform.notification.feishu_client_config import FeishuClient

        client = FeishuClient(config.feishu_app_id, config.feishu_app_secret)
        open_id = await client.get_user_by_mobile_or_email(mobile=mobile, email=email)
        if open_id:
            return ApiResponse(message="获取成功", data={"open_id": open_id})
        else:
            return ApiResponse(message="未找到该用户", data={"open_id": None})
    except Exception as e:
        logger.error(f"获取飞书用户失败: {str(e)}")
        return ApiResponse(message=f"获取用户失败: {str(e)}", data={"open_id": None})


# ========== 提醒配置管理 API ==========


@router.get("/reminder-config", response_model=ApiResponse)
async def list_reminder_configs(
    service: ReminderConfigService = Depends(get_reminder_config_service),
):
    """获取所有提醒配置"""
    configs = await service.list_configs()
    items = [
        {
            "id": str(config.id),
            "name": config.name,
            "feishu_app_id": config.feishu_app_id,
            "feishu_app_secret": config.feishu_app_secret,
            "chat_id": config.chat_id,
            "receive_id_type": config.receive_id_type,
            "remind_30_days": config.remind_30_days,
            "remind_14_days": config.remind_14_days,
            "remind_7_days": config.remind_7_days,
            "remind_overdue": config.remind_overdue,
            "is_active": config.is_active,
            "last_remind_30_days": config.last_remind_30_days.isoformat()
            if config.last_remind_30_days
            else None,
            "last_remind_14_days": config.last_remind_14_days.isoformat()
            if config.last_remind_14_days
            else None,
            "last_remind_7_days": config.last_remind_7_days.isoformat()
            if config.last_remind_7_days
            else None,
            "last_remind_overdue": config.last_remind_overdue.isoformat()
            if config.last_remind_overdue
            else None,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
        }
        for config in configs
    ]

    return ApiResponse(message="获取成功", data={"items": items, "total": len(items)})


@router.post("/reminder-config", response_model=ApiResponse)
async def create_reminder_config(
    data: ReminderConfigCreate,
    service: ReminderConfigService = Depends(get_reminder_config_service),
):
    """创建提醒配置"""
    config = await service.create_config(data)

    return ApiResponse(
        message="创建成功",
        data={
            "id": str(config.id),
            "name": config.name,
            "feishu_app_id": config.feishu_app_id,
            "feishu_app_secret": config.feishu_app_secret,
            "chat_id": config.chat_id,
            "receive_id_type": config.receive_id_type,
            "remind_30_days": config.remind_30_days,
            "remind_14_days": config.remind_14_days,
            "remind_7_days": config.remind_7_days,
            "remind_overdue": config.remind_overdue,
            "is_active": config.is_active,
        },
    )


@router.put("/reminder-config/{config_id}", response_model=ApiResponse)
async def update_reminder_config(
    config_id: UUID,
    data: ReminderConfigUpdate,
    service: ReminderConfigService = Depends(get_reminder_config_service),
):
    """更新提醒配置"""
    config = await service.update_config(config_id, data)

    return ApiResponse(
        message="更新成功",
        data={
            "id": str(config.id),
            "name": config.name,
            "feishu_app_id": config.feishu_app_id,
            "feishu_app_secret": config.feishu_app_secret,
            "chat_id": config.chat_id,
            "receive_id_type": config.receive_id_type,
            "remind_30_days": config.remind_30_days,
            "remind_14_days": config.remind_14_days,
            "remind_7_days": config.remind_7_days,
            "remind_overdue": config.remind_overdue,
            "is_active": config.is_active,
        },
    )


@router.delete("/reminder-config/{config_id}", response_model=ApiResponse)
async def delete_reminder_config(
    config_id: UUID,
    service: ReminderConfigService = Depends(get_reminder_config_service),
):
    """删除提醒配置"""
    await service.delete_config(config_id)

    return ApiResponse(message="删除成功")


# ========== 仪器设备台账 API ==========


@router.get("", response_model=ApiResponse)
async def list_instruments(
    instrument_no: str | None = Query(None, description="仪器编号"),
    instrument_name: str | None = Query(None, description="仪器名称"),
    category: str | None = Query(None, description="仪器分类"),
    is_active: bool | None = Query(None, description="是否启用"),
    status: str | None = Query(None, description="状态"),
    is_overdue: bool | None = Query(None, description="是否超期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: InstrumentService = Depends(get_instrument_service),
):
    """获取仪器设备列表"""
    instruments, total = await service.list_instruments(
        instrument_no=instrument_no,
        instrument_name=instrument_name,
        category=category,
        is_active=is_active,
        status=status,
        is_overdue=is_overdue,
        page=page,
        page_size=page_size,
    )

    # list_instruments 已经返回包含 valid_until 和 is_overdue 的字典列表
    return ApiResponse(
        data={
            "items": instruments,  # service.list_instruments 返回的字典已包含 valid_until 和 is_overdue
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("", response_model=ApiResponse)
async def create_instrument(
    data: InstrumentCreate,
    service: InstrumentService = Depends(get_instrument_service),
    current_user=Depends(get_current_user),
):
    """创建仪器设备"""
    try:
        user_id = current_user.id if current_user else None
        instrument = await service.create_instrument(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=InstrumentResponse.model_validate(instrument).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{instrument_id}/submit", response_model=ApiResponse)
async def submit_instrument(
    instrument_id: UUID,
    service: InstrumentService = Depends(get_instrument_service),
    current_user=Depends(get_current_user),
):
    """提交仪器审核"""
    try:
        user_id = current_user.id if current_user else None
        instrument = await service.submit_instrument(instrument_id, user_id)
        return ApiResponse(
            message="提交成功",
            data=InstrumentResponse.model_validate(instrument).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{instrument_id}/approve", response_model=ApiResponse)
async def approve_instrument(
    instrument_id: UUID,
    approved: bool = Query(..., description="是否批准"),
    comments: str | None = Query(None, description="审批意见"),
    approval_type: str = Query("admin", description="审批类型：admin/qa"),
    service: InstrumentService = Depends(get_instrument_service),
    current_user=Depends(get_current_user),
):
    """审批仪器"""
    try:
        user_id = current_user.id if current_user else None
        user_name = current_user.username if current_user else None
        instrument = await service.approve_instrument(
            instrument_id, approved, comments, approval_type, user_id, user_name
        )
        return ApiResponse(
            message="审批完成",
            data=InstrumentResponse.model_validate(instrument).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{instrument_id}/activate", response_model=ApiResponse)
async def activate_instrument(
    instrument_id: UUID,
    service: InstrumentService = Depends(get_instrument_service),
    current_user=Depends(get_current_user),
):
    """启用仪器"""
    try:
        user_id = current_user.id if current_user else None
        instrument = await service.activate_instrument(instrument_id, user_id)
        return ApiResponse(
            message="启用成功",
            data=InstrumentResponse.model_validate(instrument).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{instrument_id}/deactivate", response_model=ApiResponse)
async def deactivate_instrument(
    instrument_id: UUID,
    reason: str = Query(..., description="停用原因"),
    service: InstrumentService = Depends(get_instrument_service),
    current_user=Depends(get_current_user),
):
    """停用仪器"""
    try:
        user_id = current_user.id if current_user else None
        instrument = await service.deactivate_instrument(instrument_id, reason, user_id)
        return ApiResponse(
            message="停用成功",
            data=InstrumentResponse.model_validate(instrument).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 校准规则 API ==========


@router.get("/rules", response_model=ApiResponse)
async def list_calibration_rules(
    instrument_id: str | None = Query(None, description="仪器ID"),
    service: CalibrationRuleService = Depends(get_rule_service),
):
    """获取校准规则列表"""
    rules = await service.list_rules(instrument_id)
    return ApiResponse(
        data=[
            CalibrationRuleResponse.model_validate(rule).model_dump() for rule in rules
        ]
    )


@router.get("/rules/{instrument_id}", response_model=ApiResponse)
async def get_calibration_rule(
    instrument_id: UUID,
    service: CalibrationRuleService = Depends(get_rule_service),
):
    """获取仪器校准规则"""
    rule = await service.repository.get_by_instrument_id(instrument_id)
    if rule:
        return ApiResponse(
            data=CalibrationRuleResponse.model_validate(rule).model_dump()
        )
    return ApiResponse(data=None)


@router.post("/rules", response_model=ApiResponse)
async def create_calibration_rule(
    data: CalibrationRuleCreate,
    service: CalibrationRuleService = Depends(get_rule_service),
    current_user=Depends(get_current_user),
):
    """创建校准规则"""
    try:
        user_id = current_user.id if current_user else None
        rule = await service.create_rule(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=CalibrationRuleResponse.model_validate(rule).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/rules/{rule_id}", response_model=ApiResponse)
async def update_calibration_rule(
    rule_id: UUID,
    data: CalibrationRuleUpdate,
    service: CalibrationRuleService = Depends(get_rule_service),
    current_user=Depends(get_current_user),
):
    """更新校准规则"""
    try:
        user_id = current_user.id if current_user else None
        rule = await service.update_rule(rule_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=CalibrationRuleResponse.model_validate(rule).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_calibration_rule(
    rule_id: UUID,
    service: CalibrationRuleService = Depends(get_rule_service),
):
    """删除校准规则"""
    try:
        await service.delete_rule(rule_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/upcoming", response_model=ApiResponse)
async def get_upcoming_calibrations(
    days: int = Query(30, description="提前预警天数"),
    service: CalibrationRuleService = Depends(get_rule_service),
):
    """获取即将到期的校准计划"""
    rules = await service.get_upcoming_calibrations(days)
    return ApiResponse(
        data=[
            {
                "id": str(rule.id),
                "instrument_id": str(rule.instrument_id),
                "instrument_name": rule.instrument.instrument_name
                if rule.instrument
                else None,
                "calibration_method": rule.calibration_method,
                "next_calibration_date": rule.next_calibration_date.isoformat()
                if rule.next_calibration_date
                else None,
                "warning_days": rule.warning_days,
            }
            for rule in rules
        ]
    )


# ========== 校准记录 API ==========


@router.get("/records", response_model=ApiResponse)
async def list_calibration_records(
    instrument_id: str | None = Query(None, description="仪器ID"),
    rule_id: str | None = Query(None, description="校准规则ID"),
    calibration_no: str | None = Query(None, description="校准单据编号"),
    calibration_result: str | None = Query(None, description="校准结论"),
    status: str | None = Query(None, description="状态"),
    calibration_method: str | None = Query(None, description="校准方式"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: CalibrationRecordService = Depends(get_record_service),
):
    """获取校准记录列表"""
    from datetime import datetime

    # 直接使用字符串instrument_id，让service层处理转换
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    records, total = await service.list_records(
        instrument_id=instrument_id,
        rule_id=rule_id,
        calibration_no=calibration_no,
        calibration_result=calibration_result,
        status=status,
        calibration_method=calibration_method,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        page_size=page_size,
    )

    # 获取仪器信息
    instrument_service = InstrumentService(service.session)
    items = []
    for record in records:
        instrument = await instrument_service.repository.get_by_id(record.instrument_id)
        items.append(
            {
                "id": str(record.id),
                "calibration_no": record.calibration_no,
                "instrument_id": str(record.instrument_id),
                "rule_id": str(record.rule_id) if record.rule_id else None,
                "instrument_no": instrument.instrument_no if instrument else None,
                "instrument_name": instrument.instrument_name if instrument else None,
                "calibration_date": record.calibration_date.isoformat()
                if record.calibration_date
                else None,
                "valid_until": record.valid_until.isoformat()
                if record.valid_until
                else None,
                "calibration_method": record.calibration_method,
                "calibration_result": record.calibration_result,
                "status": record.status,
                "calibrator_name": record.calibrator_name,
                "certificate_no": record.certificate_no,
                "created_at": record.created_at.isoformat()
                if record.created_at
                else None,
            }
        )

    return ApiResponse(
        data={"items": items, "total": total, "page": page, "page_size": page_size}
    )


@router.get("/records/{record_id}", response_model=ApiResponse)
async def get_calibration_record(
    record_id: UUID,
    service: CalibrationRecordService = Depends(get_record_service),
):
    """获取校准记录详情"""
    try:
        record = await service.get_record(record_id)
        return ApiResponse(
            data=CalibrationRecordResponse.model_validate(record).model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/records", response_model=ApiResponse)
async def create_calibration_record(
    data: CalibrationRecordCreate,
    service: CalibrationRecordService = Depends(get_record_service),
    current_user=Depends(get_current_user),
):
    """创建校准记录"""
    try:
        user_id = current_user.id if current_user else None
        record = await service.create_record(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=CalibrationRecordResponse.model_validate(record).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/records/{record_id}", response_model=ApiResponse)
async def update_calibration_record(
    record_id: UUID,
    data: CalibrationRecordUpdate,
    service: CalibrationRecordService = Depends(get_record_service),
    current_user=Depends(get_current_user),
):
    """更新校准记录"""
    try:
        user_id = current_user.id if current_user else None
        record = await service.update_record(record_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=CalibrationRecordResponse.model_validate(record).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/records/{record_id}")
async def delete_calibration_record(
    record_id: UUID,
    service: CalibrationRecordService = Depends(get_record_service),
):
    """删除校准记录"""
    try:
        await service.delete_record(record_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/records/{record_id}/submit", response_model=ApiResponse)
async def submit_calibration_record(
    record_id: UUID,
    service: CalibrationRecordService = Depends(get_record_service),
    current_user=Depends(get_current_user),
):
    """提交校准记录"""
    try:
        user_id = current_user.id if current_user else None
        record = await service.submit_record(record_id, user_id)
        return ApiResponse(
            message="提交成功",
            data=CalibrationRecordResponse.model_validate(record).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/records/{record_id}/approve", response_model=ApiResponse)
async def approve_calibration_record(
    record_id: UUID,
    approved: bool = Query(..., description="是否批准"),
    comments: str | None = Query(None, description="审批意见"),
    approval_type: str = Query("admin", description="审批类型：admin/qa"),
    service: CalibrationRecordService = Depends(get_record_service),
    current_user=Depends(get_current_user),
):
    """审批校准记录"""
    try:
        user_id = current_user.id if current_user else None
        user_name = current_user.username if current_user else None
        record = await service.approve_record(
            record_id, approved, comments, approval_type, user_id, user_name
        )
        return ApiResponse(
            message="审批完成",
            data=CalibrationRecordResponse.model_validate(record).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 仪器设备详情/更新/删除 API (必须在/records之后) ==========


@router.get("/{instrument_id}", response_model=ApiResponse)
async def get_instrument(
    instrument_id: UUID,
    service: InstrumentService = Depends(get_instrument_service),
):
    """获取仪器详情"""
    try:
        instrument = await service.get_instrument(instrument_id)
        return ApiResponse(
            data=InstrumentResponse.model_validate(instrument).model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{instrument_id}", response_model=ApiResponse)
async def update_instrument(
    instrument_id: UUID,
    data: InstrumentUpdate,
    service: InstrumentService = Depends(get_instrument_service),
    current_user=Depends(get_current_user),
):
    """更新仪器设备"""
    try:
        user_id = current_user.id if current_user else None
        instrument = await service.update_instrument(instrument_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=InstrumentResponse.model_validate(instrument).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{instrument_id}")
async def delete_instrument(
    instrument_id: UUID,
    service: InstrumentService = Depends(get_instrument_service),
):
    """删除仪器设备"""
    try:
        await service.delete_instrument(instrument_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== AI 识别 API ==========


@router.post("/recognize", response_model=ApiResponse)
async def recognize_instrument_label(
    file: UploadFile = File(..., description="仪器标签图片"),
):
    """AI识别仪器标签图片，提取设备信息"""
    import json
    import os
    from pathlib import Path

    # 检查文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    # 保存上传的文件到临时目录
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    uploads_dir = backend_dir / "uploads" / "instrument_labels"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    suffix = Path(file.filename).suffix if file.filename else ".jpg"
    temp_path = uploads_dir / f"temp_{os.urandom(8).hex()}{suffix}"

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # 调用 AI 识别
        from app.platform.ai.minimax_util import get_vision_util

        vision_util = get_vision_util()

        # 设备标签识别提示词
        prompt = """你是专业的设备标签信息识别专家，服务于制药行业GMP合规的实验室设备管理系统。请从提供的设备标签图片中准确提取指定字段的信息。

请提取以下字段并以JSON格式返回：
- instrument_name: 设备名称/仪器名称
- model: 规格型号
- serial_no: 出厂编号/序列号
- manufacturer: 制造商/生产厂家
- last_calibration_date: 最近校准日期（格式YYYY-MM-DD）
- next_calibration_date: 下次校准日期（格式YYYY-MM-DD）
- calibration_agency: 校准机构

提取规则：
1. 严格按照指定的字段名称提取，不要遗漏任何字段
2. 日期格式统一为YYYY-MM-DD，如图片中的日期格式不符合，请转换为标准格式
3. 如某个字段在图片中不存在或无法识别，对应的值填空字符串
4. 确保提取的信息准确无误，符合制药行业GMP管理的严谨要求
5. 只返回JSON格式，不要有其他文字"""

        # 使用相对路径（相对于后端根目录的uploads目录）
        relative_path = f"/uploads/instrument_labels/{temp_path.name}"
        result = await vision_util.recognize_image([relative_path], prompt)

        # 解析AI返回的JSON结果
        try:
            # 尝试提取JSON部分
            json_str = result.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]

            recognized_data = json.loads(json_str.strip())

            # 映射字段名到我们的格式
            return ApiResponse(
                message="识别成功",
                data={
                    "instrument_name": recognized_data.get("instrument_name", ""),
                    "model": recognized_data.get("model", ""),
                    "serial_no": recognized_data.get("serial_no", ""),
                    "manufacturer": recognized_data.get("manufacturer", ""),
                    "last_calibration_date": recognized_data.get(
                        "last_calibration_date", ""
                    ),
                    "next_calibration_date": recognized_data.get(
                        "next_calibration_date", ""
                    ),
                    "calibration_agency": recognized_data.get("calibration_agency", ""),
                },
            )
        except json.JSONDecodeError:
            # AI返回的不是有效JSON，直接返回原始结果
            return ApiResponse(
                message="识别完成，请核对结果",
                data={
                    "raw_result": result,
                    "instrument_name": "",
                    "model": "",
                    "serial_no": "",
                    "manufacturer": "",
                    "last_calibration_date": "",
                    "next_calibration_date": "",
                    "calibration_agency": "",
                },
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ========== 校准记录到期提醒 API ==========


@router.get("/record/upcoming", response_model=ApiResponse)
async def get_upcoming_calibration_records(
    days: int = Query(30, ge=1, le=365, description="提前提醒天数"),
    service: CalibrationRecordService = Depends(get_record_service),
):
    """获取即将到期的校准记录"""
    records = await service.get_upcoming_records(days=days)

    # 构建响应数据
    items = []
    for record in records:
        instrument = record.instrument
        days_until_expiry = None
        if record.valid_until:
            from datetime import datetime

            days_until_expiry = (
                record.valid_until.replace(tzinfo=None) - datetime.now()
            ).days

        items.append(
            {
                "id": str(record.id),
                "calibration_no": record.calibration_no,
                "instrument_id": str(record.instrument_id)
                if record.instrument_id
                else None,
                "instrument_no": instrument.instrument_no if instrument else None,
                "instrument_name": instrument.instrument_name if instrument else None,
                "calibration_date": record.calibration_date.isoformat()
                if record.calibration_date
                else None,
                "valid_until": record.valid_until.isoformat()
                if record.valid_until
                else None,
                "calibration_result": record.calibration_result,
                "days_until_expiry": days_until_expiry,
            }
        )

    return ApiResponse(
        message="获取成功",
        data={
            "items": items,
            "total": len(items),
            "days": days,
        },
    )


@router.get("/record/for-reminder", response_model=ApiResponse)
async def get_records_for_reminder(
    days: int = Query(30, ge=1, le=365, description="提前提醒天数"),
    service: CalibrationRecordService = Depends(get_record_service),
):
    """获取需要提醒的记录（超期 + 即将到期）"""
    result = await service.get_records_for_reminder(days=days)
    return ApiResponse(message="获取成功", data=result)


@router.post("/record/remind", response_model=ApiResponse)
async def send_calibration_reminder(
    chat_id: str = Query(..., description="飞书群ID或用户ID或open_id"),
    receive_id_type: str = Query(
        "chat_id", description="接收者类型: chat_id/user_id/open_id"
    ),
    days: int = Query(30, ge=1, le=365, description="提前提醒天数"),
    include_overdue: bool = Query(True, description="是否包含超期记录"),
    feishu_app_id: str | None = Query(None, description="飞书应用AppID"),
    feishu_app_secret: str | None = Query(None, description="飞书应用AppSecret"),
    service: CalibrationRecordService = Depends(get_record_service),
):
    """发送校准记录到期提醒到飞书"""
    import logging

    from app.platform.notification.feishu_client_config import (
        send_feishu_card_from_config,
    )

    logger = logging.getLogger(__name__)
    from datetime import datetime

    try:
        # 获取即将到期的记录
        records = await service.get_upcoming_records(days=days)

        # 获取超期记录
        overdue_records = []
        if include_overdue:
            overdue_records = await service.get_overdue_records()
    except Exception as e:
        logger.error(f"获取校准提醒记录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取提醒记录失败: {str(e)}")

    if not records and not overdue_records:
        return ApiResponse(
            message="没有需要提醒的校准记录", data={"sent": False, "count": 0}
        )

    # 构建消息内容
    now_utc = datetime.now(UTC)
    content_lines = []
    overdue_count = 0
    upcoming_count = 0

    # 超期记录
    if overdue_records:
        content_lines.append("⚠️ **【已超期】**")
        for record in overdue_records:
            instrument = record.instrument
            instrument_name = instrument.instrument_name if instrument else "未知仪器"
            instrument_no = instrument.instrument_no if instrument else "未知编号"
            if record.valid_until:
                valid_until_str = record.valid_until.strftime("%Y-%m-%d")
                days_overdue = (now_utc - record.valid_until).days
                days_str = f"已超期 {days_overdue} 天"
            else:
                valid_until_str = "未设置"
                days_str = ""
            content_lines.append(
                f"• **{instrument_name}** ({instrument_no})\n"
                f"  有效期至: {valid_until_str} {days_str}\n"
                f"  校准结论: {record.calibration_result}"
            )
            overdue_count += 1

    # 即将到期记录
    if records:
        if overdue_records:
            content_lines.append("")
        content_lines.append("📅 **【即将到期】**")
        for record in records:
            instrument = record.instrument
            instrument_name = instrument.instrument_name if instrument else "未知仪器"
            instrument_no = instrument.instrument_no if instrument else "未知编号"
            if record.valid_until:
                valid_until_str = record.valid_until.strftime("%Y-%m-%d")
                days_left = (record.valid_until - now_utc).days
                days_str = f"剩余 {days_left} 天"
            else:
                valid_until_str = "未设置"
                days_str = ""
            content_lines.append(
                f"• **{instrument_name}** ({instrument_no})\n"
                f"  有效期至: {valid_until_str} {days_str}\n"
                f"  校准结论: {record.calibration_result}"
            )
            upcoming_count += 1

        total_count = overdue_count + upcoming_count
        content = "\n".join(content_lines)

        # 构建标题
        title_parts = []
        if overdue_count > 0:
            title_parts.append(f"超期 {overdue_count} 条")
        if upcoming_count > 0:
            title_parts.append(f"即将到期 {upcoming_count} 条")
        title = f"🔔 仪器校准提醒（{'，'.join(title_parts)}）"

        # 发送飞书卡片消息
        try:
            await send_feishu_card_from_config(
                app_id=feishu_app_id,
                app_secret=feishu_app_secret,
                receive_id=chat_id,
                receive_id_type=receive_id_type,
                title=title,
                content=content,
            )
            logger.info(
                f"成功发送校准提醒到 {receive_id_type}: {chat_id}，共 {total_count} 条记录（超期{overdue_count}条，即将到期{upcoming_count}条）"
            )

            return ApiResponse(
                message="发送成功",
                data={
                    "sent": True,
                    "count": total_count,
                    "overdue_count": overdue_count,
                    "upcoming_count": upcoming_count,
                    "chat_id": chat_id,
                    "receive_id_type": receive_id_type,
                },
            )
        except Exception as e:
            logger.error(f"发送飞书提醒失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")


# ========== 自动提醒触发 API ==========


@router.post("/reminder/auto-trigger", response_model=ApiResponse)
async def auto_trigger_reminders(
    service: ReminderConfigService = Depends(get_reminder_config_service),
    record_service: CalibrationRecordService = Depends(get_record_service),
):
    """触发自动提醒（可由定时任务调用）"""
    from datetime import datetime

    logger = logging.getLogger(__name__)

    # 获取所有启用的配置
    configs = await service.list_active_configs()

    results = []
    now = datetime.now()

    for config in configs:
        if not config.chat_id:
            continue

        config_results = {"config_name": config.name, "sent": [], "errors": []}

        # 30天提醒
        if config.remind_30_days:
            if (
                not config.last_remind_30_days
                or (now - config.last_remind_30_days).days >= 1
            ):
                try:
                    records = await record_service.get_upcoming_records(days=30)
                    # 只取刚好30天左右的记录
                    records_30 = [
                        r
                        for r in records
                        if r.valid_until
                        and 28 <= (r.valid_until.replace(tzinfo=None) - now).days <= 32
                    ]
                    if records_30:
                        await _send_reminder(records_30, config, "30天")
                        await service.repository.update(
                            config.id, {"last_remind_30_days": now}
                        )
                        config_results["sent"].append(f"30天提醒: {len(records_30)}条")
                except Exception as e:
                    config_results["errors"].append(f"30天提醒失败: {str(e)}")

        # 14天提醒
        if config.remind_14_days:
            if (
                not config.last_remind_14_days
                or (now - config.last_remind_14_days).days >= 1
            ):
                try:
                    records = await record_service.get_upcoming_records(days=14)
                    records_14 = [
                        r
                        for r in records
                        if r.valid_until
                        and 12 <= (r.valid_until.replace(tzinfo=None) - now).days <= 16
                    ]
                    if records_14:
                        await _send_reminder(records_14, config, "14天")
                        await service.repository.update(
                            config.id, {"last_remind_14_days": now}
                        )
                        config_results["sent"].append(f"14天提醒: {len(records_14)}条")
                except Exception as e:
                    config_results["errors"].append(f"14天提醒失败: {str(e)}")

        # 7天提醒
        if config.remind_7_days:
            if (
                not config.last_remind_7_days
                or (now - config.last_remind_7_days).days >= 1
            ):
                try:
                    records = await record_service.get_upcoming_records(days=7)
                    records_7 = [
                        r
                        for r in records
                        if r.valid_until
                        and 5 <= (r.valid_until.replace(tzinfo=None) - now).days <= 9
                    ]
                    if records_7:
                        await _send_reminder(records_7, config, "7天")
                        await service.repository.update(
                            config.id, {"last_remind_7_days": now}
                        )
                        config_results["sent"].append(f"7天提醒: {len(records_7)}条")
                except Exception as e:
                    config_results["errors"].append(f"7天提醒失败: {str(e)}")

        # 超期提醒
        if config.remind_overdue:
            if (
                not config.last_remind_overdue
                or (now - config.last_remind_overdue).days >= 1
            ):
                try:
                    from app.modules.quality.qms.instrument_repository import (
                        CalibrationRecordRepository,
                    )

                    repo = CalibrationRecordRepository(record_service.session)
                    # 查询已超期的记录
                    overdue_records = []
                    result = await record_service.session.execute(
                        select(InstrumentCalibrationRecord)
                        .options(selectinload(InstrumentCalibrationRecord.instrument))
                        .where(
                            and_(
                                InstrumentCalibrationRecord.is_deleted == False,
                                InstrumentCalibrationRecord.status == "active",
                                InstrumentCalibrationRecord.valid_until.isnot(None),
                                InstrumentCalibrationRecord.valid_until < now,
                            )
                        )
                        .order_by(InstrumentCalibrationRecord.valid_until)
                    )
                    overdue_records = list(result.scalars().all())
                    if overdue_records:
                        await _send_reminder(
                            overdue_records, config, "已超期", is_overdue=True
                        )
                        await service.repository.update(
                            config.id, {"last_remind_overdue": now}
                        )
                        config_results["sent"].append(
                            f"超期提醒: {len(overdue_records)}条"
                        )
                except Exception as e:
                    config_results["errors"].append(f"超期提醒失败: {str(e)}")

        results.append(config_results)

    return ApiResponse(message="自动提醒执行完成", data={"results": results})


async def _send_reminder(records, config, reminder_type, is_overdue=False):
    """发送提醒的内部函数"""
    from datetime import datetime

    from app.platform.notification.feishu_client_config import (
        send_feishu_card_from_config,
    )

    content_lines = []
    for record in records:
        instrument = record.instrument
        instrument_name = instrument.instrument_name if instrument else "未知仪器"
        instrument_no = instrument.instrument_no if instrument else "未知编号"

        if record.valid_until:
            valid_until_str = record.valid_until.strftime("%Y-%m-%d")
            if is_overdue:
                days_ago = (
                    datetime.now() - record.valid_until.replace(tzinfo=None)
                ).days
                days_str = f"已超期 {days_ago} 天"
            else:
                days_left = (
                    record.valid_until.replace(tzinfo=None) - datetime.now()
                ).days
                days_str = f"剩余 {days_left} 天"
        else:
            valid_until_str = "未设置"
            days_str = ""

        content_lines.append(
            f"• **{instrument_name}** ({instrument_no})\n"
            f"  有效期至: {valid_until_str} {days_str}\n"
            f"  校准结论: {record.calibration_result}"
        )

    content = "\n\n".join(content_lines)

    await send_feishu_card_from_config(
        app_id=config.feishu_app_id,
        app_secret=config.feishu_app_secret,
        receive_id=config.chat_id,
        receive_id_type=config.receive_id_type,
        title=f"🔔 仪器校准{reminder_type}提醒（共 {len(records)} 条）",
        content=content,
    )
