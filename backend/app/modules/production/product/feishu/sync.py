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


    async def preview_push(self, product_id: str | None = None) -> dict[str, Any]:
        """预览推送操作，不实际执行"""
        logger.info("预览推送到飞书")
        
        # 获取飞书所有记录
        all_feishu_records = await self.bitable.list_records(page_size=500)
        feishu_record_map = {}
        for record in all_feishu_records:
            fields = record.get("fields", {})
            batch_no = str(fields.get("批号（批次编号）", ""))
            product_name = str(fields.get("产品名称（产品）", ""))
            workshop = str(fields.get("车间（生产车间）", ""))
            if batch_no and product_name and workshop:
                key = (batch_no, product_name, workshop)
                feishu_record_map[key] = record.get("record_id")
        
        # 查询平台记录
        query = text("""
            SELECT id, workshop, product_name, batch_no, production_date, end_date, weight, unit, notes
            FROM production.product_outputs
            WHERE is_deleted = false
            AND (product_id = :product_id OR :product_id IS NULL)
        """)
        result = await self.db.execute(query, {"product_id": product_id})
        rows = result.fetchall()
        
        # 分析变更
        to_create = []
        to_update = []
        to_skip = []
        
        for row in rows:
            record_id, workshop, product_name, batch_no, production_date, end_date, weight, unit, notes = row
            key = (batch_no, product_name, workshop)
            
            if key in feishu_record_map:
                to_update.append({
                    "batch_no": batch_no,
                    "product_name": product_name,
                    "workshop": workshop,
                    "production_date": str(production_date),
                    "weight": weight,
                    "action": "更新"
                })
            else:
                to_create.append({
                    "batch_no": batch_no,
                    "product_name": product_name,
                    "workshop": workshop,
                    "production_date": str(production_date),
                    "weight": weight,
                    "action": "新增"
                })
        
        return {
            "to_create": len(to_create),
            "to_update": len(to_update),
            "to_skip": len(to_skip),
            "details": to_create + to_update
        }

    async def preview_pull(self, product_id: str | None = None) -> dict[str, Any]:
        """预览拉取操作，不实际执行"""
        logger.info("预览从飞书拉取")
        
        # 获取飞书所有记录
        all_feishu_records = await self.bitable.list_records(page_size=500)
        
        # 查询平台现有记录
        query = text("""
            SELECT batch_no, product_name, workshop, production_date
            FROM production.product_outputs
            WHERE is_deleted = false
            AND (product_id = :product_id OR :product_id IS NULL)
        """)
        result = await self.db.execute(query, {"product_id": product_id})
        existing_records = {(row[0], row[1], row[2], str(row[3])) for row in result.fetchall()}
        
        # 分析变更
        to_create = []
        to_update = []
        
        for record in all_feishu_records:
            fields = record.get("fields", {})
            batch_no = str(fields.get("批号（批次编号）", ""))
            product_name = str(fields.get("产品名称（产品）", ""))
            workshop = str(fields.get("车间（生产车间）", ""))
            production_date_raw = fields.get("生产日期（生产开始日）")
            
            if not batch_no or not product_name or not workshop:
                continue
            
            # 解析日期
            if isinstance(production_date_raw, int):
                from datetime import datetime, timezone
                dt = datetime.fromtimestamp(production_date_raw / 1000, tz=timezone.utc)
                production_date = dt.strftime("%Y-%m-%d")
            else:
                production_date = str(production_date_raw) if production_date_raw else ""
            
            key = (batch_no, product_name, workshop, production_date)
            weight = fields.get("重量（产出量）", 0)
            
            if key in existing_records:
                to_update.append({
                    "batch_no": batch_no,
                    "product_name": product_name,
                    "workshop": workshop,
                    "production_date": production_date,
                    "weight": weight,
                    "action": "更新"
                })
            else:
                to_create.append({
                    "batch_no": batch_no,
                    "product_name": product_name,
                    "workshop": workshop,
                    "production_date": production_date,
                    "weight": weight,
                    "action": "新增"
                })
        
        return {
            "to_create": len(to_create),
            "to_update": len(to_update),
            "details": to_create + to_update
        }

    async def push_to_feishu(self, product_id: str | None = None) -> dict[str, Any]:
        logger.info("开始推送到飞书")
        
        # 一次性获取飞书所有记录，建立批号→record_id 映射
        logger.info("获取飞书所有记录...")
        all_feishu_records = await self.bitable.list_records(page_size=500)
        feishu_record_map = {}  # (batch_no, product_name, workshop) -> record_id
        for record in all_feishu_records:
            fields = record.get("fields", {})
            batch_no = str(fields.get("批号（批次编号）", ""))
            product_name = str(fields.get("产品名称（产品）", ""))
            workshop = str(fields.get("车间（生产车间）", ""))
            if batch_no and product_name and workshop:
                key = (batch_no, product_name, workshop)
                feishu_record_map[key] = record.get("record_id")
        logger.info(f"飞书现有 {len(feishu_record_map)} 条记录")
        
        query = text("""
            SELECT id, workshop, product_name, batch_no, production_date, end_date, weight, unit, notes
            FROM production.product_outputs
            WHERE is_deleted = false
            AND (product_id = :product_id OR :product_id IS NULL)
        """)
        result = await self.db.execute(query, {"product_id": product_id})
        rows = result.fetchall()
        logger.info(f"查询到 {len(rows)} 条待推送记录")

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

            # 直接从映射表查找，不再调用 API
            key = (batch_no, product_name, workshop)
            feishu_record_id = feishu_record_map.get(key)
            logger.info(f"批号 {batch_no} 飞书记录 ID: {feishu_record_id}")

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

        # 记录操作日志
        operation_records = [
            {"batch_no": r["batch_no"], "action": r["action"]}
            for r in (to_create + to_update)
        ]
        await SyncOperationLog.log_operation(
            self.db, product_id or "", "push", operation_records
        )

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

        # 记录操作日志
        operation_records = [
            {"batch_no": r["batch_no"], "action": r["action"]}
            for r in (to_create + to_update)
        ]
        await SyncOperationLog.log_operation(
            self.db, product_id or "", "pull", operation_records
        )

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
        # 飞书 filter API 不支持带括号的字段名，改用获取所有记录后在代码中匹配
        all_records = await self.bitable.list_records(page_size=500)
        for record in all_records:
            fields = record.get("fields", {})
            record_batch = str(fields.get("批号（批次编号）", ""))
            record_product = str(fields.get("产品名称（产品）", ""))
            record_workshop = str(fields.get("车间（生产车间）", ""))
            if record_batch == batch_no and record_product == product_name and record_workshop == workshop:
                return record.get("record_id")
        return None


