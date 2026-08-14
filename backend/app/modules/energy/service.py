"""Energy business workflows live here."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateException, NotFoundException
from app.core.llm.client import LLMClient
from app.modules.energy import repository as repo
from app.modules.energy.adapters import ADAPTERS
from app.modules.energy.models import (
    EnergyAlertRecord,
    EnergyAlertRule,
    EnergyCollectLog,
    EnergyData,
    EnergyDeviceConfig,
    EnergyMonthlyRecord,
    EnergyUnitConsumptionTarget,
    EnergyWorkshop,
)
from app.modules.energy.schemas import (
    AlertRecordProcessRequest,
    CollectTriggerRequest,
    EnergyAlertRuleCreate,
    EnergyAlertRuleUpdate,
    EnergyDeviceConfigCreate,
    EnergyDeviceConfigUpdate,
    EnergyMonthlyRecordCreate,
    EnergyWorkshopCreate,
    EnergyWorkshopUpdate,
)

logger = logging.getLogger(__name__)

# 中国标准时间 timezone.utc+8
CST = timezone(timedelta(hours=8))


async def create_device_config(db: AsyncSession, data: EnergyDeviceConfigCreate) -> EnergyDeviceConfig:
    if await repo.exists_device_config(db, data.platform_code, data.platform_device_code):
        raise DuplicateException(
            "设备配置",
            f"{data.platform_code}:{data.platform_device_code}",
        )
    return await repo.create_device_config(db, data.model_dump())


async def get_device_config(db: AsyncSession, config_id: UUID) -> EnergyDeviceConfig:
    obj = await repo.get_device_config_by_id(db, config_id)
    if obj is None:
        raise NotFoundException("设备配置", str(config_id))
    return obj


async def list_device_configs(
    db: AsyncSession,
    *,
    platform_code: str | None = None,
    energy_type: str | None = None,
    workshop: str | None = None,
    is_enabled: bool | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EnergyDeviceConfig], int]:
    return await repo.list_device_configs(
        db,
        platform_code=platform_code,
        energy_type=energy_type,
        workshop=workshop,
        is_enabled=is_enabled,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


async def update_device_config(db: AsyncSession, config_id: UUID, data: EnergyDeviceConfigUpdate) -> EnergyDeviceConfig:
    existing = await repo.get_device_config_by_id(db, config_id)
    if existing is None:
        raise NotFoundException("设备配置", str(config_id))

    update_data = data.model_dump(exclude_unset=True)
    if "platform_code" in update_data or "platform_device_code" in update_data:
        pc = update_data.get("platform_code", existing.platform_code)
        pdc = update_data.get("platform_device_code", existing.platform_device_code)
        if await repo.exists_device_config(db, pc, pdc, exclude_id=config_id):
            raise DuplicateException("设备配置", f"{pc}:{pdc}")

    result = await repo.update_device_config(db, config_id, update_data)
    assert result is not None  # already verified existence above
    return result


async def delete_device_config(db: AsyncSession, config_id: UUID) -> None:
    obj = await repo.get_device_config_by_id(db, config_id)
    if obj is None:
        raise NotFoundException("设备配置", str(config_id))
    await repo.delete_device_config(db, config_id)


def get_target_hour() -> datetime:
    """获取目标采集小时：上一个整点（时区感知）。"""
    now = datetime.now(CST)
    return now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)


async def trigger_collection(db: AsyncSession, request: CollectTriggerRequest) -> dict[str, Any]:
    """触发采集任务"""
    target_hour = get_target_hour()

    if request.platform_code:
        platform_codes = [request.platform_code]
    else:
        platform_codes = list(ADAPTERS.keys())

    results: dict[str, Any] = {}
    for platform_code in platform_codes:
        adapter = ADAPTERS.get(platform_code)
        if adapter is None:
            results[platform_code] = {
                "status": "failed",
                "error": f"未找到平台适配器: {platform_code}",
            }
            continue

        devices = await repo.get_enabled_devices_by_platform(db, platform_code)
        if not devices:
            results[platform_code] = {
                "status": "success",
                "device_count": 0,
                "success_count": 0,
            }
            continue

        device_codes = [d.platform_device_code for d in devices]
        device_map = {d.platform_device_code: d for d in devices}
        api_endpoint = devices[0].api_endpoint

        try:
            collect_results = await adapter.fetch_energy_data(device_codes, target_hour, api_endpoint)

            success_count = 0
            for cr in collect_results:
                device = device_map.get(cr.device_code)
                if device is None:
                    continue
                await repo.upsert_energy_data(
                    db,
                    device_config_id=device.id,
                    timestamp=cr.timestamp,
                    value=cr.value,
                    unit=cr.unit,
                    platform_raw_data=cr.raw_data,
                )
                success_count += 1

            status = "success" if success_count == len(device_codes) else "partial"
            await repo.create_collect_log(
                db,
                {
                    "platform_code": platform_code,
                    "collect_time": datetime.now(),
                    "status": status,
                    "device_count": len(device_codes),
                    "success_count": success_count,
                },
            )
            results[platform_code] = {
                "status": status,
                "device_count": len(device_codes),
                "success_count": success_count,
            }

        except Exception as e:
            logger.exception("采集失败: platform=%s", platform_code)
            await repo.create_collect_log(
                db,
                {
                    "platform_code": platform_code,
                    "collect_time": datetime.now(),
                    "status": "failed",
                    "device_count": len(device_codes),
                    "success_count": 0,
                    "error_message": str(e),
                },
            )
            results[platform_code] = {
                "status": "failed",
                "device_count": len(device_codes),
                "success_count": 0,
                "error": str(e),
            }

    return results


async def list_energy_data(
    db: AsyncSession,
    *,
    device_config_id: UUID | None = None,
    energy_type: str | None = None,
    workshop: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EnergyData], int]:
    return await repo.list_energy_data(
        db,
        device_config_id=device_config_id,
        energy_type=energy_type,
        workshop=workshop,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )


async def get_energy_statistics(
    db: AsyncSession,
    *,
    group_by: str = "workshop",
    energy_type: str | None = None,
    start_time: datetime,
    end_time: datetime,
) -> list[dict[str, Any]]:
    return await repo.get_energy_statistics(
        db,
        group_by=group_by,
        energy_type=energy_type,
        start_time=start_time,
        end_time=end_time,
    )


async def list_collect_logs(
    db: AsyncSession,
    *,
    platform_code: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EnergyCollectLog], int]:
    return await repo.list_collect_logs(
        db,
        platform_code=platform_code,
        status=status,
        page=page,
        page_size=page_size,
    )


async def get_collect_log_detail(db: AsyncSession, log_id: UUID) -> dict[str, Any]:
    """获取采集日志详情，包含设备数据和时间范围。"""
    log, rows = await repo.get_collect_log_detail(db, log_id)
    if log is None:
        raise NotFoundException("采集日志", str(log_id))

    devices: list[dict[str, Any]] = []
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None

    for energy_data, device_config in rows:
        devices.append(
            {
                "device_name": device_config.device_name,
                "platform_device_code": device_config.platform_device_code,
                "energy_type": device_config.energy_type,
                "value": float(energy_data.value),
                "unit": energy_data.unit,
                "data_timestamp": energy_data.timestamp,
            }
        )
        if time_range_start is None or energy_data.timestamp < time_range_start:
            time_range_start = energy_data.timestamp
        if time_range_end is None or energy_data.timestamp > time_range_end:
            time_range_end = energy_data.timestamp

    return {
        "id": str(log.id),
        "platform_code": log.platform_code,
        "collect_time": log.collect_time,
        "status": log.status,
        "device_count": log.device_count,
        "success_count": log.success_count,
        "error_message": log.error_message,
        "created_at": log.created_at,
        "devices": devices,
        "time_range_start": time_range_start,
        "time_range_end": time_range_end,
    }


# ── 总览 ──


async def get_overview(
    db: AsyncSession,
    start_time: datetime,
    end_time: datetime,
    energy_type: str | None = None,
) -> dict[str, Any]:
    summary_rows = await repo.get_overview_summary(db, start_time, end_time)
    summary: dict[str, float] = {"electricity": 0, "water": 0, "steam": 0, "natural_gas": 0}
    for row in summary_rows:
        et = row["energy_type"]
        if et in summary:
            summary[et] = row["total_value"]

    trend_rows = await repo.get_overview_trend(db, start_time, end_time, energy_type=energy_type)

    distribution_rows = await repo.get_energy_statistics(
        db,
        group_by="workshop",
        start_time=start_time,
        end_time=end_time,
        energy_type=energy_type,
    )

    return {
        "summary": {
            "total_electricity": summary["electricity"],
            "total_water": summary["water"],
            "total_steam": summary["steam"],
            "total_natural_gas": summary["natural_gas"],
        },
        "trend": trend_rows,
        "distribution": distribution_rows,
    }


# ── 预警规则 ──


async def create_alert_rule(db: AsyncSession, data: EnergyAlertRuleCreate) -> EnergyAlertRule:
    return await repo.create_alert_rule(db, data.model_dump())


async def get_alert_rule(db: AsyncSession, rule_id: UUID) -> EnergyAlertRule:
    obj = await repo.get_alert_rule_by_id(db, rule_id)
    if obj is None:
        raise NotFoundException("预警规则", str(rule_id))
    return obj


async def list_alert_rules(
    db: AsyncSession,
    *,
    energy_type: str | None = None,
    alert_level: str | None = None,
    is_enabled: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EnergyAlertRule], int]:
    return await repo.list_alert_rules(
        db,
        energy_type=energy_type,
        alert_level=alert_level,
        is_enabled=is_enabled,
        page=page,
        page_size=page_size,
    )


async def update_alert_rule(db: AsyncSession, rule_id: UUID, data: EnergyAlertRuleUpdate) -> EnergyAlertRule:
    existing = await repo.get_alert_rule_by_id(db, rule_id)
    if existing is None:
        raise NotFoundException("预警规则", str(rule_id))
    result = await repo.update_alert_rule(db, rule_id, data.model_dump(exclude_unset=True))
    assert result is not None
    return result


async def delete_alert_rule(db: AsyncSession, rule_id: UUID) -> None:
    obj = await repo.get_alert_rule_by_id(db, rule_id)
    if obj is None:
        raise NotFoundException("预警规则", str(rule_id))
    await repo.delete_alert_rule(db, rule_id)


# ── 预警记录 ──


async def list_alert_records(
    db: AsyncSession,
    *,
    energy_type: str | None = None,
    alert_level: str | None = None,
    status: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EnergyAlertRecord], int]:
    return await repo.list_alert_records(
        db,
        energy_type=energy_type,
        alert_level=alert_level,
        status=status,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )


async def process_alert_record(
    db: AsyncSession, record_id: UUID, request: AlertRecordProcessRequest
) -> EnergyAlertRecord:
    existing = await repo.get_alert_record_by_id(db, record_id)
    if existing is None:
        raise NotFoundException("预警记录", str(record_id))
    result = await repo.update_alert_record(
        db,
        record_id,
        {
            "status": request.status,
            "process_note": request.process_note,
            "processed_at": datetime.now(),
        },
    )
    assert result is not None
    return result


# ── 车间管理 ──


async def create_workshop(db: AsyncSession, data: EnergyWorkshopCreate) -> EnergyWorkshop:
    # 检查编码是否已存在
    existing = await repo.get_workshop_by_code(db, data.code)
    if existing:
        raise DuplicateException("车间编码", data.code)
    return await repo.create_workshop(db, data.model_dump())


async def get_workshop(db: AsyncSession, workshop_id: UUID) -> EnergyWorkshop:
    obj = await repo.get_workshop_by_id(db, workshop_id)
    if obj is None:
        raise NotFoundException("车间", str(workshop_id))
    return obj


async def list_workshops(
    db: AsyncSession,
    *,
    category: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[EnergyWorkshop], int]:
    return await repo.list_workshops(
        db,
        category=category,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


async def update_workshop(db: AsyncSession, workshop_id: UUID, data: EnergyWorkshopUpdate) -> EnergyWorkshop:
    existing = await repo.get_workshop_by_id(db, workshop_id)
    if existing is None:
        raise NotFoundException("车间", str(workshop_id))

    update_data = data.model_dump(exclude_unset=True)

    # 如果更新编码，检查是否冲突
    if "code" in update_data:
        code_existing = await repo.get_workshop_by_code(db, update_data["code"])
        if code_existing and code_existing.id != workshop_id:
            raise DuplicateException("车间编码", update_data["code"])

    result = await repo.update_workshop(db, workshop_id, update_data)
    assert result is not None
    return result


async def delete_workshop(db: AsyncSession, workshop_id: UUID) -> None:
    obj = await repo.get_workshop_by_id(db, workshop_id)
    if obj is None:
        raise NotFoundException("车间", str(workshop_id))
    await repo.delete_workshop(db, workshop_id)


# ── 月度记录 ──


async def create_monthly_record(db: AsyncSession, data: EnergyMonthlyRecordCreate) -> EnergyMonthlyRecord:
    # 验证车间是否存在
    workshop = await repo.get_workshop_by_id(db, data.workshop_id)  # type: ignore[arg-type]
    if workshop is None:
        raise NotFoundException("车间", data.workshop_id)
        raise NotFoundException("车间", str(data.workshop_id))
    return await repo.create_monthly_record(db, data.model_dump())


async def batch_create_monthly_records(
    db: AsyncSession, records: list[EnergyMonthlyRecordCreate]
) -> list[EnergyMonthlyRecord]:
    # 验证所有车间是否存在
    workshop_ids = {r.workshop_id for r in records}
    for workshop_id in workshop_ids:
        workshop = await repo.get_workshop_by_id(db, workshop_id)  # type: ignore[arg-type]
        if workshop is None:
            raise NotFoundException("车间", str(workshop_id))

    return await repo.batch_create_monthly_records(db, [r.model_dump() for r in records])


async def list_monthly_records(
    db: AsyncSession,
    *,
    workshop_id: UUID | None = None,
    energy_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[EnergyMonthlyRecord], int]:
    return await repo.list_monthly_records(
        db,
        workshop_id=workshop_id,
        energy_type=energy_type,
        start_date=start_date,  # type: ignore[arg-type]
        end_date=end_date,  # type: ignore[arg-type]
        page=page,
        page_size=page_size,
    )


async def get_monthly_record(db: AsyncSession, record_id: UUID) -> EnergyMonthlyRecord:
    obj = await repo.get_monthly_record_by_id(db, record_id)
    if obj is None:
        raise NotFoundException("月度记录", str(record_id))
    return obj


async def delete_monthly_record(db: AsyncSession, record_id: UUID) -> None:
    obj = await repo.get_monthly_record_by_id(db, record_id)
    if obj is None:
        raise NotFoundException("月度记录", str(record_id))
    await repo.delete_monthly_record(db, record_id)


async def get_monthly_summary(
    db: AsyncSession,
    workshop_id: UUID | None = None,
    energy_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """获取月度记录汇总，按能源类型分组统计总量"""
    return await repo.get_monthly_summary(
        db,
        workshop_id=workshop_id,
        energy_type=energy_type,
        start_date=start_date,
        end_date=end_date,
    )


# ── AI 分析相关服务 ──


async def prepare_daily_stats(
    db: AsyncSession, workshop_id: UUID, start_date: date, end_date: date, energy_types: list[str]
) -> list[dict[str, Any]]:
    """准备每日统计数据，处理跨天记录的平均拆分"""

    from app.modules.energy.models import EnergyMonthlyRecord

    query = select(EnergyMonthlyRecord).where(
        EnergyMonthlyRecord.workshop_id == workshop_id,
        EnergyMonthlyRecord.record_date <= end_date,
        (EnergyMonthlyRecord.date_range_end >= start_date) | (EnergyMonthlyRecord.date_range_end.is_(None)),
        EnergyMonthlyRecord.energy_type.in_(energy_types),
    )

    result = await db.execute(query)
    records = result.scalars().all()

    daily_map: dict[str, Any] = {}  # {date_str: {energy_type: value}}

    for record in records:
        s_date = record.record_date
        e_date = record.date_range_end or s_date

        # 计算天数并平均拆分
        if not record.value:
            continue
        days = (e_date - s_date).days + 1
        if days <= 0:
            continue
        avg_value = round(float(record.value) / days, 4)

        current = s_date
        while current <= e_date:
            if start_date <= current <= end_date:
                date_str = current.isoformat()
                if date_str not in daily_map:
                    daily_map[date_str] = {}

                if record.energy_type not in daily_map[date_str]:
                    daily_map[date_str][record.energy_type] = 0
                daily_map[date_str][record.energy_type] += avg_value
            current += timedelta(days=1)

    return [{"date": k, **v} for k, v in sorted(daily_map.items())]


async def fetch_mock_production(workshop_name: str, dates: list[str]) -> list[dict[str, Any]]:
    """获取模拟产量数据"""
    import random

    production_data = []
    for d in dates:
        production_data.append(
            {
                "date": d,
                "workshop": workshop_name,
                "weight": round(random.uniform(1000, 5000), 2),  # 模拟随机产量
                "unit": "kg",
            }
        )
    return production_data


async def analyze_energy_with_ai(
    daily_stats: list[Any],
    production_data: list[Any],
    weather_info: str = "",
) -> dict[str, Any]:
    """调用 LLM 进行能耗偏差分析"""
    client = LLMClient()

    prompt = (
        f"你是一位专业的能源管理专家。请根据以下数据进行分析：\n"
        f"1. 每日能耗数据: {json.dumps(daily_stats, ensure_ascii=False)}\n"
        f"2. 每日产量数据: {json.dumps(production_data, ensure_ascii=False)}\n"
        f"3. 天气参考信息: {weather_info or '未知'}\n\n"
        f"请完成以下任务：\n"
        f"1. 计算“单位产量能耗”（总能耗/总产量）。\n"
        f"2. 识别是否存在能耗波动异常或偏差。\n"
        f"3. 结合产量变化和可能的天气因素，分析异常原因。\n\n"
        f"请以 JSON 格式返回结果，包含字段：summary, unit_consumption_trend, anomalies"
    )

    messages = [{"role": "user", "content": prompt}]

    try:
        response_text = await client.chat(messages, temperature=0.3)
        content = response_text.replace("```json", "").replace("```", "").strip()
        try:
            result: dict[str, Any] = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"LLM JSON 解析失败: {e}, 原始内容: {content[:200]}")
            return {"error": "AI 响应格式错误", "summary": "请稍后重试"}
    except Exception as e:
        return {"error": f"AI 分析失败: {str(e)}", "summary": "分析过程中出现错误。"}


async def analyze_energy_with_vision(image_base64: str, prompt: str) -> dict[str, Any]:
    """利用多模态大模型分析能耗图表截图"""
    client = LLMClient()

    # 构造 Data URI 格式的图片 URL
    image_url = f"data:image/png;base64,{image_base64}"

    try:
        # 调用专门的多模态接口
        response_text = await client.chat_vision(text_prompt=prompt, image_urls=[image_url])

        # 尝试解析 JSON 结果
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        result: dict[str, Any] = json.loads(cleaned)
        return result
    except Exception as e:
        return {"error": f"视觉分析失败: {str(e)}", "summary": "无法解析图表内容。"}


# ── 单耗目标管理 ──


async def create_target(
    db: AsyncSession, workshop_id: UUID, target_month: str, target_unit_consumption: float
) -> EnergyUnitConsumptionTarget:
    """创建单耗目标"""

    # 验证车间是否存在
    workshop = await get_workshop_by_id(db, workshop_id)
    if not workshop:
        raise NotFoundException("车间", str(workshop_id))

    # 检查是否已存在同车间同月份的目标
    existing = await get_target(db, workshop_id, target_month)
    if existing:
        raise DuplicateException("单耗目标", f"车间{workshop_id}在{target_month}已存在目标")

    # 解析月份字符串为日期（存储为该月第一天）
    year, month = map(int, target_month.split("-"))
    target_date = date(year, month, 1)

    target = await repo.create_unit_consumption_target(db, workshop_id, target_date, target_unit_consumption)
    await db.commit()

    # Re-fetch after commit
    if target.id:
        _target = await repo.get_unit_consumption_target_by_id(db, target.id)
        if _target:
            target = _target
    assert target is not None

    return target


async def get_target(db: AsyncSession, workshop_id: UUID, target_month: str) -> EnergyUnitConsumptionTarget | None:
    """查询单耗目标"""
    year, month = map(int, target_month.split("-"))
    target_date = date(year, month, 1)

    query = select(EnergyUnitConsumptionTarget).where(
        EnergyUnitConsumptionTarget.workshop_id == workshop_id,
        EnergyUnitConsumptionTarget.target_month == target_date,
    )

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_target(db: AsyncSession, target_id: UUID, new_value: float) -> EnergyUnitConsumptionTarget:
    """更新单耗目标"""
    query = select(EnergyUnitConsumptionTarget).where(EnergyUnitConsumptionTarget.id == target_id)

    result = await db.execute(query)
    target = result.scalar_one_or_none()

    if not target:
        raise NotFoundException("单耗目标", str(target_id))

    target = await repo.update_unit_consumption_target(db, target_id, new_value)
    await db.commit()

    if target is None:
        raise NotFoundException("单耗目标", str(target_id))

    return target


async def get_workshop_by_id(db: AsyncSession, workshop_id: UUID) -> EnergyWorkshop | None:
    """根据 ID 查询车间"""
    query = select(EnergyWorkshop).where(EnergyWorkshop.id == workshop_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def calculate_unit_consumption(total_energy_kwh: float, production: int) -> float:
    """计算实际单耗"""
    if not isinstance(production, int) or production <= 0:
        raise ValueError("产量必须为正整数")

    try:
        result = total_energy_kwh / production
        return round(result, 4)
    except ZeroDivisionError:
        # 防御性编程，理论上不会到达这里
        raise ValueError("产量不能为零")
    except Exception as e:
        logger.error(f"单耗计算失败: {e}")
        raise ValueError("单耗计算失败")


def calculate_deviation_rate(actual: float, target: float) -> float:
    """计算偏差率（百分比）"""
    if target <= 0:
        raise ValueError("目标值必须为正数")
    return round(((actual - target) / target) * 100, 2)


def determine_deviation_status(deviation_rate: float | None) -> str:
    """判定偏差状态"""
    if deviation_rate is None:
        return "unknown"

    abs_rate = abs(deviation_rate)
    if abs_rate <= 5:
        return "normal"
    elif abs_rate <= 15:
        return "warning"
    else:
        return "critical"


async def prepare_ai_analysis_data(
    db: AsyncSession, workshop_id: UUID, analysis_month: str, production_items: list[dict[str, Any]]
) -> dict[str, Any]:
    """准备 AI 分析所需的所有数据"""

    # 1. 获取车间信息
    workshop = await get_workshop_by_id(db, workshop_id)
    if not workshop:
        raise NotFoundException("车间", str(workshop_id))

    # 2. 查询当月总能耗
    year, month = map(int, analysis_month.split("-"))
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    total_energy = await repo.get_monthly_energy_total(db, workshop_id, month_start, month_end)

    if total_energy is None or total_energy == 0:
        raise NotFoundException("能耗数据", f"{workshop.name}在{analysis_month}无能耗数据")

    total_energy_kwh = float(total_energy)

    # 3. 计算折算总产量
    from sqlalchemy import select

    from app.modules.energy.models import EnergyProductConversion

    converted_production = 0.0
    product_details = []

    for item in production_items:
        product_name = item.get("product_name")
        quantity = float(item.get("quantity", 0))

        # 获取折算系数
        stmt = select(EnergyProductConversion).where(
            EnergyProductConversion.product_name == product_name, EnergyProductConversion.is_active
        )
        result = await db.execute(stmt)
        conv_record = result.scalars().first()

        factor = float(conv_record.conversion_factor) if conv_record else 1.0
        converted_qty = quantity * factor

        converted_production += converted_qty
        product_details.append(
            {"product_name": product_name, "quantity": quantity, "factor": factor, "converted_qty": converted_qty}
        )

    if converted_production <= 0:
        raise ValueError("折算后总产量不能为 0")

    # 4. 计算实际单耗
    actual_unit_consumption = await calculate_unit_consumption(total_energy_kwh, int(converted_production))

    # 4. 查询目标值
    target_record = await get_target(db, workshop_id, analysis_month)
    target_unit_consumption = None
    deviation_rate = None
    deviation_status = "unknown"

    if target_record:
        target_unit_consumption = float(target_record.target_unit_consumption)
        deviation_rate = calculate_deviation_rate(actual_unit_consumption, target_unit_consumption)
        deviation_status = determine_deviation_status(deviation_rate)

    return {
        "workshop_id": workshop_id,
        "workshop_name": workshop.name,
        "analysis_month": analysis_month,
        "total_energy_kwh": total_energy_kwh,
        "production_details": product_details,
        "converted_production": converted_production,
        "actual_unit_consumption": actual_unit_consumption,
        "target_unit_consumption": target_unit_consumption,
        "deviation_rate": deviation_rate,
        "deviation_status": deviation_status,
    }


def construct_ai_prompt(analysis_data: dict[str, Any]) -> str:
    """构造 AI Prompt（包含多产品明细）"""
    has_target = analysis_data["target_unit_consumption"] is not None

    # 构造产品明细字符串
    product_details = ""
    for item in analysis_data.get("production_details", []):
        product_details += (
            f"- {item['name']}: {item['quantity']} kg\n"
            f"  (系数: {item['factor']}, 折算后: {item['converted_qty']:.2f} kg)\n"
        )

    prompt = f"""你是一名能源管理专家。请根据以下数据分析车间的能源使用效率，并提供优化建议。

