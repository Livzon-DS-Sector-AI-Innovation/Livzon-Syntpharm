"""Energy module Feishu Bitable sync service.

从飞书多维表格同步车间和月度能耗记录数据。
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.energy.models import EnergyMonthlyRecord, EnergyWorkshop
from app.platform.integrations.feishu.client import FeishuClient

logger = logging.getLogger(__name__)
_settings = get_settings()


class EnergyBitableSync:
    """从飞书多维表格同步能源数据。"""

    def __init__(self) -> None:
        self.client = FeishuClient()
        self.app_token = _settings.feishu.energy.app_token
        self.workshop_table_id = _settings.feishu.energy.workshop_table_id
        self.monthly_table_id = _settings.feishu.energy.monthly_table_id

    def _is_enabled(self) -> bool:
        return bool(self.app_token)

    def _workshop_path(self, suffix: str = "") -> str:
        return f"/bitable/v1/apps/{self.app_token}/tables/{self.workshop_table_id}{suffix}"

    def _monthly_path(self, suffix: str = "") -> str:
        return f"/bitable/v1/apps/{self.app_token}/tables/{self.monthly_table_id}{suffix}"

    async def list_records(self, table_id: str, page_size: int = 500) -> list[dict[str, Any]]:
        """获取多维表格中的所有记录。"""
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

    async def sync_workshops(self, db: AsyncSession) -> dict[str, Any]:
        """从多维表格同步车间数据。"""
        if not self._is_enabled() or not self.workshop_table_id:
            return {"status": "disabled", "message": "未配置能源多维表格"}

        records = await self.list_records(self.workshop_table_id)
        created = 0
        updated = 0

        for record in records:
            fields = record.get("fields", {})
            code = fields.get("编码") or fields.get("code")
            name = fields.get("名称") or fields.get("name")
            category = fields.get("分类") or fields.get("category") or "workshop"
            sort_order = fields.get("排序") or fields.get("sort_order") or 0
            is_active = fields.get("启用") if "启用" in fields else fields.get("is_active", True)

            if not code or not name:
                continue

            # 检查是否已存在
            result = await db.execute(select(EnergyWorkshop).where(EnergyWorkshop.code == code))
            workshop = result.scalar_one_or_none()

            if workshop:
                # 更新
                workshop.name = name
                workshop.category = category
                workshop.sort_order = sort_order
                workshop.is_active = is_active
                updated += 1
            else:
                # 创建
                workshop = EnergyWorkshop(
                    code=code,
                    name=name,
                    category=category,
                    sort_order=sort_order,
                    is_active=is_active,
                )
                db.add(workshop)
                created += 1

        await db.commit()
        return {"status": "success", "created": created, "updated": updated, "total": len(records)}

    async def sync_monthly_records(self, db: AsyncSession) -> dict[str, Any]:
        """从多维表格同步月度能耗记录。"""
        if not self._is_enabled() or not self.monthly_table_id:
            return {"status": "disabled", "message": "未配置能源多维表格"}

        records = await self.list_records(self.monthly_table_id)
        created = 0
        updated = 0

        # 先获取所有车间映射
        result = await db.execute(select(EnergyWorkshop))
        workshops = {w.name: w for w in result.scalars().all()}
        workshops.update({w.code: w for w in workshops.values()})

        for record in records:
            fields = record.get("fields", {})

            # 解析车间（支持名称或编码）
            workshop_ref = fields.get("车间") or fields.get("workshop")
            if not workshop_ref:
                continue

            workshop = workshops.get(workshop_ref)
            if not workshop:
                logger.warning(f"车间不存在: {workshop_ref}")
                continue

            # 解析能源类型
            energy_type = fields.get("能源类型") or fields.get("energy_type")
            if not energy_type:
                continue

            # 标准化能源类型
            energy_type_map = {
                "电": "electricity",
                "电力": "electricity",
                "水": "water",
                "蒸汽": "steam",
                "天然气": "natural_gas",
                "燃气": "natural_gas",
            }
            energy_type = energy_type_map.get(energy_type, energy_type)

            # 解析日期
            record_date_raw = fields.get("日期") or fields.get("record_date")
            if not record_date_raw:
                continue

            if isinstance(record_date_raw, int):
                # 毫秒时间戳
                record_date = datetime.fromtimestamp(record_date_raw / 1000).date()
            elif isinstance(record_date_raw, str):
                record_date = datetime.fromisoformat(record_date_raw).date()
            else:
                continue

            # 解析数值
            value = fields.get("数值") or fields.get("value")
            if value is None:
                continue

            unit = fields.get("单位") or fields.get("unit") or ""
            remark = fields.get("备注") or fields.get("remark")

            # 检查是否已存在
            result = await db.execute(
                select(EnergyMonthlyRecord).where(
                    EnergyMonthlyRecord.workshop_id == workshop.id,
                    EnergyMonthlyRecord.energy_type == energy_type,
                    EnergyMonthlyRecord.record_date == record_date,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # 更新
                existing.value = value  # type: ignore[attr-defined]
                existing.unit = unit  # type: ignore[attr-defined]
                existing.remark = remark  # type: ignore[attr-defined]
                updated += 1
            else:
                # 创建
                new_record = EnergyMonthlyRecord(
                    workshop_id=workshop.id,
                    energy_type=energy_type,
                    record_date=record_date,
                    value=value,
                    unit=unit,
                    source="feishu_bitable",
                    remark=remark,
                )
                db.add(new_record)
                created += 1

        await db.commit()
        return {"status": "success", "created": created, "updated": updated, "total": len(records)}

    async def sync_all(self, db: AsyncSession) -> dict[str, Any]:
        """同步所有能源数据。"""
        workshop_result = await self.sync_workshops(db)
        monthly_result = await self.sync_monthly_records(db)
        return {
            "workshops": workshop_result,
            "monthly_records": monthly_result,
        }
