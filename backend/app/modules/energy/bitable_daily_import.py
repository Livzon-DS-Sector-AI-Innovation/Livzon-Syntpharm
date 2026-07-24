"""Energy module Feishu Bitable daily data import adapter.

从飞书多维表格导入每日能耗数据，用于预警检查。
"""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.energy.models import EnergyAlertRecord, EnergyDailyData
from app.platform.integrations.feishu.client import FeishuClient

logger = logging.getLogger(__name__)
_settings = get_settings()

# 飞书表格 ID 到能源类型的映射
TABLE_MAPPING = {
    "tblt8N0jHCNKzE4n": ("water", "💧水"),
    "tblrPwKIh2KtZT7F": ("electricity", "⚡电"),
    "tblmVASM8va4sXfb": ("natural_gas", "💨天然气"),
    "tbl6iyiYrc1ebsmx": ("natural_gas", "RTO天然气"),
    "tblwaxPzKR7aRluo": ("steam", "蒸汽"),
}


class EnergyBitableDailyImport:
    """从飞书多维表格导入每日能耗数据"""

    def __init__(self, app_token: str | None = None) -> None:
        self.client = FeishuClient()
        self.app_token = app_token or _settings.feishu.energy.alert_app_token

    async def list_records(self, table_id: str, page_size: int = 100) -> list[dict[str, Any]]:
        """获取数据表中的所有记录"""
        path = f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records"
        all_records = []
        page_token = None

        while True:
            params: dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            data = await self.client.request("GET", path, params=params)
            items = data.get("items", [])
            all_records.extend(items)

            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

        return all_records

    def _parse_timestamp(self, timestamp_ms: int) -> date:
        """将毫秒时间戳转换为日期"""
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        return dt.date()

    def _parse_record(self, record: dict[str, Any], energy_type: str, source_table: str) -> dict[str, Any] | None:
        """解析单条记录"""
        fields = record.get("fields", {})

        # 提取时间
        timestamp_ms = fields.get("时间")
        if not timestamp_ms:
            return None

        record_date = self._parse_timestamp(timestamp_ms)

        # 提取类别
        category = fields.get("类别", "")

        # 提取数值
        total_value = fields.get("总数")
        alert_threshold = fields.get("警戒线")

        if total_value is None or alert_threshold is None:
            return None

        # 转换为 Decimal
        try:
            total_value = Decimal(str(total_value))
            alert_threshold = Decimal(str(alert_threshold))
        except (ValueError, TypeError):
            return None

        # 可选字段
        cost = fields.get("费用")
        if cost is not None:
            try:
                cost = Decimal(str(cost))
            except (ValueError, TypeError):
                cost = None

        municipal_meter = fields.get("市政总表")
        if municipal_meter is not None:
            try:
                municipal_meter = Decimal(str(municipal_meter))
            except (ValueError, TypeError):
                municipal_meter = None

        error_value = fields.get("误差")
        if error_value is not None:
            try:
                error_value = Decimal(str(error_value))
            except (ValueError, TypeError):
                error_value = None

        return {
            "date": record_date,
            "energy_type": energy_type,
            "category": category,
            "total_value": total_value,
            "alert_threshold": alert_threshold,
            "cost": cost,
            "municipal_meter": municipal_meter,
            "error_value": error_value,
            "source_table": source_table,
            "is_alert": total_value > alert_threshold,
        }

    async def import_table(self, db: AsyncSession, table_id: str) -> dict[str, Any]:
        """导入单个表格的数据"""
        if table_id not in TABLE_MAPPING:
            return {"status": "error", "message": f"Unknown table: {table_id}"}

        energy_type, source_table = TABLE_MAPPING[table_id]

        # 获取所有记录
        records = await self.list_records(table_id)
        logger.info(f"Found {len(records)} records in table {source_table}")

        created = 0
        updated = 0
        errors = []

        for record in records:
            try:
                parsed = self._parse_record(record, energy_type, source_table)
                if not parsed:
                    continue

                # 检查是否已存在
                result = await db.execute(
                    select(EnergyDailyData).where(
                        EnergyDailyData.date == parsed["date"],
                        EnergyDailyData.energy_type == parsed["energy_type"],
                        EnergyDailyData.category == parsed["category"],
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新现有记录
                    existing.total_value = parsed["total_value"]
                    existing.alert_threshold = parsed["alert_threshold"]
                    existing.cost = parsed["cost"]
                    existing.municipal_meter = parsed["municipal_meter"]
                    existing.error_value = parsed["error_value"]
                    existing.is_alert = parsed["is_alert"]
                    updated += 1
                else:
                    # 创建新记录
                    new_record = EnergyDailyData(**parsed)
                    db.add(new_record)
                    created += 1

            except Exception as e:
                errors.append(f"Error processing record: {str(e)}")
                logger.exception(f"Error processing record: {record}")

        await db.commit()

        return {
            "status": "success",
            "table": source_table,
            "total_created": created,
            "total_updated": updated,
            "total_parsed": len(records),
            "errors": errors[:10],
        }

    async def import_all_tables(self, db: AsyncSession) -> dict[str, Any]:
        """导入所有表格的最新数据"""
        results = []
        total_created = 0
        total_updated = 0
        total_errors = []

        for table_id in TABLE_MAPPING.keys():
            result = await self.import_table(db, table_id)
            results.append(result)
            total_created += result.get("total_created", 0)
            total_updated += result.get("total_updated", 0)
            total_errors.extend(result.get("errors", []))

        return {
            "status": "success",
            "tables_imported": len(TABLE_MAPPING),
            "total_created": total_created,
            "total_updated": total_updated,
            "total_errors": len(total_errors),
            "details": results,
        }

    async def check_alerts(self, db: AsyncSession, check_date: date) -> list[dict[str, Any]]:
        """检查某日数据是否触发预警，并生成预警记录"""
        # 查询该日所有触发预警的数据
        result = await db.execute(
            select(EnergyDailyData).where(
                EnergyDailyData.date == check_date,
                EnergyDailyData.is_alert == True,
                EnergyDailyData.alert_record_id.is_(None),  # 尚未生成预警记录
            )
        )
        alert_data = result.scalars().all()

        alert_records = []

        for data in alert_data:
            # 确定预警等级
            if data.total_value > data.alert_threshold * Decimal("1.2"):
                alert_level = "critical"
            elif data.total_value > data.alert_threshold * Decimal("1.1"):
                alert_level = "warning"
            else:
                alert_level = "info"

            # 创建预警记录
            alert_record = EnergyAlertRecord(
                rule_id=None,  # 暂时不关联规则
                device_config_id=None,
                energy_type=data.energy_type,
                alert_level=alert_level,
                trigger_value=data.total_value,
                threshold_value=data.alert_threshold,
                unit="",  # TODO: 从 category 解析单位
                alert_time=datetime.combine(data.date, datetime.max.time()),
                status="pending",
            )
            db.add(alert_record)
            await db.flush()  # 获取 alert_record.id

            # 更新 daily_data 的 alert_record_id
            data.alert_record_id = alert_record.id
            alert_records.append(
                {
                    "id": str(alert_record.id),
                    "energy_type": data.energy_type,
                    "category": data.category,
                    "trigger_value": str(data.total_value),
                    "threshold_value": str(data.alert_threshold),
                    "alert_level": alert_level,
                }
            )

        await db.commit()

        return alert_records