【基础信息】
- 车间名称：{analysis_data["workshop_name"]}
- 分析月份：{analysis_data["analysis_month"]}

【产品结构】
{product_details}

【能耗数据】
- 当月总能耗：{analysis_data["total_energy_kwh"]:.2f} kWh
- 折算总产量：{analysis_data["converted_production"]:.2f} kg
- 实际单耗：{analysis_data["actual_unit_consumption"]:.4f} kWh/kg

【目标对比】
"""

    if has_target:
        prompt += f"""- 目标单耗：{analysis_data["target_unit_consumption"]:.4f} kWh/kg
- 偏差率：{analysis_data["deviation_rate"]:+.2f}%
- 偏差状态：{analysis_data["deviation_status"]}

【分析要求】
1. 分析可能导致偏差的原因（至少 2-3 个）
2. 提供具体的改进建议（3-5 条，可操作）
3. 评估建议的预期效果
"""
    else:
        prompt += """- 目标单耗：未设定
- 偏差分析：无法进行（缺少目标值）

【分析要求】
1. 解释为什么需要设定目标
2. 建议如何确定合理的目标值
3. 提供行业参考标准（如有）
"""

    prompt += """
【输出格式】
请以 JSON 格式返回，包含以下字段：
- summary: 一句话总结（不超过 50 字）
- detailed_analysis: 详细分析（200-500 字）
- recommendations: 建议列表（数组，3-5 条）
- confidence_level: 置信度（high/medium/low）

