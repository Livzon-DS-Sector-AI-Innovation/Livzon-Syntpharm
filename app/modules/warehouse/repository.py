"""Warehouse database queries live here."""

from uuid import UUID

from sqlalchemy import Float, asc, case, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.warehouse.models import (
    PackagingMaterialInventory,
    ProductInventory,
    RawMaterialInventory,
    WarehouseFeishuConfig,
    WarehouseFeishuField,
    WarehouseFeishuRecord,
    WarehouseFeishuTable,
)


class WarehouseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _json_scalar_text(json_value):
        json_type = func.jsonb_typeof(json_value)
        return case(
            (json_type.in_(("string", "number", "boolean")), json_value.astext),
            else_=None,
        )

    @classmethod
    def _feishu_field_display_text(cls, field: str):
        field_value = WarehouseFeishuRecord.fields[field]
        first_item = field_value[0]
        nested_value = field_value["value"]
        nested_value_first_item = nested_value[0]

        return func.coalesce(
            cls._json_scalar_text(field_value),
            field_value["text"].astext,
            field_value["name"].astext,
            field_value["title"].astext,
            field_value["display_name"].astext,
            field_value["number"].astext,
            field_value["amount"].astext,
            cls._json_scalar_text(nested_value),
            nested_value["text"].astext,
            nested_value["name"].astext,
            nested_value["number"].astext,
            nested_value["amount"].astext,
            cls._json_scalar_text(first_item),
            first_item["text"].astext,
            first_item["name"].astext,
            first_item["number"].astext,
            first_item["amount"].astext,
            cls._json_scalar_text(nested_value_first_item),
            nested_value_first_item["text"].astext,
            nested_value_first_item["name"].astext,
            nested_value_first_item["number"].astext,
            nested_value_first_item["amount"].astext,
            field_value.astext,
        )

    async def list_raw_materials(self) -> list[RawMaterialInventory]:
        result = await self.session.execute(
            select(RawMaterialInventory)
            .where(RawMaterialInventory.is_deleted.is_(False))
            .order_by(
                asc(RawMaterialInventory.product_line),
                asc(RawMaterialInventory.code),
                asc(RawMaterialInventory.name),
            )
        )
        return list(result.scalars().all())

    async def list_packaging_materials(self) -> list[PackagingMaterialInventory]:
        result = await self.session.execute(
            select(PackagingMaterialInventory)
            .where(PackagingMaterialInventory.is_deleted.is_(False))
            .order_by(
                asc(PackagingMaterialInventory.product_line),
                asc(PackagingMaterialInventory.code),
                asc(PackagingMaterialInventory.name),
            )
        )
        return list(result.scalars().all())

    async def list_products(self) -> list[ProductInventory]:
        result = await self.session.execute(
            select(ProductInventory)
            .where(ProductInventory.is_deleted.is_(False))
            .order_by(
                asc(ProductInventory.name),
                asc(ProductInventory.spec),
            )
        )
        return list(result.scalars().all())

    async def get_raw_material_by_import_key(
        self, import_key: str
    ) -> RawMaterialInventory | None:
        result = await self.session.execute(
            select(RawMaterialInventory).where(
                RawMaterialInventory.import_key == import_key
            )
        )
        return result.scalar_one_or_none()

    async def get_packaging_material_by_import_key(
        self, import_key: str
    ) -> PackagingMaterialInventory | None:
        result = await self.session.execute(
            select(PackagingMaterialInventory).where(
                PackagingMaterialInventory.import_key == import_key
            )
        )
        return result.scalar_one_or_none()

    async def get_product_by_import_key(
        self, import_key: str
    ) -> ProductInventory | None:
        result = await self.session.execute(
            select(ProductInventory).where(ProductInventory.import_key == import_key)
        )
        return result.scalar_one_or_none()

    async def create_raw_material(
        self, item: RawMaterialInventory
    ) -> RawMaterialInventory:
        self.session.add(item)
        await self.session.flush()
        return item

    async def create_packaging_material(
        self, item: PackagingMaterialInventory
    ) -> PackagingMaterialInventory:
        self.session.add(item)
        await self.session.flush()
        return item

    async def create_product(self, item: ProductInventory) -> ProductInventory:
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_active_feishu_config(self) -> WarehouseFeishuConfig | None:
        result = await self.session.execute(
            select(WarehouseFeishuConfig)
            .where(
                WarehouseFeishuConfig.is_deleted.is_(False),
                WarehouseFeishuConfig.is_active.is_(True),
            )
            .order_by(WarehouseFeishuConfig.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_any_feishu_config(self) -> WarehouseFeishuConfig | None:
        result = await self.session.execute(
            select(WarehouseFeishuConfig)
            .where(WarehouseFeishuConfig.is_deleted.is_(False))
            .order_by(WarehouseFeishuConfig.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_feishu_config(
        self, config: WarehouseFeishuConfig
    ) -> WarehouseFeishuConfig:
        self.session.add(config)
        await self.session.flush()
        return config

    async def list_feishu_tables(
        self,
        *,
        business_domain: str | None = None,
        keyword: str | None = None,
        enabled: bool | None = None,
    ) -> list[WarehouseFeishuTable]:
        conditions = [WarehouseFeishuTable.is_deleted.is_(False)]
        if business_domain:
            conditions.append(WarehouseFeishuTable.business_domain == business_domain)
        if enabled is not None:
            conditions.append(WarehouseFeishuTable.is_enabled.is_(enabled))
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    WarehouseFeishuTable.name.ilike(pattern),
                    WarehouseFeishuTable.table_id.ilike(pattern),
                    WarehouseFeishuTable.app_token.ilike(pattern),
                )
            )
        result = await self.session.execute(
            select(WarehouseFeishuTable)
            .where(*conditions)
            .order_by(
                asc(WarehouseFeishuTable.business_domain),
                asc(WarehouseFeishuTable.name),
                asc(WarehouseFeishuTable.table_id),
            )
        )
        return list(result.scalars().all())

    async def get_feishu_table(
        self, business_domain: str, app_token: str, table_id: str
    ) -> WarehouseFeishuTable | None:
        result = await self.session.execute(
            select(WarehouseFeishuTable).where(
                WarehouseFeishuTable.is_deleted.is_(False),
                WarehouseFeishuTable.business_domain == business_domain,
                WarehouseFeishuTable.app_token == app_token,
                WarehouseFeishuTable.table_id == table_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_feishu_table_by_id(
        self, table_pk: UUID
    ) -> WarehouseFeishuTable | None:
        result = await self.session.execute(
            select(WarehouseFeishuTable).where(
                WarehouseFeishuTable.is_deleted.is_(False),
                WarehouseFeishuTable.id == table_pk,
            )
        )
        return result.scalar_one_or_none()

    async def get_enabled_feishu_table(
        self, app_token: str, table_id: str
    ) -> WarehouseFeishuTable | None:
        result = await self.session.execute(
            select(WarehouseFeishuTable).where(
                WarehouseFeishuTable.is_deleted.is_(False),
                WarehouseFeishuTable.is_enabled.is_(True),
                WarehouseFeishuTable.app_token == app_token,
                WarehouseFeishuTable.table_id == table_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_enabled_feishu_tables(self) -> list[WarehouseFeishuTable]:
        result = await self.session.execute(
            select(WarehouseFeishuTable)
            .where(
                WarehouseFeishuTable.is_deleted.is_(False),
                WarehouseFeishuTable.is_enabled.is_(True),
            )
            .order_by(
                asc(WarehouseFeishuTable.business_domain),
                asc(WarehouseFeishuTable.name),
            )
        )
        return list(result.scalars().all())

    async def save_feishu_table(
        self, table: WarehouseFeishuTable
    ) -> WarehouseFeishuTable:
        self.session.add(table)
        await self.session.flush()
        return table

    async def get_feishu_field(
        self, business_domain: str, app_token: str, table_id: str, field_id: str
    ) -> WarehouseFeishuField | None:
        result = await self.session.execute(
            select(WarehouseFeishuField).where(
                WarehouseFeishuField.is_deleted.is_(False),
                WarehouseFeishuField.business_domain == business_domain,
                WarehouseFeishuField.app_token == app_token,
                WarehouseFeishuField.table_id == table_id,
                WarehouseFeishuField.field_id == field_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_feishu_fields(
        self, business_domain: str, app_token: str, table_id: str
    ) -> list[WarehouseFeishuField]:
        result = await self.session.execute(
            select(WarehouseFeishuField)
            .where(
                WarehouseFeishuField.is_deleted.is_(False),
                WarehouseFeishuField.business_domain == business_domain,
                WarehouseFeishuField.app_token == app_token,
                WarehouseFeishuField.table_id == table_id,
            )
            .order_by(
                asc(WarehouseFeishuField.created_at),
                asc(WarehouseFeishuField.field_name),
            )
        )
        return list(result.scalars().all())

    async def save_feishu_field(
        self, field: WarehouseFeishuField
    ) -> WarehouseFeishuField:
        self.session.add(field)
        await self.session.flush()
        return field

    async def get_feishu_record(
        self, business_domain: str, app_token: str, table_id: str, record_id: str
    ) -> WarehouseFeishuRecord | None:
        result = await self.session.execute(
            select(WarehouseFeishuRecord).where(
                WarehouseFeishuRecord.business_domain == business_domain,
                WarehouseFeishuRecord.app_token == app_token,
                WarehouseFeishuRecord.table_id == table_id,
                WarehouseFeishuRecord.record_id == record_id,
            )
        )
        return result.scalar_one_or_none()

    async def save_feishu_record(
        self, record: WarehouseFeishuRecord
    ) -> WarehouseFeishuRecord:
        self.session.add(record)
        await self.session.flush()
        return record

    async def mark_missing_feishu_records_deleted(
        self,
        *,
        business_domain: str,
        app_token: str,
        table_id: str,
        active_record_ids: set[str],
    ) -> None:
        stmt = (
            update(WarehouseFeishuRecord)
            .where(
                WarehouseFeishuRecord.business_domain == business_domain,
                WarehouseFeishuRecord.app_token == app_token,
                WarehouseFeishuRecord.table_id == table_id,
                WarehouseFeishuRecord.is_deleted.is_(False),
                WarehouseFeishuRecord.record_id.not_in(active_record_ids),
            )
            .values(is_deleted=True)
        )
        await self.session.execute(stmt)

    async def list_feishu_records(
        self,
        *,
        business_domain: str,
        app_token: str,
        table_id: str,
        keyword: str | None,
        field: str | None,
        field_operator: str | None,
        field_value: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[WarehouseFeishuRecord], int]:
        conditions = [
            WarehouseFeishuRecord.is_deleted.is_(False),
            WarehouseFeishuRecord.business_domain == business_domain,
            WarehouseFeishuRecord.app_token == app_token,
            WarehouseFeishuRecord.table_id == table_id,
        ]
        if keyword:
            pattern = f"%{keyword.strip()}%"
            if field:
                conditions.append(self._feishu_field_display_text(field).ilike(pattern))
            else:
                conditions.append(WarehouseFeishuRecord.search_text.ilike(pattern))
        if field and field_operator and field_value is not None:
            field_text = self._feishu_field_display_text(field)
            normalized_value = field_value.strip()

            if field_operator == "contains":
                conditions.append(field_text.ilike(f"%{normalized_value}%"))
            elif field_operator == "eq":
                conditions.append(field_text == normalized_value)
            elif field_operator == "ne":
                conditions.append(field_text != normalized_value)
            elif field_operator in {"gt", "gte", "lt", "lte"}:
                numeric_pattern = r"^\s*-?\d+(\.\d+)?\s*$"
                field_number = case(
                    (field_text.op("~")(numeric_pattern), cast(field_text, Float)),
                    else_=None,
                )
                compare_value = float(normalized_value)
                if field_operator == "gt":
                    conditions.append(field_number > compare_value)
                elif field_operator == "gte":
                    conditions.append(field_number >= compare_value)
                elif field_operator == "lt":
                    conditions.append(field_number < compare_value)
                else:
                    conditions.append(field_number <= compare_value)

        total_result = await self.session.execute(
            select(func.count()).select_from(WarehouseFeishuRecord).where(*conditions)
        )
        total = int(total_result.scalar_one() or 0)

        result = await self.session.execute(
            select(WarehouseFeishuRecord)
            .where(*conditions)
            .order_by(
                WarehouseFeishuRecord.feishu_last_modified_time.desc().nullslast(),
                WarehouseFeishuRecord.updated_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
