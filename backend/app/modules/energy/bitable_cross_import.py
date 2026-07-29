"""Energy module Feishu Bitable cross-table import adapter.

从飞书多维表格的交叉表格式导入月度能耗数据。
每个表（如 "2026-06"）包含三个能源类型的交叉表：电力、蒸汽、自来水。
"""

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.energy.models import EnergyMonthlyRecord, EnergyWorkshop
from app.platform.integrations.feishu.client import FeishuClient

logger = logging.getLogger(__name__)
_settings = get_settings()


class EnergyBitableCrossImport:
    """从飞书多维表格交叉表导入能源数据。"""

    # 需要跳过的汇总行模式
    SKIP_WORKSHOP_PATTERNS = [
        re.compile(r".*(合计|小计|总计|总电量|车间总计|误差|蒸汽总量|总数|市政总表|全厂|汇总).*"),
    ]
    SKIP_WORKSHOPS_EXACT = {"None", ""}

    @classmethod
    def _should_skip_workshop(cls, name: str) -> bool:
        """判断是否为汇总行，应跳过。"""
        if name in cls.SKIP_WORKSHOPS_EXACT:
            return True
        return any(p.match(name) for p in cls.SKIP_WORKSHOP_PATTERNS)

    # 能源类型识别模式（用于检测section切换）
    ENERGY_SECTION_PATTERNS = {
        "steam": re.compile(r"各车间蒸汽用量明细"),
        "water": re.compile(r"各车间自来水用量明细"),
        "natural_gas": re.compile(r"各车间天然气用量明细"),
    }

    def __init__(self, app_token: str | None = None) -> None:
        self.client = FeishuClient()
        self.app_token = app_token or _settings.feishu.energy.app_token

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
            items = data.get("items", [])
            all_tables.extend(items)

            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

        return all_tables

    async def list_records(self, table_id: str) -> list[dict[str, Any]]:
        """获取数据表中的所有记录。"""
        path = f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records"
        all_records = []
        page_token = None

        while True:
            params: dict[str, Any] = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            data = await self.client.request("GET", path, params=params)
            items = data.get("items", [])
            all_records.extend(items)

            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

        return all_records

    def _parse_date_header(self, value: str) -> tuple[date, date | None] | None:
        """解析日期表头，支持单日期和日期范围。"""
        if not value or value == "None":
            return None

        # 清理日期字符串
        value = value.strip().replace("/", "-")

        # 尝试匹配日期范围格式：2026-05-30-06-01 或 2026-6-13-15
        range_match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})\s*[-–]\s*(\d{1,2})-(\d{1,2})", value)
        if range_match:
            year = int(range_match.group(1))
            month1 = int(range_match.group(2))
            day1 = int(range_match.group(3))
            month2 = int(range_match.group(4))
            day2 = int(range_match.group(5))
            start_date = date(year, month1, day1)
            end_date = date(year, month2, day2)
            return (start_date, end_date)

        # 尝试匹配同月日期范围格式：2026-07-01-03（年月日-日）
        same_month_match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})\s*[-–]\s*(\d{1,2})$", value)
        if same_month_match:
            year = int(same_month_match.group(1))
            month = int(same_month_match.group(2))
            day1 = int(same_month_match.group(3))
            day2 = int(same_month_match.group(4))
            start_date = date(year, month, day1)
            end_date = date(year, month, day2)
            return (start_date, end_date)

        # 尝试匹配单日期格式：2026-06-02
        single_match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})$", value)
        if single_match:
            year = int(single_match.group(1))
            month = int(single_match.group(2))
            day = int(single_match.group(3))
            d = date(year, month, day)
            return (d, None)

        return None

    def _parse_value(self, value: Any) -> Decimal | None:
        """解析数值，支持字符串和数字。"""
        if value is None or value == "None" or value == "/" or value == "":
            return None

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            # 清理字符串，移除空格和逗号
            cleaned = value.strip().replace(",", "").replace(" ", "")
            if not cleaned or cleaned == "/" or cleaned == "None":
                return None
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                return None

        return None

    def _normalize_workshop_name(self, name: str) -> str:
        """标准化车间名称。"""
        name = name.strip()
        # 处理 "303、106车间" 这种格式
        if "、" in name:
            name = name.split("、")[0]
        # 纯数字名称自动加"车间"后缀（如 "101" → "101车间"）
        if re.match(r"^\d+$", name):
            name = name + "车间"
        return name

    async def _get_or_create_workshop(self, db: AsyncSession, name: str, category: str = "workshop") -> EnergyWorkshop:
        """获取或创建车间。"""
        normalized_name = self._normalize_workshop_name(name)

        # 先按名称查找
        result = await db.execute(select(EnergyWorkshop).where(EnergyWorkshop.name == normalized_name))
        workshop = result.scalar_one_or_none()
        if workshop:
            return workshop

        # 按 code 查找
        result = await db.execute(select(EnergyWorkshop).where(EnergyWorkshop.code == normalized_name))
        workshop = result.scalar_one_or_none()
        if workshop:
            return workshop

        # 创建新车间
        workshop = EnergyWorkshop(
            code=normalized_name,
            name=normalized_name,
            category=category,
            sort_order=0,
            is_active=True,
        )
        db.add(workshop)
        await db.flush()
        logger.info(f"Created workshop: {normalized_name}")
        return workshop

    def _detect_energy_type(self, field_value: str) -> str | None:
        """检测当前行属于哪个能源类型section。"""
        for energy_type, pattern in self.ENERGY_SECTION_PATTERNS.items():
            if pattern.search(field_value):
                return energy_type
        return None

    def _get_main_field_value(self, fields: dict[str, Any]) -> str | None:
        """获取主要字段的值（可能是三个字段中的任意一个）。"""
        for field_name in ["各车间电用量明细", "各车间蒸汽用量明细", "各车间自来水用量明细表"]:
            value = fields.get(field_name)
            if value:
                return str(value).strip()
        return None

    def _parse_cross_table(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """解析交叉表数据。

        数据结构：
        - 电力部分从第一条记录开始（没有标题行）
        - 蒸汽部分以 "各车间蒸汽用量明细" 开始
        - 自来水部分以 "各车间自来水用量明细表" 开始，且每个日期有两列：凉水塔用量和车间生产用水量
        """
        parsed_records = []
        current_energy_type = "electricity"  # 默认从电力开始
        current_unit = "kWh"
        date_columns: dict[str, tuple[date, date | None]] = {}
        water_subcategory: dict[str, str] = {}  # 自来水子类别映射
        expect_subcategory_row = False

        # 单位映射
        unit_map = {
            "electricity": "kWh",
            "steam": "t",
            "water": "m³",
            "natural_gas": "Nm³",
        }

        for i, record in enumerate(records):
            fields = record.get("fields", {})

            # 获取主要字段值
            main_value = self._get_main_field_value(fields)
            if not main_value:
                continue

            # 检查是否进入新的能源类型section
            detected_type = self._detect_energy_type(main_value)
            if detected_type:
                current_energy_type = detected_type
                current_unit = unit_map.get(detected_type, "")
                date_columns = {}
                water_subcategory = {}
                expect_subcategory_row = detected_type == "water"
                continue

            # 如果是空行或None，跳过
            if self._should_skip_workshop(main_value):
                continue

            # 检查是否是日期表头行
            if main_value == "日期":
                date_columns = {}
                for key, value in fields.items():
                    if key.startswith("列") and value:
                        parsed = self._parse_date_header(str(value))
                        if parsed:
                            date_columns[key] = parsed
                continue

            # 检查是否是子类别行（自来水部分）
            if main_value == "车间" and expect_subcategory_row:
                # 解析每个列的子类别
                for key in date_columns.keys():
                    subcat_value = fields.get(key)
                    if subcat_value:
                        water_subcategory[key] = str(subcat_value)
                expect_subcategory_row = False
                continue

            # 检查是否是单位行（蒸汽/电力部分）
            if main_value == "车间":
                continue

            # 检查是否是RTO用电行（跳过，但保留RTO天然气）
            if main_value == "RTO用电":
                continue

            # 检测天然气相关行
            if "天然气" in main_value:
                if "总表" in main_value or "合计" in main_value or "总量" in main_value:
                    # 跳过汇总行
                    continue
                # RTO(天然气）等实际数据行
                current_energy_type = "natural_gas"
                current_unit = "Nm³"
                # 继续处理为数据行

            # 解析数据行
            if date_columns and not self._should_skip_workshop(main_value):
                # 对于自来水部分，需要按日期汇总（合并凉水塔和生产用水）
                if current_energy_type == "water" and water_subcategory:
                    # 按日期汇总所有子类别的值
                    date_totals: dict[tuple[date, date | None], float] = {}
                    for col_key, (record_date, date_range_end) in date_columns.items():
                        value = self._parse_value(fields.get(col_key))
                        if value is not None and value > 0:
                            date_key = (record_date, date_range_end)
                            date_totals[date_key] = date_totals.get(date_key, 0) + float(value)

                    # 生成汇总记录
                    for (record_date, date_range_end), total_value in date_totals.items():
                        if total_value > 0:
                            parsed_records.append(
                                {
                                    "workshop_name": main_value,
                                    "energy_type": current_energy_type,
                                    "record_date": record_date,
                                    "date_range_end": date_range_end,
                                    "value": Decimal(str(total_value)),
                                    "unit": current_unit,
                                }
                            )
                else:
                    # 电力/蒸汽/天然气：直接按列解析
                    for col_key, (record_date, date_range_end) in date_columns.items():
                        value = self._parse_value(fields.get(col_key))
                        if value is not None and value > 0:
                            parsed_records.append(
                                {
                                    "workshop_name": main_value,
                                    "energy_type": current_energy_type,
                                    "record_date": record_date,
                                    "date_range_end": date_range_end,
                                    "value": value,
                                    "unit": current_unit,
                                }
                            )

        return parsed_records

    async def import_month(self, db: AsyncSession, table_name: str) -> dict[str, Any]:
        """导入单个月份的数据。"""
        # 获取所有表
        tables = await self.list_tables()
        table_id = None
        for t in tables:
            if t.get("name") == table_name:
                table_id = t.get("table_id")
                break

        if not table_id:
            return {"status": "error", "message": f"Table '{table_name}' not found"}

        # 获取所有记录
        records = await self.list_records(table_id)
        logger.info(f"Found {len(records)} records in table {table_name}")

        # 解析交叉表
        all_parsed = self._parse_cross_table(records)
        logger.info(f"Parsed {len(all_parsed)} records from table {table_name}")

        # 获取或创建车间并保存记录
        created = 0
        updated = 0
        errors = []

        for parsed in all_parsed:
            try:
                workshop = await self._get_or_create_workshop(db, parsed["workshop_name"])

                # 检查是否已存在
                result = await db.execute(
                    select(EnergyMonthlyRecord).where(
                        EnergyMonthlyRecord.workshop_id == workshop.id,
                        EnergyMonthlyRecord.energy_type == parsed["energy_type"],
                        EnergyMonthlyRecord.record_date == parsed["record_date"],
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.value = parsed["value"]
                    existing.unit = parsed["unit"]
                    existing.date_range_end = parsed["date_range_end"]
                    updated += 1
                else:
                    new_record = EnergyMonthlyRecord(
                        workshop_id=workshop.id,
                        energy_type=parsed["energy_type"],
                        record_date=parsed["record_date"],
                        date_range_end=parsed["date_range_end"],
                        value=parsed["value"],
                        unit=parsed["unit"],
                        source="feishu_bitable",
                    )
                    db.add(new_record)
                    created += 1

            except Exception as e:
                errors.append(f"Error processing {parsed}: {str(e)}")
                logger.exception(f"Error processing record: {parsed}")

        await db.commit()

        return {
            "status": "success",
            "table": table_name,
            "total_created": created,
            "total_updated": updated,
            "total_parsed": len(all_parsed),
            "errors": errors[:10],
        }

    async def import_year(self, db: AsyncSession, year: int) -> dict[str, Any]:
        """导入一整年的数据。"""
        tables = await self.list_tables()

        # 找到该年份的所有表
        year_tables = []
        for t in tables:
            name = t.get("name", "")
            # 匹配 "2026-06" 或 "202606" 格式
            if str(year) in name and ("-" in name or len(name) == 6):
                year_tables.append(name)

        year_tables.sort()
        logger.info(f"Found {len(year_tables)} tables for year {year}: {year_tables}")

        results = []
        total_created = 0
        total_updated = 0
        total_errors = []

        for table_name in year_tables:
            result = await self.import_month(db, table_name)
            results.append(result)
            total_created += result.get("created", 0)
            total_updated += result.get("updated", 0)
            total_errors.extend(result.get("errors", []))

        return {
            "status": "success",
            "year": year,
            "months_imported": len(year_tables),
            "total_created": total_created,
            "total_updated": total_updated,
            "total_errors": len(total_errors),
            "details": results,
        }
