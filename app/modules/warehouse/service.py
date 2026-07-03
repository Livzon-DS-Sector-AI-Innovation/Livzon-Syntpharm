"""Warehouse business workflows live here."""
import logging

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.redis import redis_client
from app.core.secrets import decrypt_secret, encrypt_secret, mask_secret
from app.modules.warehouse.feishu_client import WarehouseFeishuClient
from app.modules.warehouse.models import (
    PackagingMaterialInventory,
    ProductInventory,
    RawMaterialInventory,
    WarehouseFeishuConfig,
    WarehouseFeishuField,
    WarehouseFeishuRecord,
    WarehouseFeishuTable,
)
from app.modules.warehouse.repository import WarehouseRepository
from app.modules.warehouse.schemas import (
    WAREHOUSE_FEISHU_DOMAIN_LABELS,
    WarehouseFeishuBusinessDomain,
    WarehouseFeishuConfigResponse,
    WarehouseFeishuConfigUpsert,
    WarehouseFeishuConnectivityResult,
    WarehouseFeishuConnectivityStep,
    WarehouseFeishuFieldResponse,
    WarehouseFeishuRawRecordData,
    WarehouseFeishuRawRecordResponse,
    WarehouseFeishuTableResponse,
    WarehouseFeishuTableSyncResult,
)


logger = logging.getLogger(__name__)