【注意事项】
- 语言简洁专业，避免空泛表述
- 建议必须具体可执行，避免"加强管理"等模糊表述
- 如果数据异常（如单耗极高或极低），请在分析中指出
"""

    return prompt


async def analyze_energy_v2(
    db: AsyncSession,
    workshop_id: UUID,
    analysis_month: str,
    production_items: list[dict[str, Any]],
    include_ai_suggestion: bool = True,
) -> dict[str, Any]:
    """执行 AI 能耗分析 V2（支持多产品和单耗计算）"""
    from app.core.llm import LLMClient
    from app.modules.energy.schemas import AISuggestion

    # 1. 准备分析数据
    analysis_data = await prepare_ai_analysis_data(db, workshop_id, analysis_month, production_items)

    # 2. 生成 AI 建议（如果请求）
    ai_suggestion = None
    if include_ai_suggestion:
        try:
            prompt = construct_ai_prompt(analysis_data)
            client = LLMClient()
            messages = [{"role": "user", "content": prompt}]

            response_text = await client.chat(messages, temperature=0.3)
            content = response_text.replace("```json", "").replace("```", "").strip()

            import json
            try:
                ai_result = json.loads(content)
                ai_suggestion = AISuggestion(
                    status=analysis_data["deviation_status"],
                    summary=ai_result.get("summary", ""),
                    detailed_analysis=ai_result.get("detailed_analysis", ""),
                    recommendations=ai_result.get("recommendations", []),
                    confidence_level=ai_result.get("confidence_level", "medium"),
                )
            except json.JSONDecodeError:
                ai_suggestion = AISuggestion(
                    status=analysis_data["deviation_status"],
                    summary="AI 分析暂时不可用",
                    detailed_analysis="请稍后重试",
                    recommendations=[],
                    confidence_level="low",
                )
        except Exception as e:
            ai_suggestion = AISuggestion(
                status=analysis_data["deviation_status"],
                summary=f"AI 分析失败: {str(e)}",
                detailed_analysis="",
                recommendations=[],
                confidence_level="low",
            )

    # 3. 构造产品明细（用于响应）
    production_items_detail = []
    for item in analysis_data["production_details"]:
        production_items_detail.append({
            "product_name": item["product_name"],
            "quantity": item["quantity"],
            "unit": "kg",
            "conversion_factor": item["factor"],
            "converted_quantity": item["converted_qty"],
        })

    return {
        "workshop_id": str(analysis_data["workshop_id"]),
        "workshop_name": analysis_data["workshop_name"],
        "analysis_month": analysis_data["analysis_month"],
        "total_energy_kwh": analysis_data["total_energy_kwh"],
        "production_items": production_items_detail,
        "converted_production": analysis_data["converted_production"],
        "actual_unit_consumption": analysis_data["actual_unit_consumption"],
        "target_unit_consumption": analysis_data["target_unit_consumption"],
        "deviation_rate": analysis_data["deviation_rate"],
        "deviation_status": analysis_data["deviation_status"],
        "ai_suggestion": ai_suggestion,
    }