class SyncOperationLog:
    """同步操作日志"""
    
    @staticmethod
    async def log_operation(
        db: AsyncSession,
        product_id: str,
        operation_type: str,  # 'push' or 'pull'
        records: list[dict[str, Any]],
    ) -> str:
        """记录同步操作日志"""
        import uuid as uuid_module
        log_id = str(uuid_module.uuid4())
        
        await db.execute(
            text("""
            INSERT INTO production.sync_operation_logs
            (id, product_id, operation_type, records, created_at)
            VALUES (:id, :product_id, :operation_type, :records, NOW())
            """),
            {
                "id": log_id,
                "product_id": product_id,
                "operation_type": operation_type,
                "records": json.dumps(records),
            }
        )
        await db.commit()
        return log_id
    
    @staticmethod
    async def get_operation_log(db: AsyncSession, log_id: str) -> dict[str, Any] | None:
        """获取操作日志"""
        result = await db.execute(
            text("""
            SELECT id, product_id, operation_type, records, created_at
            FROM production.sync_operation_logs
            WHERE id = :log_id
            """),
            {"log_id": log_id}
        )
        row = result.first()
        if row:
            return {
                "id": row[0],
                "product_id": str(row[1]),
                "operation_type": row[2],
                "records": json.loads(row[3]) if row[3] else [],
                "created_at": row[4],
            }
        return None
    
    @staticmethod
    async def get_latest_operation(db: AsyncSession, product_id: str) -> dict[str, Any] | None:
        """获取最新操作日志"""
        result = await db.execute(
            text("""
            SELECT id, product_id, operation_type, records, created_at
            FROM production.sync_operation_logs
            WHERE product_id = :product_id
            ORDER BY created_at DESC
            LIMIT 1
            """),
            {"product_id": product_id}
        )
        row = result.first()
        if row:
            return {
                "id": row[0],
                "product_id": str(row[1]),
                "operation_type": row[2],
                "records": json.loads(row[3]) if row[3] else [],
                "created_at": row[4],
            }
        return None