def _safe_number(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def build_warehouse_import_key(*parts: str | None) -> str:
    normalized = "|".join((part or "").strip().lower() for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class WarehouseService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = WarehouseRepository(session)

    async def list_raw_materials(self) -> list[RawMaterialInventory]:
        return await self.repo.list_raw_materials()

    async def list_packaging_materials(self) -> list[PackagingMaterialInventory]:
        return await self.repo.list_packaging_materials()

    async def list_products(self) -> list[ProductInventory]:
        return await self.repo.list_products()

    async def upsert_raw_material_snapshot(
        self,
        *,
        source_id: str | None,
        code: str,
        name: str,
        spec: str | None,
        unit: str | None,
        available: float | int | None,
        safety: float | int | None,
        last_month: float | int | None,
        two_months_ago: float | int | None,
        today_balance: float | int | None,
        front_stock: float | int | None,
        this_month_use: float | int | None,
        warning: str | None,
        product_line: str | None,
        erp_no: str | None,
        delivery: str | None,
        remark: str | None,
        source: str,
    ) -> RawMaterialInventory:
        import_key = build_warehouse_import_key(source_id, code, name, product_line)
        existing = await self.repo.get_raw_material_by_import_key(import_key)
        payload = {
            "source_id": source_id,
            "code": code,
            "name": name,
            "spec": spec,
            "unit": unit,
            "available": _safe_number(available),
            "safety": _safe_number(safety),
            "last_month": _safe_number(last_month),
            "two_months_ago": _safe_number(two_months_ago),
            "today_balance": _safe_number(today_balance),
            "front_stock": _safe_number(front_stock),
            "this_month_use": _safe_number(this_month_use),
            "warning": warning,
            "product_line": product_line,
            "erp_no": erp_no,
            "delivery": delivery,
            "remark": remark,
            "source": source,
            "import_key": import_key,
            "last_synced_at": datetime.now(UTC),
        }
        if existing:
            for field, value in payload.items():
                setattr(existing, field, value)
            existing.is_deleted = False
            await self.repo.session.flush()
            return existing

        item = RawMaterialInventory(**payload)
        return await self.repo.create_raw_material(item)

    async def upsert_packaging_snapshot(
        self,
        *,
        source_id: str | None,
        code: str,
        name: str,
        spec: str | None,
        batch: str | None,
        available: float | int | None,
        safety: float | int | None,
        last_month: float | int | None,
        two_months_ago: float | int | None,
        today_balance: float | int | None,
        front_stock: float | int | None,
        this_month_use: float | int | None,
        warning: str | None,
        product_line: str | None,
        erp_no: str | None,
        delivery: str | None,
        remark: str | None,
        source: str,
    ) -> PackagingMaterialInventory:
        import_key = build_warehouse_import_key(source_id, code, name, product_line)
        existing = await self.repo.get_packaging_material_by_import_key(import_key)
        payload = {
            "source_id": source_id,
            "code": code,
            "name": name,
            "spec": spec,
            "batch": batch,
            "available": _safe_number(available),
            "safety": _safe_number(safety),
            "last_month": _safe_number(last_month),
            "two_months_ago": _safe_number(two_months_ago),
            "today_balance": _safe_number(today_balance),
            "front_stock": _safe_number(front_stock),
            "this_month_use": _safe_number(this_month_use),
            "warning": warning,
            "product_line": product_line,
            "erp_no": erp_no,
            "delivery": delivery,
            "remark": remark,
            "source": source,
            "import_key": import_key,
            "last_synced_at": datetime.now(UTC),
        }
        if existing:
            for field, value in payload.items():
                setattr(existing, field, value)
            existing.is_deleted = False
            await self.repo.session.flush()
            return existing

        item = PackagingMaterialInventory(**payload)
        return await self.repo.create_packaging_material(item)

    async def upsert_product_snapshot(
        self,
        *,
        source_id: str | None,
        name: str,
        spec: str | None,
        order_quantity: float | int | None,
        pending_quantity: float | int | None,
        qualified_quantity: float | int | None,
        subtotal_quantity: float | int | None,
        remaining_quantity: float | int | None,
        unit: str | None,
        remark: str | None,
        source: str,
    ) -> ProductInventory:
        import_key = build_warehouse_import_key(source_id, name, spec, unit)
        existing = await self.repo.get_product_by_import_key(import_key)
        payload = {
            "source_id": source_id,
            "name": name,
            "spec": spec,
            "order_quantity": _safe_number(order_quantity),
            "pending_quantity": _safe_number(pending_quantity),
            "qualified_quantity": _safe_number(qualified_quantity),
            "subtotal_quantity": _safe_number(subtotal_quantity),
            "remaining_quantity": _safe_number(remaining_quantity),
            "unit": unit,
            "remark": remark,
            "source": source,
            "import_key": import_key,
            "last_synced_at": datetime.now(UTC),
        }
        if existing:
            for field, value in payload.items():
                setattr(existing, field, value)
            existing.is_deleted = False
            await self.repo.session.flush()
            return existing

        item = ProductInventory(**payload)
        return await self.repo.create_product(item)

    async def get_feishu_config_response(self) -> WarehouseFeishuConfigResponse:
        config = await self.repo.get_any_feishu_config()
        if not config:
            return WarehouseFeishuConfigResponse(
                id=None,
                config_name="仓储飞书配置",
                app_id="",
                finished_product_app_token=None,
                materials_packaging_app_token=None,
                hardware_app_token=None,
                bitable_app_token=None,
                is_active=True,
                remark=None,
                app_secret_configured=False,
                app_secret_masked="",
            )
        return self._to_feishu_config_response(config)

    async def save_feishu_config(
        self, data: WarehouseFeishuConfigUpsert
    ) -> WarehouseFeishuConfigResponse:
        existing = await self.repo.get_any_feishu_config()
        legacy_token = self._legacy_app_token(data)
        if existing:
            existing.config_name = data.config_name
            existing.app_id = data.app_id
            if data.app_secret:
                existing.encrypted_app_secret = encrypt_secret(data.app_secret)
            existing.bitable_app_token = legacy_token
            existing.finished_product_app_token = data.finished_product_app_token
            existing.materials_packaging_app_token = data.materials_packaging_app_token
            existing.hardware_app_token = data.hardware_app_token
            existing.is_active = data.is_active
            existing.remark = data.remark
            await self.repo.session.flush()
            await self.repo.session.commit()
            if existing.is_active:
                await self._after_feishu_config_saved(existing)
            return self._to_feishu_config_response(existing)

        if not data.app_secret:
            raise AppException(message="首次保存飞书配置时必须填写 App Secret")

        config = WarehouseFeishuConfig(
            config_name=data.config_name,
            app_id=data.app_id,
            encrypted_app_secret=encrypt_secret(data.app_secret),
            bitable_app_token=legacy_token,
            finished_product_app_token=data.finished_product_app_token,
            materials_packaging_app_token=data.materials_packaging_app_token,
            hardware_app_token=data.hardware_app_token,
            raw_material_table_id=None,
            packaging_table_id=None,
            product_table_id=None,
            is_active=data.is_active,
            remark=data.remark,
        )
        await self.repo.save_feishu_config(config)
        await self.repo.session.commit()
        if config.is_active:
            await self._after_feishu_config_saved(config)
        return self._to_feishu_config_response(config)

    async def test_feishu_connectivity(
        self, data: WarehouseFeishuConfigUpsert | None = None
    ) -> WarehouseFeishuConnectivityResult:
        config = await self._resolve_feishu_config(data)
        steps: list[WarehouseFeishuConnectivityStep] = []

        token = await self._test_tenant_token(config, steps)
        if not token:
            return WarehouseFeishuConnectivityResult(ok=False, steps=steps)

        app_tokens = self._config_app_tokens(config)
        if not app_tokens:
            steps.append(
                WarehouseFeishuConnectivityStep(
                    name="多维表格",
                    status="warning",
                    message="未配置任何业务域 app_token，仅完成应用凭证测试",
                )
            )
            return WarehouseFeishuConnectivityResult(ok=True, steps=steps)

        for domain, app_token in app_tokens.items():
            label = WAREHOUSE_FEISHU_DOMAIN_LABELS[domain]
            try:
                client = self._build_feishu_client(config, app_token)
                tables = await client.list_tables()
                await self._save_discovered_feishu_tables(domain, app_token, tables)
                steps.append(
                    WarehouseFeishuConnectivityStep(
                        name=f"{label}表目录",
                        status="ok",
                        message=f"已发现 {len(tables)} 张数据表",
                    )
                )
            except Exception as exc:
                steps.append(
                    WarehouseFeishuConnectivityStep(
                        name=f"{label}表目录",
                        status="error",
                        message=f"读取数据表失败：{exc}",
                    )
                )

        ok = all(step.status in {"ok", "warning"} for step in steps)
        return WarehouseFeishuConnectivityResult(ok=ok, steps=steps)

    async def list_feishu_tables(
        self,
        *,
        business_domain: str | None = None,
        keyword: str | None = None,
        enabled: bool | None = None,
    ) -> list[WarehouseFeishuTable]:
        await self._get_active_feishu_config_or_raise()
        self._validate_optional_domain(business_domain)
        return await self.repo.list_feishu_tables(
            business_domain=business_domain,
            keyword=keyword,
            enabled=enabled,
        )

    async def refresh_feishu_tables(self) -> list[WarehouseFeishuTable]:
        config = await self._get_active_feishu_config_or_raise()
        discovered: list[WarehouseFeishuTable] = []
        for domain, app_token in self._config_app_tokens(config).items():
            client = self._build_feishu_client(config, app_token)
            raw_tables = await client.list_tables()
            discovered.extend(
                await self._save_discovered_feishu_tables(domain, app_token, raw_tables)
            )
        return discovered

    async def set_feishu_table_enabled(
        self, table_pk: UUID, is_enabled: bool
    ) -> WarehouseFeishuTable:
        table = await self._get_table_by_id_or_raise(table_pk)
        table.is_enabled = is_enabled
        table.sync_error = None
        table.sync_status = "enabled" if is_enabled else "disabled"
        await self.repo.session.commit()
        if is_enabled:
            await self.sync_feishu_table(table_pk)
            return await self._get_table_by_id_or_raise(table_pk)
        return table

    async def set_feishu_tables_enabled(
        self, table_pks: list[UUID], is_enabled: bool
    ) -> list[WarehouseFeishuTable]:
        if not table_pks:
            return []

        updated: list[WarehouseFeishuTable] = []
        seen: set[UUID] = set()
        for table_pk in table_pks:
            if table_pk in seen:
                continue
            seen.add(table_pk)
            table = await self._get_table_by_id_or_raise(table_pk)
            table.is_enabled = is_enabled
            table.sync_error = None
            table.sync_status = "pending" if is_enabled else "disabled"
            updated.append(table)

        await self.repo.session.commit()
        return updated

    async def sync_feishu_table(self, table_pk: UUID) -> WarehouseFeishuTableSyncResult:
        config = await self._get_active_feishu_config_or_raise()
        table = await self._get_table_by_id_or_raise(table_pk)
        if table.app_token not in set(self._config_app_tokens(config).values()):
            raise AppException(message="该数据表不属于当前启用的仓储飞书配置")
        return await self._sync_feishu_table(config, table)

    async def get_feishu_table_records(
        self,
        table_pk: UUID,
        *,
        keyword: str | None = None,
        field: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> WarehouseFeishuRawRecordData:
        table = await self._get_table_by_id_or_raise(table_pk)
        return await self._get_records_for_table(
            table=table,
            keyword=keyword,
            field=field,
            page=page,
            page_size=page_size,
        )

    async def get_feishu_domain_records(
        self,
        business_domain: WarehouseFeishuBusinessDomain,
        *,
        table_id: UUID | None = None,
        keyword: str | None = None,
        field: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> WarehouseFeishuRawRecordData:
        if table_id:
            table = await self._get_table_by_id_or_raise(table_id)
            if table.business_domain != business_domain:
                raise AppException(message="选择的数据表不属于当前仓储菜单")
        else:
            tables = await self.repo.list_feishu_tables(
                business_domain=business_domain,
                enabled=True,
            )
            table = tables[0] if tables else None
        if not table:
            return WarehouseFeishuRawRecordData(fields=[], records=[], total=0)
        return await self._get_records_for_table(
            table=table,
            keyword=keyword,
            field=field,
            page=page,
            page_size=page_size,
        )

    async def handle_feishu_bitable_record_changed(
        self,
        *,
        file_token: str,
        table_id: str,
        revision: int | None,
        update_time: int | None,
        actions: list[dict[str, str | None]],
    ) -> dict[str, str | bool | None]:
        config = await self.repo.get_active_feishu_config()
        if not config:
            return {"matched": False, "status": "no_active_config"}

        table = await self.repo.get_enabled_feishu_table(file_token, table_id)
        if not table:
            return {"matched": False, "status": "ignored"}

        event_id = revision or update_time or "unknown"
        dedup_key = f"warehouse:feishu:event:{file_token}:{table_id}:{event_id}"
        is_new = await redis_client.set(dedup_key, "1", ex=300, nx=True)
        if not is_new:
            return {
                "matched": True,
                "status": "duplicate",
                "table_kind": table.business_domain,
            }

        table.last_event_at = datetime.now(UTC)
        action_summary = ",".join(
            f"{item.get('action') or 'unknown'}:{item.get('record_id') or ''}"
            for item in actions[:20]
        )
        await redis_client.set(
            f"warehouse:feishu:last_event:{table.business_domain}",
            action_summary,
            ex=86400,
        )
        try:
            await self._sync_feishu_table(config, table)
        except Exception as exc:
            table.sync_status = "failed"
            table.sync_error = str(exc)
            await self.repo.session.commit()
            return {
                "matched": True,
                "status": "sync_failed",
                "table_kind": table.business_domain,
            }

        return {
            "matched": True,
            "status": "synced",
            "table_kind": table.business_domain,
        }

    async def _save_discovered_feishu_tables(
        self,
        business_domain: str,
        app_token: str,
        raw_tables: list[dict[str, Any]],
    ) -> list[WarehouseFeishuTable]:
        discovered: list[WarehouseFeishuTable] = []
        now = datetime.now(UTC)

        for item in raw_tables:
            table_id = str(item.get("table_id") or "").strip()
            if not table_id:
                continue
            table = await self.repo.get_feishu_table(
                business_domain,
                app_token,
                table_id,
            )
            if not table:
                table = WarehouseFeishuTable(
                    business_domain=business_domain,
                    app_token=app_token,
                    table_id=table_id,
                    name=str(item.get("name") or table_id),
                    revision=self._safe_int(item.get("revision")),
                    last_discovered_at=now,
                    sync_status="pending",
                )
                await self.repo.save_feishu_table(table)
            else:
                table.name = str(item.get("name") or table.name or table_id)
                table.revision = self._safe_int(item.get("revision"))
                table.last_discovered_at = now
                table.is_deleted = False
            discovered.append(table)

        await self.repo.session.commit()
        return discovered

    async def _sync_feishu_table(
        self, config: WarehouseFeishuConfig, table: WarehouseFeishuTable
    ) -> WarehouseFeishuTableSyncResult:
        table.sync_status = "syncing"
        table.sync_error = None
        await self.repo.session.flush()

        try:
            client = self._build_feishu_client(config, table.app_token)
            raw_fields = await client.list_fields(table.table_id)
            raw_records = await self._read_all_records(client, table.table_id)
            now = datetime.now(UTC)

            for item in raw_fields:
                field = self._field_from_raw(item)
                existing = await self.repo.get_feishu_field(
                    table.business_domain,
                    table.app_token,
                    table.table_id,
                    field.field_id,
                )
                payload = {
                    "field_name": field.field_name,
                    "field_type": field.type,
                    "property": field.property,
                    "last_synced_at": now,
                    "is_deleted": False,
                }
                if existing:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                else:
                    await self.repo.save_feishu_field(
                        WarehouseFeishuField(
                            business_domain=table.business_domain,
                            app_token=table.app_token,
                            table_id=table.table_id,
                            field_id=field.field_id,
                            **payload,
                        )
                    )

            active_record_ids: set[str] = set()
            for item in raw_records:
                record = self._record_from_raw(item)
                if not record.record_id:
                    continue
                active_record_ids.add(record.record_id)
                existing = await self.repo.get_feishu_record(
                    table.business_domain,
                    table.app_token,
                    table.table_id,
                    record.record_id,
                )
                payload = {
                    "fields": record.fields,
                    "search_text": self._build_search_text(record.fields),
                    "feishu_created_time": record.created_time,
                    "feishu_last_modified_time": record.last_modified_time,
                    "last_synced_at": now,
                    "is_deleted": False,
                }
                if existing:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                else:
                    await self.repo.save_feishu_record(
                        WarehouseFeishuRecord(
                            business_domain=table.business_domain,
                            app_token=table.app_token,
                            table_id=table.table_id,
                            record_id=record.record_id,
                            **payload,
                        )
                    )

            await self.repo.mark_missing_feishu_records_deleted(
                business_domain=table.business_domain,
                app_token=table.app_token,
                table_id=table.table_id,
                active_record_ids=active_record_ids,
            )

            table.field_count = len(raw_fields)
            table.record_count = len(active_record_ids)
            table.last_synced_at = now
            table.sync_status = "success"
            table.sync_error = None
            await self.repo.session.commit()
            return WarehouseFeishuTableSyncResult(
                table=self._to_table_response(table),
                field_count=table.field_count,
                record_count=table.record_count,
            )
        except Exception as exc:
            table.sync_status = "failed"
            table.sync_error = str(exc)
            await self.repo.session.commit()
            raise

    async def _read_all_records(
        self, client: WarehouseFeishuClient, table_id: str
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            data = await client.search_records(
                table_id,
                page_size=500,
                page_token=page_token,
            )
            records.extend(data.get("items") or [])
            if not data.get("has_more"):
                break
            page_token = str(data.get("page_token") or "")
            if not page_token:
                break
        return records

    async def _get_records_for_table(
        self,
        *,
        table: WarehouseFeishuTable,
        keyword: str | None,
        field: str | None,
        page: int,
        page_size: int,
    ) -> WarehouseFeishuRawRecordData:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), 200)
        fields = await self.repo.list_feishu_fields(
            table.business_domain,
            table.app_token,
            table.table_id,
        )
        records, total = await self.repo.list_feishu_records(
            business_domain=table.business_domain,
            app_token=table.app_token,
            table_id=table.table_id,
            keyword=keyword,
            field=field,
            page=normalized_page,
            page_size=normalized_page_size,
        )
        return WarehouseFeishuRawRecordData(
            table=self._to_table_response(table),
            fields=[self._to_field_response(item) for item in fields],
            records=[self._to_record_response(item) for item in records],
            page=normalized_page,
            page_size=normalized_page_size,
            total=total,
        )

    def _to_feishu_config_response(
        self, config: WarehouseFeishuConfig
    ) -> WarehouseFeishuConfigResponse:
        return WarehouseFeishuConfigResponse(
            id=config.id,
            config_name=config.config_name,
            app_id=config.app_id,
            finished_product_app_token=config.finished_product_app_token,
            materials_packaging_app_token=(
                config.materials_packaging_app_token or config.bitable_app_token
            ),
            hardware_app_token=config.hardware_app_token,
            bitable_app_token=config.bitable_app_token,
            is_active=config.is_active,
            remark=config.remark,
            app_secret_configured=bool(config.encrypted_app_secret),
            app_secret_masked=self._mask_encrypted_secret(config.encrypted_app_secret),
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    async def _resolve_feishu_config(
        self, data: WarehouseFeishuConfigUpsert | None
    ) -> WarehouseFeishuConfig:
        if data:
            if data.app_secret:
                encrypted_secret = encrypt_secret(data.app_secret)
            else:
                stored = await self._get_any_feishu_config_or_raise()
                encrypted_secret = stored.encrypted_app_secret if stored else ""
            if not encrypted_secret:
                raise AppException(message="请填写 App Secret 后再测试连通性")
            return WarehouseFeishuConfig(
                config_name=data.config_name,
                app_id=data.app_id,
                encrypted_app_secret=encrypted_secret,
                bitable_app_token=self._legacy_app_token(data),
                finished_product_app_token=data.finished_product_app_token,
                materials_packaging_app_token=data.materials_packaging_app_token,
                hardware_app_token=data.hardware_app_token,
                raw_material_table_id=None,
                packaging_table_id=None,
                product_table_id=None,
                is_active=data.is_active,
                remark=data.remark,
            )
        stored = await self._get_any_feishu_config_or_raise()
        if stored:
            return stored
        raise AppException(message="请先保存仓储飞书配置")

    async def _get_any_feishu_config_or_raise(self) -> WarehouseFeishuConfig | None:
        try:
            return await self.repo.get_any_feishu_config()
        except SQLAlchemyError as exc:
            raise AppException(
                status_code=500,
                message=(
                    "仓储飞书配置表不可用，请先执行数据库迁移：alembic upgrade head"
                ),
                detail=str(exc.__class__.__name__),
            ) from exc

    async def _get_active_feishu_config_or_raise(self) -> WarehouseFeishuConfig:
        try:
            config = await self.repo.get_active_feishu_config()
        except SQLAlchemyError as exc:
            raise AppException(
                status_code=500,
                message=(
                    "仓储飞书配置表不可用，请先执行数据库迁移：alembic upgrade head"
                ),
                detail=str(exc.__class__.__name__),
            ) from exc
        if not config:
            raise AppException(message="请先启用仓储飞书配置")
        return config

    async def _get_table_by_id_or_raise(self, table_pk: UUID) -> WarehouseFeishuTable:
        try:
            table = await self.repo.get_feishu_table_by_id(table_pk)
        except SQLAlchemyError as exc:
            raise AppException(
                status_code=500,
                message=(
                    "仓储飞书表目录不可用，请先执行数据库迁移：alembic upgrade head"
                ),
                detail=str(exc.__class__.__name__),
            ) from exc
        if not table:
            raise AppException(message="仓储飞书数据表不存在")
        return table

    async def _test_tenant_token(
        self,
        config: WarehouseFeishuConfig,
        steps: list[WarehouseFeishuConnectivityStep],
    ) -> str | None:
        if not config.app_id or not config.encrypted_app_secret:
            steps.append(
                WarehouseFeishuConnectivityStep(
                    name="应用凭证",
                    status="error",
                    message="App ID 或 App Secret 未配置",
                )
            )
            return None

        try:
            app_token = next(iter(self._config_app_tokens(config).values()), "")
            token = await self._build_feishu_client(
                config, app_token
            ).get_tenant_access_token()
        except Exception as exc:
            steps.append(
                WarehouseFeishuConnectivityStep(
                    name="应用凭证",
                    status="error",
                    message=f"飞书认证失败：{exc}",
                )
            )
            return None

        steps.append(
            WarehouseFeishuConnectivityStep(
                name="应用凭证",
                status="ok",
                message="tenant_access_token 获取成功",
            )
        )
        return token

    def _build_feishu_client(
        self,
        config: WarehouseFeishuConfig,
        app_token: str,
    ) -> WarehouseFeishuClient:
        return WarehouseFeishuClient(
            app_id=config.app_id,
            app_secret=decrypt_secret(config.encrypted_app_secret),
            app_token=app_token,
        )

    async def _restart_warehouse_ws(self, config: WarehouseFeishuConfig) -> None:
        try:
            from app.modules.warehouse.ws_client import restart_ws_with_config

            await restart_ws_with_config(
                app_id=config.app_id,
                app_secret=decrypt_secret(config.encrypted_app_secret),
                app_tokens=self._config_app_tokens(config),
            )
        except Exception:
            logger.warning("Failed to restart warehouse WebSocket after config save", exc_info=True)

    async def _after_feishu_config_saved(self, config: WarehouseFeishuConfig) -> None:
        try:
            await self.refresh_feishu_tables()
        except Exception:
            logger.warning("Failed to refresh Feishu tables", exc_info=True)
        await self._restart_warehouse_ws(config)

    @staticmethod
    def _config_app_tokens(config: WarehouseFeishuConfig) -> dict[str, str]:
        tokens = {
            "finished_product": config.finished_product_app_token,
            "materials_packaging": (
                config.materials_packaging_app_token or config.bitable_app_token
            ),
            "hardware": config.hardware_app_token,
        }
        return {key: value for key, value in tokens.items() if value}

    @staticmethod
    def _legacy_app_token(data: WarehouseFeishuConfigUpsert) -> str:
        return (
            data.materials_packaging_app_token
            or data.finished_product_app_token
            or data.hardware_app_token
            or ""
        )

    @staticmethod
    def _validate_optional_domain(domain: str | None) -> None:
        if domain is None:
            return
        if domain not in WAREHOUSE_FEISHU_DOMAIN_LABELS:
            raise AppException(message="仓储飞书业务域无效")

    @staticmethod
    def _mask_encrypted_secret(encrypted_secret: str) -> str:
        if not encrypted_secret:
            return ""
        try:
            return mask_secret(decrypt_secret(encrypted_secret))
        except RuntimeError:
            return "****"

    @staticmethod
    def _to_table_response(table: WarehouseFeishuTable) -> WarehouseFeishuTableResponse:
        return WarehouseFeishuTableResponse.model_validate(table)

    @staticmethod
    def _to_field_response(item: WarehouseFeishuField) -> WarehouseFeishuFieldResponse:
        return WarehouseFeishuFieldResponse(
            field_id=item.field_id,
            field_name=item.field_name,
            type=item.field_type,
            property=item.property,
        )

    @staticmethod
    def _to_record_response(
        item: WarehouseFeishuRecord,
    ) -> WarehouseFeishuRawRecordResponse:
        return WarehouseFeishuRawRecordResponse(
            record_id=item.record_id,
            fields=item.fields,
            created_time=item.feishu_created_time,
            last_modified_time=item.feishu_last_modified_time,
        )

    @staticmethod
    def _field_from_raw(item: dict[str, Any]) -> WarehouseFeishuFieldResponse:
        field_id = str(item.get("field_id") or item.get("id") or "")
        field_name = str(item.get("field_name") or item.get("name") or field_id)
        return WarehouseFeishuFieldResponse(
            field_id=field_id,
            field_name=field_name,
            type=WarehouseService._safe_int(item.get("type")),
            property=(
                item.get("property") if isinstance(item.get("property"), dict) else None
            ),
        )

    @staticmethod
    def _record_from_raw(item: dict[str, Any]) -> WarehouseFeishuRawRecordResponse:
        fields = item.get("fields") if isinstance(item.get("fields"), dict) else {}
        return WarehouseFeishuRawRecordResponse(
            record_id=str(item.get("record_id") or ""),
            fields=fields,
            created_time=WarehouseService._safe_int(item.get("created_time")),
            last_modified_time=WarehouseService._safe_int(
                item.get("last_modified_time")
            ),
        )

    @staticmethod
    def _build_search_text(value: Any) -> str:
        parts: list[str] = []

        def walk(raw: Any) -> None:
            if raw is None:
                return
            if isinstance(raw, str):
                if raw.strip():
                    parts.append(raw.strip())
                return
            if isinstance(raw, (int, float, bool)):
                parts.append(str(raw))
                return
            if isinstance(raw, list):
                for item in raw:
                    walk(item)
                return
            if isinstance(raw, dict):
                for key, item in raw.items():
                    parts.append(str(key))
                    walk(item)

        walk(value)
        return " ".join(parts)[:20000]

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            if value in (None, ""):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None
