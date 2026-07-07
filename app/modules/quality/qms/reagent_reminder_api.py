"""试剂提醒管理 API

提供试剂库存不足时的飞书提醒配置和手动触发接口
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.reagent_reminder_service import ReagentReminderService
from app.platform.database import get_db_session

router = APIRouter(prefix="/reagent-reminder", tags=["试剂提醒管理"])


# ============ 请求模型 ============


class ReminderConfigRequest(BaseModel):
    """提醒配置请求"""

    feishu_app_id: str = Field(..., description="飞书应用 AppID")
    feishu_app_secret: str = Field(..., description="飞书应用 AppSecret")
    feishu_chat_id: str = Field(..., description="飞书群 ID")
    low_stock_threshold: int = Field(default=2, description="库存不足阈值")
    is_enabled: bool = Field(default=True, description="是否启用")


class ItemReminderRequest(BaseModel):
    """单个试剂提醒配置请求"""

    reagent_name: str = Field(..., description="试剂名称")
    is_enabled: bool = Field(default=True, description="是否启用提醒")


# ============ API 接口 ============


@router.get("/config", summary="获取提醒配置")
async def get_config(session: AsyncSession = Depends(get_db_session)):
    """获取当前的提醒配置"""
    service = ReagentReminderService(session)
    config = await service.get_config()

    if not config:
        return {"code": 200, "message": "success", "data": None}

    return {
        "code": 200,
        "message": "success",
        "data": {
            "feishu_app_id": config.feishu_app_id,
            "feishu_app_secret": config.feishu_app_secret,
            "feishu_chat_id": config.feishu_chat_id,
            "low_stock_threshold": config.low_stock_threshold,
            "is_enabled": config.is_enabled,
            "last_remind_time": config.last_remind_time.isoformat()
            if config.last_remind_time
            else None,
            "last_remind_content": config.last_remind_content,
        },
    }


@router.post("/config", summary="保存提醒配置")
async def save_config(
    request: ReminderConfigRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """保存提醒配置"""
    service = ReagentReminderService(session)
    config = await service.create_or_update_config(
        feishu_app_id=request.feishu_app_id,
        feishu_app_secret=request.feishu_app_secret,
        feishu_chat_id=request.feishu_chat_id,
        low_stock_threshold=request.low_stock_threshold,
        is_enabled=request.is_enabled,
    )

    return {
        "code": 200,
        "message": "保存成功",
        "data": {
            "id": config.id,
            "feishu_app_id": config.feishu_app_id,
            "feishu_chat_id": config.feishu_chat_id,
            "low_stock_threshold": config.low_stock_threshold,
            "is_enabled": config.is_enabled,
        },
    }


@router.post("/check", summary="手动检查并发送提醒")
async def check_and_remind(session: AsyncSession = Depends(get_db_session)):
    """手动触发库存检查和提醒"""
    service = ReagentReminderService(session)
    result = await service.check_and_remind()
    return result


@router.get("/low-stock", summary="获取库存不足的试剂列表")
async def get_low_stock_reagents(
    threshold: int = 2,
    session: AsyncSession = Depends(get_db_session),
):
    """获取库存不足的试剂列表（用于预览，包含每个试剂的提醒开关状态）"""
    service = ReagentReminderService(session)
    items = await service.get_low_stock_reagents(threshold)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "count": len(items),
            "items": items,
        },
    }


@router.post("/item-reminder", summary="设置单个试剂的提醒开关")
async def set_item_reminder(
    request: ItemReminderRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """设置单个试剂的提醒开关（启用/禁用）"""
    service = ReagentReminderService(session)
    result = await service.set_item_reminder_enabled(
        request.reagent_name, request.is_enabled
    )
    return result


@router.get("/item-reminder/{reagent_name}", summary="获取单个试剂的提醒配置")
async def get_item_reminder(
    reagent_name: str,
    session: AsyncSession = Depends(get_db_session),
):
    """获取单个试剂的提醒配置"""
    service = ReagentReminderService(session)
    config = await service.get_item_reminder_config(reagent_name)

    if config:
        return {"code": 200, "message": "success", "data": config}
    else:
        # 默认返回启用状态
        return {
            "code": 200,
            "message": "success",
            "data": {
                "reagent_name": reagent_name,
                "is_enabled": True,
            },
        }
