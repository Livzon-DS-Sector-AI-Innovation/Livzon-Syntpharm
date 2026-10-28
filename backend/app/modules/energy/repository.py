"""Energy database queries and persistence."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.energy.models import (
    EnergyAlertRecord,
    EnergyAlertRule,
    EnergyCollectLog,
    EnergyDailyData,
    EnergyData,
    EnergyDeviceConfig,
    EnergyMonthlyRecord,
    EnergyUnitConsumptionTarget,
    EnergyWorkshop,
)

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=8))


def _cst_date(value: datetime) -> date:
    """把查询窗口端点换算成东八区日期。

    前端把本地零点 `toISOString()` 成 UTC，东八区零点是前一天 16:00 UTC；
    直接取 `.date()` 会让「今日」窗口变成「昨天 + 今天」。
    """
    if value.tzinfo is None:
        # 没带时区的值按调用方已给出的本地时间处理
        return value.date()
    return value.astimezone(CST).date()


def apply_changed_fields(obj: Any, values: dict[str, Any]) -> bool:
    """逐字段按需赋值，返回是否真的有字段发生变化。

    SQLAlchemy 只对值真变了的属性发 UPDATE，所以「匹配到已有行」不等于「更新了该行」；
    导入器用返回值计数（`D-51`）。
    """
    changed = False
    for field, value in values.items():
        if getattr(obj, field) != value:
            setattr(obj, field, value)
            changed = True
    return changed


# ── 设备配置 ──


async def create_device_config(db: AsyncSession, data: dict[str, Any]) -> EnergyDeviceConfig:
    obj = EnergyDeviceConfig(**data)
    db.add(obj)
    await db.flush()
    return obj


async def get_device_config_by_id(db: AsyncSession, config_id: UUID) -> EnergyDeviceConfig | None:
    result = await db.execute(
        select(EnergyDeviceConfig).where(
            EnergyDeviceConfig.id == config_id,
            EnergyDeviceConfig.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


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
    query = select(EnergyDeviceConfig).where(
        EnergyDeviceConfig.is_deleted == False  # noqa: E712
    )
    if platform_code:
        query = query.where(EnergyDeviceConfig.platform_code == platform_code)
    if energy_type:
        query = query.where(EnergyDeviceConfig.energy_type == energy_type)
    if workshop:
        query = query.where(EnergyDeviceConfig.workshop == workshop)
    if is_enabled is not None:
        query = query.where(EnergyDeviceConfig.is_enabled == is_enabled)
    if keyword:
        escaped_keyword = keyword.replace("%", "\\%").replace("_", "\\_")
        query = query.where(EnergyDeviceConfig.device_name.ilike(f"%{escaped_keyword}%", escape="\\"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_device_config(db: AsyncSession, config_id: UUID, data: dict[str, Any]) -> EnergyDeviceConfig | None:
    obj = await get_device_config_by_id(db, config_id)
    if obj is None:
        return None
    for key, value in data.items():
        setattr(obj, key, value)
    await db.flush()
    # Re-fetch via select to avoid MissingGreenlet (禁止 db.refresh)
    result = await db.execute(
        select(EnergyDeviceConfig).where(
            EnergyDeviceConfig.id == config_id,
            EnergyDeviceConfig.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def delete_device_config(db: AsyncSession, config_id: UUID) -> bool:
    obj = await get_device_config_by_id(db, config_id)
    if obj is None:
        return False
    obj.is_deleted = True
    await db.flush()
    return True


async def exists_device_config(
    db: AsyncSession,
    platform_code: str,
    platform_device_code: str,
    exclude_id: UUID | None = None,
) -> bool:
    query = select(func.count()).where(
        EnergyDeviceConfig.platform_code == platform_code,
        EnergyDeviceConfig.platform_device_code == platform_device_code,
        EnergyDeviceConfig.is_deleted == False,  # noqa: E712  # noqa: E712
    )
    if exclude_id:
        query = query.where(EnergyDeviceConfig.id != exclude_id)
    count = (await db.execute(query)).scalar() or 0
    return count > 0


async def get_enabled_devices_by_platform(db: AsyncSession, platform_code: str) -> list[EnergyDeviceConfig]:
    result = await db.execute(
        select(EnergyDeviceConfig).where(
            EnergyDeviceConfig.platform_code == platform_code,
            EnergyDeviceConfig.is_enabled == True,  # noqa: E712
            EnergyDeviceConfig.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def get_latest_energy_data(db: AsyncSession, device_config_id: UUID) -> EnergyData | None:
    """获取指定设备最近一条能耗数据记录。"""
    result = await db.execute(
        select(EnergyData)
        .where(
            EnergyData.device_config_id == device_config_id,
            EnergyData.is_deleted == False,  # noqa: E712  # noqa: E712
        )
        .order_by(EnergyData.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_distinct_enabled_platforms(db: AsyncSession) -> list[str]:
    """返回所有有启用设备的平台 code 列表（去重）。"""
    result = await db.execute(
        select(EnergyDeviceConfig.platform_code)
        .where(
            EnergyDeviceConfig.is_enabled == True,  # noqa: E712
            EnergyDeviceConfig.is_deleted == False,  # noqa: E712  # noqa: E712
        )
        .distinct()
    )
    return list(result.scalars().all())


# ── 能耗数据 ──


async def upsert_energy_data(
    db: AsyncSession,
    device_config_id: UUID,
    timestamp: datetime,
    value: float,
    unit: str,
    platform_raw_data: dict[str, Any] | None = None,
) -> EnergyData:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(EnergyData).values(
        device_config_id=device_config_id,
        timestamp=timestamp,
        value=value,
        unit=unit,
        platform_raw_data=platform_raw_data,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_energy_data_device_timestamp",
        set_={"value": value, "platform_raw_data": platform_raw_data},
    )
    returning_stmt = stmt.returning(EnergyData)
    result = await db.execute(returning_stmt)
    return result.scalar_one()


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
    query = select(EnergyData).where(
        EnergyData.is_deleted == False  # noqa: E712
    )
    if device_config_id:
        query = query.where(EnergyData.device_config_id == device_config_id)
    if start_time:
        query = query.where(EnergyData.timestamp >= start_time)
    if end_time:
        query = query.where(EnergyData.timestamp <= end_time)
    if energy_type or workshop:
        query = query.join(
            EnergyDeviceConfig,
            EnergyData.device_config_id == EnergyDeviceConfig.id,
        )
        if energy_type:
            query = query.where(EnergyDeviceConfig.energy_type == energy_type)
        if workshop:
            query = query.where(EnergyDeviceConfig.workshop == workshop)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(EnergyData.timestamp.desc(), EnergyData.device_config_id, EnergyData.id)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


# ── 全厂汇总口径 ──


def _not_rollup_record() -> ColumnElement[bool]:
    """剔除车间已标记的合计行能源类型，避免全厂汇总与其构成项重复计数。

    粒度是 (车间, 能源类型)：RTO 的电已含在「环保中心（含RTO）」内，但其天然气是全厂唯一气源，仍须计入。
    """
    marked = (
        select(sa.literal(1))
        .where(EnergyWorkshop.id == EnergyMonthlyRecord.workshop_id)
        .where(
            func.array_position(
                EnergyWorkshop.excluded_energy_types,
                EnergyMonthlyRecord.energy_type,
            ).is_not(None)
        )
        .correlate(EnergyMonthlyRecord)
        .scalar_subquery()
    )
    return ~sa.exists(marked)


async def get_energy_statistics(
    db: AsyncSession,
    *,
    group_by: str,
    energy_type: str | None = None,
    start_time: datetime,
    end_time: datetime,
) -> list[dict[str, Any]]:
    """按车间/产线/设备汇总能耗（从月度记录表查询）"""
    start_date = _cst_date(start_time)
    end_date = _cst_date(end_time)

    if group_by == "workshop":
        query = (
            select(
                EnergyWorkshop.name.label("group_key"),
                func.sum(EnergyMonthlyRecord.value).label("total_value"),
                EnergyMonthlyRecord.unit,
                EnergyMonthlyRecord.energy_type,
                func.count(EnergyMonthlyRecord.id).label("data_count"),
            )
            .join(
                EnergyWorkshop,
                EnergyMonthlyRecord.workshop_id == EnergyWorkshop.id,
            )
            .where(
                EnergyMonthlyRecord.record_date >= start_date,
                EnergyMonthlyRecord.record_date <= end_date,
                EnergyMonthlyRecord.is_deleted == False,  # noqa: E712  # noqa: E712
                EnergyWorkshop.is_deleted == False,  # noqa: E712  # noqa: E712
            )
            .group_by(EnergyWorkshop.name, EnergyMonthlyRecord.unit, EnergyMonthlyRecord.energy_type)
        )
    else:
        # 对于其他分组方式，暂时按车间分组
        query = (
            select(
                EnergyWorkshop.name.label("group_key"),
                func.sum(EnergyMonthlyRecord.value).label("total_value"),
                EnergyMonthlyRecord.unit,
                EnergyMonthlyRecord.energy_type,
                func.count(EnergyMonthlyRecord.id).label("data_count"),
            )
            .join(
                EnergyWorkshop,
                EnergyMonthlyRecord.workshop_id == EnergyWorkshop.id,
            )
            .where(
                EnergyMonthlyRecord.record_date >= start_date,
                EnergyMonthlyRecord.record_date <= end_date,
                EnergyMonthlyRecord.is_deleted == False,  # noqa: E712  # noqa: E712
                EnergyWorkshop.is_deleted == False,  # noqa: E712  # noqa: E712
            )
            .group_by(EnergyWorkshop.name, EnergyMonthlyRecord.unit, EnergyMonthlyRecord.energy_type)
        )

    if energy_type:
        query = query.where(EnergyMonthlyRecord.energy_type == energy_type)

    # 区域分布/按车间汇总属全厂口径，剔除合计行避免重复计数
    query = query.where(_not_rollup_record())

    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "group_key": row.group_key,
            "total_value": float(row.total_value or 0),
            "unit": row.unit,
            "energy_type": row.energy_type,
            "data_count": row.data_count,
        }
        for row in rows
    ]


# ── 采集日志 ──


# ── 总览统计 ──


async def get_overview_summary(
    db: AsyncSession,
    start_time: datetime,
    end_time: datetime,
) -> list[dict[str, Any]]:
    """按能源类型汇总能耗（从月度记录表查询）"""
    # 将 datetime 换算成东八区日期用于查询
    start_date = _cst_date(start_time)
    end_date = _cst_date(end_time)

    query = (
        select(
            EnergyMonthlyRecord.energy_type,
            func.sum(EnergyMonthlyRecord.value).label("total_value"),
            EnergyMonthlyRecord.unit,
        )
        .join(
            EnergyWorkshop,
            EnergyMonthlyRecord.workshop_id == EnergyWorkshop.id,
        )
        .where(
            EnergyMonthlyRecord.record_date >= start_date,
            EnergyMonthlyRecord.record_date <= end_date,
            EnergyMonthlyRecord.is_deleted == False,  # noqa: E712
            EnergyWorkshop.is_deleted == False,  # noqa: E712
            _not_rollup_record(),
        )
        .group_by(EnergyMonthlyRecord.energy_type, EnergyMonthlyRecord.unit)
    )
    result = await db.execute(query)
    return [
        {
            "energy_type": row.energy_type,
            "total_value": float(row.total_value or 0),
            "unit": row.unit,
        }
        for row in result.all()
    ]


async def get_overview_trend(
    db: AsyncSession,
    start_time: datetime,
    end_time: datetime,
    energy_type: str | None = None,
) -> list[dict[str, Any]]:
    """按日期获取能耗趋势数据（从月度记录表查询）"""
    # 将 datetime 换算成东八区日期用于查询
    start_date = _cst_date(start_time)
    end_date = _cst_date(end_time)

    query = (
        select(
            EnergyMonthlyRecord.record_date,
            EnergyMonthlyRecord.energy_type,
            func.sum(EnergyMonthlyRecord.value).label("total_value"),
        )
        .join(
            EnergyWorkshop,
            EnergyMonthlyRecord.workshop_id == EnergyWorkshop.id,
        )
        .where(
            EnergyMonthlyRecord.record_date >= start_date,
            EnergyMonthlyRecord.record_date <= end_date,
            EnergyMonthlyRecord.is_deleted == False,  # noqa: E712
            EnergyWorkshop.is_deleted == False,  # noqa: E712
        )
        .group_by(EnergyMonthlyRecord.record_date, EnergyMonthlyRecord.energy_type)
        .order_by(EnergyMonthlyRecord.record_date.asc())
    )
    if energy_type:
        query = query.where(EnergyMonthlyRecord.energy_type == energy_type)

    # 趋势曲线属全厂口径，剔除合计行避免重复计数
    query = query.where(_not_rollup_record())

    result = await db.execute(query)
    return [
        {
            "time": row.record_date.isoformat(),
            "value": float(row.total_value or 0),
            "type": row.energy_type,
        }
        for row in result.all()
    ]


async def create_collect_log(db: AsyncSession, data: dict[str, Any]) -> EnergyCollectLog:
    obj = EnergyCollectLog(**data)
    db.add(obj)
    await db.flush()
    return obj


async def list_collect_logs(
    db: AsyncSession,
    *,
    platform_code: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EnergyCollectLog], int]:
    query = select(EnergyCollectLog).where(
        EnergyCollectLog.is_deleted == False  # noqa: E712
    )
    if platform_code:
        query = query.where(EnergyCollectLog.platform_code == platform_code)
    if status:
        query = query.where(EnergyCollectLog.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(EnergyCollectLog.collect_time.desc(), EnergyCollectLog.id)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_collect_log_detail(
    db: AsyncSession,
    log_id: UUID,
    time_window_seconds: int = 30,
) -> tuple[EnergyCollectLog | None, list[tuple[EnergyData, EnergyDeviceConfig]]]:
    """获取采集日志详情及关联的能耗数据。

    通过 platform_code + 时间窗口匹配 EnergyData 和 EnergyCollectLog。
    """
    log = await db.scalar(
        select(EnergyCollectLog).where(
            EnergyCollectLog.id == log_id,
            EnergyCollectLog.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    if log is None:
        return None, []

    from datetime import timedelta

    window_start = log.collect_time - timedelta(seconds=time_window_seconds)
    window_end = log.collect_time + timedelta(seconds=time_window_seconds)

    query = (
        select(EnergyData, EnergyDeviceConfig)
        .join(
            EnergyDeviceConfig,
            EnergyData.device_config_id == EnergyDeviceConfig.id,
        )
        .where(
            EnergyDeviceConfig.platform_code == log.platform_code,
            EnergyData.collected_at >= window_start,
            EnergyData.collected_at <= window_end,
            EnergyData.is_deleted == False,  # noqa: E712  # noqa: E712
        )
        .order_by(EnergyData.timestamp.desc())
    )
    result = await db.execute(query)
    rows = list(result.all())

    return log, rows  # type: ignore[return-value]


# ── 预警规则 ──


async def create_alert_rule(db: AsyncSession, data: dict[str, Any]) -> EnergyAlertRule:
    obj = EnergyAlertRule(**data)
    db.add(obj)
    await db.flush()
    result = await db.execute(
        select(EnergyAlertRule).where(
            EnergyAlertRule.id == obj.id,
            EnergyAlertRule.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one()


async def get_alert_rule_by_id(db: AsyncSession, rule_id: UUID) -> EnergyAlertRule | None:
    result = await db.execute(
        select(EnergyAlertRule).where(
            EnergyAlertRule.id == rule_id,
            EnergyAlertRule.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def list_alert_rules(
    db: AsyncSession,
    *,
    energy_type: str | None = None,
    alert_level: str | None = None,
    is_enabled: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EnergyAlertRule], int]:
    query = select(EnergyAlertRule).where(
        EnergyAlertRule.is_deleted == False  # noqa: E712
    )
    if energy_type:
        query = query.where(EnergyAlertRule.energy_type == energy_type)
    if alert_level:
        query = query.where(EnergyAlertRule.alert_level == alert_level)
    if is_enabled is not None:
        query = query.where(EnergyAlertRule.is_enabled == is_enabled)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 同一事务批量写入的行 created_at 完全相同，必须补 id 才能保证翻页不重不漏
    query = query.order_by(EnergyAlertRule.created_at.desc(), EnergyAlertRule.id)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_alert_rule(db: AsyncSession, rule_id: UUID, data: dict[str, Any]) -> EnergyAlertRule | None:
    obj = await get_alert_rule_by_id(db, rule_id)
    if obj is None:
        return None
    for key, value in data.items():
        setattr(obj, key, value)
    await db.flush()
    result = await db.execute(
        select(EnergyAlertRule).where(
            EnergyAlertRule.id == rule_id,
            EnergyAlertRule.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def delete_alert_rule(db: AsyncSession, rule_id: UUID) -> bool:
    obj = await get_alert_rule_by_id(db, rule_id)
    if obj is None:
        return False
    obj.is_deleted = True
    await db.flush()
    return True


# ── 预警记录 ──


async def create_alert_record(db: AsyncSession, data: dict[str, Any]) -> EnergyAlertRecord:
    obj = EnergyAlertRecord(**data)
    db.add(obj)
    await db.flush()
    result = await db.execute(
        select(EnergyAlertRecord).where(
            EnergyAlertRecord.id == obj.id,
            EnergyAlertRecord.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one()


async def get_alert_record_by_id(db: AsyncSession, record_id: UUID) -> EnergyAlertRecord | None:
    result = await db.execute(
        select(EnergyAlertRecord).where(
            EnergyAlertRecord.id == record_id,
            EnergyAlertRecord.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def delete_alert_record(db: AsyncSession, record_id: UUID) -> bool:
    """软删除预警记录，并清掉日数据行上的反向引用。

    清 `energy_daily_data.alert_record_id` 是让「删除 → 重导入」能拿回这条预警：`check_alerts`
    只处理 `alert_record_id IS NULL` 的行，留着引用就等于永久屏蔽。多维表格的日数据每天会被修正，
    改对之后重新导入应当按新的 `is_alert` 重新判定——仍然超线就再生成，已被改到线下就不再生成。
    """
    obj = await get_alert_record_by_id(db, record_id)
    if obj is None:
        return False
    obj.is_deleted = True
    await db.execute(
        sa.update(EnergyDailyData).where(EnergyDailyData.alert_record_id == record_id).values(alert_record_id=None)
    )
    await db.flush()
    return True


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
    query = select(EnergyAlertRecord).where(
        EnergyAlertRecord.is_deleted == False  # noqa: E712
    )
    if energy_type:
        query = query.where(EnergyAlertRecord.energy_type == energy_type)
    if alert_level:
        query = query.where(EnergyAlertRecord.alert_level == alert_level)
    if status:
        query = query.where(EnergyAlertRecord.status == status)
    if start_time:
        query = query.where(EnergyAlertRecord.alert_time >= start_time)
    if end_time:
        query = query.where(EnergyAlertRecord.alert_time <= end_time)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # alert_time 只到日，同一天必然并列；不补决胜位会让同一行在翻页时重复出现
    query = query.order_by(EnergyAlertRecord.alert_time.desc(), EnergyAlertRecord.energy_type, EnergyAlertRecord.id)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_alert_record(db: AsyncSession, record_id: UUID, data: dict[str, Any]) -> EnergyAlertRecord | None:
    obj = await get_alert_record_by_id(db, record_id)
    if obj is None:
        return None
    for key, value in data.items():
        setattr(obj, key, value)
    await db.flush()
    result = await db.execute(
        select(EnergyAlertRecord).where(
            EnergyAlertRecord.id == record_id,
            EnergyAlertRecord.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ── 车间管理 ──


async def create_workshop(db: AsyncSession, data: dict[str, Any]) -> EnergyWorkshop:
    from app.modules.energy.models import EnergyWorkshop

    obj = EnergyWorkshop(**data)
    db.add(obj)
    await db.flush()
    return obj


async def get_workshop_by_id(db: AsyncSession, workshop_id: UUID) -> EnergyWorkshop | None:
    from app.modules.energy.models import EnergyWorkshop

    result = await db.execute(
        select(EnergyWorkshop).where(
            EnergyWorkshop.id == workshop_id,
            EnergyWorkshop.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_workshop_by_code(db: AsyncSession, code: str) -> EnergyWorkshop | None:
    from app.modules.energy.models import EnergyWorkshop

    result = await db.execute(
        select(EnergyWorkshop).where(
            EnergyWorkshop.code == code,
            EnergyWorkshop.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_workshop_by_name(db: AsyncSession, name: str) -> EnergyWorkshop | None:
    from app.modules.energy.models import EnergyWorkshop

    result = await db.execute(
        select(EnergyWorkshop).where(
            EnergyWorkshop.name == name,
            EnergyWorkshop.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def list_workshops(
    db: AsyncSession,
    *,
    category: str | None = None,
    is_active: bool | None = None,
    name_in: Sequence[str] | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[EnergyWorkshop], int]:
    from app.modules.energy.models import EnergyWorkshop

    query = select(EnergyWorkshop).where(
        EnergyWorkshop.is_deleted == False  # noqa: E712
    )
    if category:
        query = query.where(EnergyWorkshop.category == category)
    if is_active is not None:
        query = query.where(EnergyWorkshop.is_active == is_active)
    if name_in is not None:
        query = query.where(EnergyWorkshop.name.in_(list(name_in)))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(EnergyWorkshop.sort_order, EnergyWorkshop.code)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_workshop(db: AsyncSession, workshop_id: UUID, data: dict[str, Any]) -> EnergyWorkshop | None:
    from app.modules.energy.models import EnergyWorkshop

    obj = await get_workshop_by_id(db, workshop_id)
    if obj is None:
        return None
    for key, value in data.items():
        setattr(obj, key, value)
    await db.flush()
    result = await db.execute(
        select(EnergyWorkshop).where(
            EnergyWorkshop.id == workshop_id,
            EnergyWorkshop.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def delete_workshop(db: AsyncSession, workshop_id: UUID) -> bool:
    obj = await get_workshop_by_id(db, workshop_id)
    if obj is None:
        return False
    obj.is_deleted = True
    await db.flush()
    return True


async def count_active_monthly_records_by_workshop(db: AsyncSession, workshop_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(EnergyMonthlyRecord)
        .where(
            EnergyMonthlyRecord.workshop_id == workshop_id,
            EnergyMonthlyRecord.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar() or 0


# ── 月度记录 ──


async def create_monthly_record(db: AsyncSession, data: dict[str, Any]) -> EnergyMonthlyRecord:
    from app.modules.energy.models import EnergyMonthlyRecord

    obj = EnergyMonthlyRecord(**data)
    db.add(obj)
    await db.flush()
    return obj


async def batch_create_monthly_records(db: AsyncSession, records: list[dict[str, Any]]) -> list[EnergyMonthlyRecord]:
    from app.modules.energy.models import EnergyMonthlyRecord

    objs = [EnergyMonthlyRecord(**r) for r in records]
    db.add_all(objs)
    await db.flush()
    return objs


async def batch_upsert_monthly_records(
    db: AsyncSession, records: list[dict[str, Any]]
) -> tuple[list[EnergyMonthlyRecord], int]:
    """批量 upsert 月度记录，遇到唯一约束冲突时更新 value。

    返回 (新建列表, 变更数量)——只匹配到已有行但值没变的不计入变更（`D-51`）。
    """
    from app.modules.energy.models import EnergyMonthlyRecord

    created: list[EnergyMonthlyRecord] = []
    updated_count = 0

    for r in records:
        result = await db.execute(
            select(EnergyMonthlyRecord).where(
                EnergyMonthlyRecord.workshop_id == r["workshop_id"],
                EnergyMonthlyRecord.energy_type == r["energy_type"],
                EnergyMonthlyRecord.record_date == r["record_date"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if existing.is_deleted:
                # 唯一约束 uq_energy_monthly_record 不含 is_deleted，命中软删行只能复活，
                # 否则插入分支会撞 UniqueViolation
                logger.info(
                    "Reviving soft-deleted monthly record",
                    extra={"record_id": str(existing.id), "record_date": str(existing.record_date)},
                )
            if apply_changed_fields(
                existing,
                {
                    "is_deleted": False,
                    "value": r["value"],
                    "unit": r.get("unit", existing.unit),
                    "source": r.get("source", existing.source),
                    "remark": r.get("remark"),
                    "date_range_end": r.get("date_range_end"),
                },
            ):
                updated_count += 1
        else:
            obj = EnergyMonthlyRecord(**r)
            db.add(obj)
            created.append(obj)

    await db.flush()
    return created, updated_count


async def list_monthly_records(
    db: AsyncSession,
    *,
    workshop_id: UUID | None = None,
    energy_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[EnergyMonthlyRecord], int]:
    from app.modules.energy.models import EnergyMonthlyRecord

    query = (
        select(EnergyMonthlyRecord, EnergyWorkshop.name)
        .join(
            EnergyWorkshop,
            EnergyMonthlyRecord.workshop_id == EnergyWorkshop.id,
        )
        .where(
            EnergyMonthlyRecord.is_deleted == False,  # noqa: E712
            EnergyWorkshop.is_deleted == False,  # noqa: E712
        )
    )
    if workshop_id:
        query = query.where(EnergyMonthlyRecord.workshop_id == workshop_id)
    if energy_type:
        query = query.where(EnergyMonthlyRecord.energy_type == energy_type)
    if start_date:
        query = query.where(EnergyMonthlyRecord.record_date >= start_date)
    if end_date:
        query = query.where(EnergyMonthlyRecord.record_date <= end_date)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # record_date 在同一批次里大量并列，并列行的顺序 Postgres 不保证稳定 → 翻页会重复显示同一车间；补唯一键其余两列决胜
    query = query.order_by(
        EnergyMonthlyRecord.record_date.desc(),
        EnergyMonthlyRecord.workshop_id,
        EnergyMonthlyRecord.energy_type,
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records: list[EnergyMonthlyRecord] = []
    for record, workshop_name in result.all():
        # 带上规范车间名，前端不必再靠 workshop_id 回查（合并未完成时也不会退化成 UUID 前缀）
        setattr(record, "workshop_name", workshop_name)
        records.append(record)
    return records, total


async def get_monthly_record_by_id(db: AsyncSession, record_id: UUID) -> EnergyMonthlyRecord | None:
    from app.modules.energy.models import EnergyMonthlyRecord

    result = await db.execute(
        select(EnergyMonthlyRecord).where(
            EnergyMonthlyRecord.id == record_id,
            EnergyMonthlyRecord.is_deleted == False,  # noqa: E712  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def delete_monthly_record(db: AsyncSession, record_id: UUID) -> bool:
    obj = await get_monthly_record_by_id(db, record_id)
    if obj is None:
        return False
    obj.is_deleted = True
    await db.flush()
    return True


async def get_monthly_summary(
    db: AsyncSession,
    workshop_id: UUID | None = None,
    energy_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """获取月度记录汇总，按能源类型分组统计总量"""
    query = (
        select(
            EnergyMonthlyRecord.energy_type,
            func.sum(EnergyMonthlyRecord.value).label("total_value"),
            EnergyMonthlyRecord.unit,
        )
        .join(
            EnergyWorkshop,
            EnergyMonthlyRecord.workshop_id == EnergyWorkshop.id,
        )
        .where(
            EnergyMonthlyRecord.is_deleted == False,  # noqa: E712
            EnergyWorkshop.is_deleted == False,  # noqa: E712
        )
    )

    if workshop_id:
        query = query.where(EnergyMonthlyRecord.workshop_id == workshop_id)
    else:
        # 全公司口径才剔除合计行；指定车间时保留其自身上报值
        query = query.where(_not_rollup_record())
    if energy_type:
        query = query.where(EnergyMonthlyRecord.energy_type == energy_type)
    if start_date:
        query = query.where(EnergyMonthlyRecord.record_date >= start_date)
    if end_date:
        query = query.where(EnergyMonthlyRecord.record_date <= end_date)

    query = query.group_by(
        EnergyMonthlyRecord.energy_type,
        EnergyMonthlyRecord.unit,
    )

    result = await db.execute(query)
    rows = result.all()

    summary = {}
    for row in rows:
        summary[row.energy_type] = {
            "total_value": float(row.total_value or 0),
            "unit": row.unit,
        }

    return summary


async def get_monthly_energy_total(
    db: AsyncSession,
    workshop_id: UUID,
    start_date: date,
    end_date: date,
    energy_type: str | None = None,
) -> Decimal | None:
    """获取指定车间在指定时间范围内的总能耗。

    `energy_type` 传值时只统计该类型。`value` 是各能源的裸值（kWh / m³ / t / Nm³），
    不加过滤把四类相加得到的数没有单位含义（单耗口径见 docs/energy-module-prd.md 6.4）。
    """
    from decimal import Decimal

    from sqlalchemy import func, select

    query = select(func.sum(EnergyMonthlyRecord.value)).where(
        EnergyMonthlyRecord.workshop_id == workshop_id,
        EnergyMonthlyRecord.record_date >= start_date,
        EnergyMonthlyRecord.record_date < end_date,  # 不包含结束日期
        EnergyMonthlyRecord.is_deleted == False,  # noqa: E712
    )
    if energy_type is not None:
        query = query.where(EnergyMonthlyRecord.energy_type == energy_type)

    result = await db.execute(query)
    total = result.scalar()

    return Decimal(str(total)) if total else None


# ── Unit Consumption Target Repository Functions ──


async def create_unit_consumption_target(
    db: AsyncSession,
    workshop_id: UUID,
    target_month: date,
    target_unit_consumption: float,
) -> EnergyUnitConsumptionTarget:
    """创建单耗目标"""
    from decimal import Decimal

    target = EnergyUnitConsumptionTarget(
        workshop_id=workshop_id,
        target_month=target_month,
        target_unit_consumption=Decimal(str(target_unit_consumption)),
    )
    db.add(target)
    await db.flush()
    return target


async def get_unit_consumption_target_by_id(
    db: AsyncSession,
    target_id: UUID,
) -> EnergyUnitConsumptionTarget | None:
    """根据 ID 查询单耗目标"""
    result = await db.execute(
        select(EnergyUnitConsumptionTarget).where(
            EnergyUnitConsumptionTarget.id == target_id,
            EnergyUnitConsumptionTarget.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_unit_consumption_target_by_workshop_and_month(
    db: AsyncSession,
    workshop_id: UUID,
    target_month: date,
) -> EnergyUnitConsumptionTarget | None:
    """根据车间和月份查询单耗目标"""
    result = await db.execute(
        select(EnergyUnitConsumptionTarget).where(
            EnergyUnitConsumptionTarget.workshop_id == workshop_id,
            EnergyUnitConsumptionTarget.target_month == target_month,
            EnergyUnitConsumptionTarget.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def update_unit_consumption_target(
    db: AsyncSession,
    target_id: UUID,
    target_unit_consumption: float,
) -> EnergyUnitConsumptionTarget | None:
    """更新单耗目标"""
    from decimal import Decimal

    target = await get_unit_consumption_target_by_id(db, target_id)
    if target is None:
        return None

    target.target_unit_consumption = Decimal(str(target_unit_consumption))
    await db.flush()

    # Re-fetch to ensure consistency
    return await get_unit_consumption_target_by_id(db, target_id)
