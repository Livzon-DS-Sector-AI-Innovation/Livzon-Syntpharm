"""Energy module Feishu Bitable sync service.

从飞书多维表格同步车间和月度能耗记录数据。
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.energy.models import ROLLUP_WORKSHOPS, EnergyMonthlyRecord, EnergyWorkshop
from app.modules.energy.repository import apply_changed_fields
from app.modules.energy.workshop_names import (
    load_workshop_alias_map,
    normalize_workshop_name,
    resolve_workshop_name,
)
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
        self._alias_map: dict[str, str] | None = None

    async def _get_alias_map(self) -> dict[str, str]:
        if self._alias_map is None:
            self._alias_map = await load_workshop_alias_map(self.list_tables, self.list_records)
        return self._alias_map

    async def list_tables(self) -> list[dict[str, Any]]:
        """获取多维表格中的所有数据表（自动分页）。"""
        path = f"/bitable/v1/apps/{self.app_token}/tables"
        all_tables: list[dict[str, Any]] = []
        page_token = None

        while True:
            params: dict[str, Any] = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            data = await self.client.request("GET", path, params=params)
            all_tables.extend(data.get("items", []))

            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

        return all_tables

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
        alias_map = await self._get_alias_map()
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

            resolved_name = resolve_workshop_name(str(name), alias_map)

            # 先按规范名找：别名行（如 QC）与规范行（质量控制部）必须落到同一个实体，
            # 否则会按别名 code 再建一个孤儿车间
            result = await db.execute(
                select(EnergyWorkshop)
                .where(
                    EnergyWorkshop.name == resolved_name,
                    EnergyWorkshop.is_deleted == False,  # noqa: E712
                )
                .order_by(EnergyWorkshop.id)
            )
            workshop = result.scalars().first()

            # 再按编码找（软删除的车间不复用，与 repository.get_workshop_by_code 口径一致）
            if workshop is None:
                result = await db.execute(
                    select(EnergyWorkshop)
                    .where(
                        EnergyWorkshop.code == code,
                        EnergyWorkshop.is_deleted == False,  # noqa: E712
                    )
                    .order_by(EnergyWorkshop.id)
                )
                workshop = result.scalars().first()

            if workshop:
                # 只统计值真变化的行（D-51）
                if apply_changed_fields(
                    workshop,
                    {
                        "name": resolved_name,
                        "category": category,
                        "sort_order": sort_order,
                        "is_active": is_active,
                    },
                ):
                    updated += 1
            else:
                # 创建
                workshop = EnergyWorkshop(
                    code=code,
                    name=resolved_name,
                    category=category,
                    sort_order=sort_order,
                    is_active=is_active,
                    excluded_energy_types=list(ROLLUP_WORKSHOPS.get(resolved_name, ())),
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
        alias_map = await self._get_alias_map()
        created = 0
        updated = 0

        # 先获取所有车间映射。名称与编码分开建索引：
        # 混进同一个 dict 时，某个车间的编码会撞上另一个车间的名称，把记录挂错实体
        result = await db.execute(
            select(EnergyWorkshop).where(
                EnergyWorkshop.is_deleted == False,  # noqa: E712
            )
        )
        workshops_by_name: dict[str, EnergyWorkshop] = {}
        workshops_by_code: dict[str, EnergyWorkshop] = {}
        for ws in result.scalars().all():
            workshops_by_name.setdefault(normalize_workshop_name(ws.name), ws)
            workshops_by_code.setdefault(ws.code, ws)

        for record in records:
            fields = record.get("fields", {})

            # 解析车间（支持名称或编码）
            workshop_ref = fields.get("车间") or fields.get("workshop")
            if not workshop_ref:
                continue

            # 先套别名再查：水侧 QC / 炊事班 等写法必须挂到规范实体上
            workshop_ref = str(workshop_ref)
            resolved_ref = resolve_workshop_name(workshop_ref, alias_map)
            workshop = (
                workshops_by_name.get(resolved_ref)
                or workshops_by_code.get(resolved_ref)
                # 过渡期兜底：规范实体还没建出来但别名实体已存在时，不丢记录
                or workshops_by_name.get(normalize_workshop_name(workshop_ref))
            )
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
                # 只统计值真变化的行（D-51）
                if apply_changed_fields(
                    existing,
                    {
                        "value": value,
                        "unit": unit,
                        "remark": remark,
                    },
                ):
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
