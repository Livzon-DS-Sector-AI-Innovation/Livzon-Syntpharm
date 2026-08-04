"""Bidirectional sync service for product outputs and Feishu Bitable."""

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.product.feishu.bitable import (
    ProductBitableClient,
    _extract_date,
    _extract_number,
    _extract_text,
    _to_ms_timestamp,
)

logger = logging.getLogger(__name__)

DEFAULT_FIELD_MAPPING = {
    "workshop": "车间",
    "product_name": "产品名称",
    "batch_no": "批号",
    "production_date": "生产日期",
    "end_date": "结束日期",
    "weight": "重量",
    "unit": "单位",
    "notes": "备注",
}


class ProductSyncService:
    """Bidirectional sync between product outputs and Feishu Bitable."""

    def __init__(self, db: AsyncSession, app_token: str, table_id: str, field_mapping: dict[str, Any] | None = None):
        self.db = db
        self.bitable = ProductBitableClient(app_token, table_id)
        self.field_mapping = field_mapping or DEFAULT_FIELD_MAPPING
        self.reverse_mapping = {v: k for k, v in self.field_mapping.items()}

    async def push_to_feishu(self, product_id: str | None = None) -> dict[str, Any]:
        query = text("""
            SELECT id, workshop, product_name, batch_no, production_date, end_date, weight, unit, notes
            FROM production.product_outputs
            WHERE is_deleted = false
            AND sync_status = 'local_only'
            AND (product_id = :product_id OR :product_id IS NULL)
        """)
        result = await self.db.execute(query, {"product_id": product_id})
        rows = result.fetchall()

        imported = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        for row in rows:
            record_id, workshop, product_name, batch_no, production_date, end_date, weight, unit, notes = row

            fields = self._build_feishu_fields(
                {
                    "workshop": workshop,
                    "product_name": product_name,
                    "batch_no": batch_no,
                    "production_date": production_date,
                    "end_date": end_date,
                    "weight": weight,
                    "unit": unit,
                    "notes": notes,
                }
            )

            feishu_record_id = await self._find_feishu_record(batch_no, product_name, workshop, production_date)

            try:
                if feishu_record_id:
                    await self.bitable.update_record(feishu_record_id, fields)
                    updated += 1
                    await self.db.execute(
                        text("""
                        UPDATE production.product_outputs
                        SET feishu_record_id = :feishu_record_id, sync_status = 'synced'
                        WHERE id = :record_id
                    """),
                        {"feishu_record_id": feishu_record_id, "record_id": record_id},
                    )
                else:
                    create_result = await self.bitable.create_record(fields)
                    feishu_record_id = create_result.get("record_id")
                    imported += 1
                    await self.db.execute(
                        text("""
                        UPDATE production.product_outputs
                        SET feishu_record_id = :feishu_record_id, sync_status = 'synced'
                        WHERE id = :record_id
                    """),
                        {"feishu_record_id": feishu_record_id, "record_id": record_id},
                    )
            except Exception as e:
                errors.append(f"批号 {batch_no}: {str(e)}")
                logger.error("Failed to push record %s to Feishu: %s", batch_no, e)

        await self.db.commit()

        return {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "message": f"推送完成：新增 {imported} 条，更新 {updated} 条，失败 {len(errors)} 条",
        }

    async def pull_from_feishu(self, product_id: str | None = None) -> dict[str, Any]:
        logger.info("开始从飞书拉取数据")
        feishu_records = await self.bitable.list_records()
        logger.info(f"获取到 {len(feishu_records)} 条飞书记录")

        imported = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        for feishu_record in feishu_records:
            record_id = feishu_record.get("record_id", "")
            fields = feishu_record.get("fields", {})

            data = self._extract_record_data(fields)
            logger.info(f"记录 {record_id} 提取数据: {data}")

            workshop = str(data.get("workshop", "")).strip()
            product_name = str(data.get("product_name", "")).strip()
            batch_no = str(data.get("batch_no", "")).strip()
            production_date_str = str(data.get("production_date", "")).strip()
            end_date_str = str(data.get("end_date", "")).strip()
            weight = data.get("weight", 0.0)
            unit = str(data.get("unit", "kg")).strip() or "kg"
            notes = str(data.get("notes", "")).strip() or None

            if not workshop or not product_name or not batch_no or not production_date_str:
                continue

            try:
                production_date = date.fromisoformat(production_date_str)
                end_date = date.fromisoformat(end_date_str) if end_date_str else None
            except ValueError:
                continue

            result = await self.db.execute(
                text("""
                SELECT id, feishu_record_id, sync_status FROM production.product_outputs
                WHERE is_deleted = false
                AND workshop = :workshop
                AND product_name = :product_name
                AND batch_no = :batch_no
                AND production_date = :production_date
            """),
                {
                    "workshop": workshop,
                    "product_name": product_name,
                    "batch_no": batch_no,
                    "production_date": production_date,
                },
            )
            existing = result.first()

            try:
                if existing:
                    local_id = existing[0]
                    await self.db.execute(
                        text("""
                        UPDATE production.product_outputs
                        SET weight = :weight, unit = :unit, notes = :notes,
                            end_date = :end_date, feishu_record_id = :feishu_record_id,
                            sync_status = 'synced'
                        WHERE id = :local_id
                    """),
                        {
                            "weight": weight,
                            "unit": unit,
                            "notes": notes,
                            "end_date": end_date,
                            "feishu_record_id": record_id,
                            "local_id": local_id,
                        },
                    )
                    updated += 1
                else:
                    product_result = await self.db.execute(
                        text("""
                        SELECT id FROM production.products
                        WHERE name = :product_name AND workshop = :workshop AND is_deleted = false
                        LIMIT 1
                    """),
                        {"product_name": product_name, "workshop": workshop},
                    )
                    product_row = product_result.first()
                    pid = product_row[0] if product_row else None

                    await self.db.execute(
                        text("""
                        INSERT INTO production.product_outputs
                        (id, product_id, workshop, product_name, batch_no,
                         production_date, end_date, weight, unit, notes,
                         feishu_record_id, sync_status)
                        VALUES (gen_random_uuid(), :product_id, :workshop, :product_name, :batch_no,
                                :production_date, :end_date, :weight, :unit, :notes,
                                :feishu_record_id, 'synced')
                    """),
                        {
                            "product_id": pid,
                            "workshop": workshop,
                            "product_name": product_name,
                            "batch_no": batch_no,
                            "production_date": production_date,
                            "end_date": end_date,
                            "weight": weight,
                            "unit": unit,
                            "notes": notes,
                            "feishu_record_id": record_id,
                        },
                    )
                    imported += 1
            except Exception as e:
                errors.append(f"批号 {batch_no}: {str(e)}")
                logger.error("Failed to pull record %s from Feishu: %s", batch_no, e)

        await self.db.commit()

        return {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "message": f"拉取完成：新增 {imported} 条，更新 {updated} 条，失败 {len(errors)} 条",
        }

    async def bidirectional_sync(self, product_id: str | None = None) -> dict[str, Any]:
        push_result = await self.push_to_feishu(product_id)
        pull_result = await self.pull_from_feishu(product_id)

        return {
            "push": push_result,
            "pull": pull_result,
            "message": f"双向同步完成 - 推送: {push_result['message']} | 拉取: {pull_result['message']}",
        }

    def _build_feishu_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for system_field, feishu_field in self.field_mapping.items():
            value = data.get(system_field)
            if value is None:
                continue
            if system_field in ("production_date", "end_date"):
                fields[feishu_field] = _to_ms_timestamp(value)
            elif system_field == "weight":
                fields[feishu_field] = float(value)
            elif system_field == "notes":
                fields[feishu_field] = str(value) if value else ""
            else:
                fields[feishu_field] = str(value)
        return fields

    def _extract_record_data(self, fields: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        text_fields = ("workshop", "product_name", "batch_no", "unit", "notes")
        number_fields = ("weight",)
        date_fields = ("production_date", "end_date")

        for feishu_field, system_field in self.reverse_mapping.items():
            if feishu_field not in fields:
                continue
            raw_value = fields[feishu_field]
            if system_field in text_fields:
                data[system_field] = _extract_text(raw_value)
            elif system_field in number_fields:
                data[system_field] = _extract_number(raw_value)
            elif system_field in date_fields:
                data[system_field] = _extract_date(raw_value)
        return data

    async def _find_feishu_record(
        self, batch_no: str, product_name: str, workshop: str, production_date: date
    ) -> str | None:
        filter_str = (
            f'CurrentValue.[批号] = "{batch_no}" AND '
            f'CurrentValue.[产品名称] = "{product_name}" AND '
            f'CurrentValue.[车间] = "{workshop}"'
        )
        items = await self.bitable.search_records(filter_str=filter_str)
        return items[0].get("record_id") if items else None
