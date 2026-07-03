"""Administration business workflows live here."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.administration.models import (
    ITServiceTicket,
    Vehicle,
    VehicleRequest,
)
from app.modules.administration.repository import (
    GiftInventoryRepository,
    GiftRequisitionRepository,
    ITServiceTicketRepository,
    RegulationRepository,
    VehicleRepository,
    VehicleRequestRepository,
)
from app.modules.administration.schemas import (
    GiftInventoryCreate,
    GiftInventoryUpdate,
    GiftRequisitionCreate,
    GiftRequisitionUpdate,
    ITServiceTicketCreate,
    ITServiceTicketUpdate,
    RegulationCreate,
    RegulationUpdate,
    VehicleCreate,
    VehicleRequestCreate,
    VehicleRequestUpdate,
    VehicleUpdate,
)

logger = logging.getLogger(__name__)
_settings = get_settings()


class RegulationService:
    def __init__(self, session: AsyncSession):
        self.repo = RegulationRepository(session)

    async def list_regulations(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        return await self.repo.list(keyword=keyword, page=page, page_size=page_size)

    async def get_regulation(self, regulation_id: UUID):
        regulation = await self.repo.get_by_id(regulation_id)
        if not regulation:
            raise ValueError("规章制度不存在")
        return regulation

    async def create_regulation(self, data: RegulationCreate):
        return await self.repo.create(data)

    async def update_regulation(self, regulation_id: UUID, data: RegulationUpdate):
        regulation = await self.get_regulation(regulation_id)
        return await self.repo.update(regulation, data)

    async def delete_regulation(self, regulation_id: UUID):
        regulation = await self.get_regulation(regulation_id)
        await self.repo.delete(regulation)


class VehicleService:
    def __init__(self, session: AsyncSession):
        self.repo = VehicleRepository(session)

    async def list_vehicles(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        return await self.repo.list(
            keyword=keyword, status=status, page=page, page_size=page_size
        )

    async def get_vehicle(self, vehicle_id: UUID) -> Vehicle:
        vehicle = await self.repo.get_by_id(vehicle_id)
        if not vehicle:
            raise ValueError("车辆不存在")
        return vehicle

    async def create_vehicle(self, data: VehicleCreate) -> Vehicle:
        return await self.repo.create(data)

    async def update_vehicle(self, vehicle_id: UUID, data: VehicleUpdate) -> Vehicle:
        vehicle = await self.get_vehicle(vehicle_id)
        return await self.repo.update(vehicle, data)

    async def delete_vehicle(self, vehicle_id: UUID) -> None:
        vehicle = await self.get_vehicle(vehicle_id)
        await self.repo.delete(vehicle)

    async def batch_import(self, file_bytes: bytes, file_type: str) -> dict:
        from io import BytesIO

        import pandas as pd
        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        df = pd.read_excel(BytesIO(file_bytes), header=None)

        # Locate the header row: first row containing "车牌号"
        header_row_idx = None
        for idx, row in df.iterrows():
            for cell in row:
                if isinstance(cell, str) and "车牌号" in cell:
                    header_row_idx = idx
                    break
            if header_row_idx is not None:
                break

        if header_row_idx is None:
            return {
                "created": 0,
                "failed": 0,
                "errors": ["未找到有效的表头行（需包含“车牌号”列）"],
            }

        # Re-read with the correct header row
        df = pd.read_excel(BytesIO(file_bytes), header=header_row_idx)

        # Normalise column names: strip * prefix, whitespace
        df.columns = [
            str(col).replace("*", "").strip()
            if isinstance(col, str)
            else str(col).strip()
            for col in df.columns
        ]

        # Query ALL existing vehicles (including soft-deleted) because unique constraint covers them
        existing_result = await self.repo.session.execute(select(Vehicle))
        existing_by_plate: dict[str, Vehicle] = {
            v.plate_number: v for v in existing_result.scalars().all()
        }

        created = 0
        restored = 0
        errors: list[str] = []
        seen_in_excel: set[str] = set()
        rows_to_insert: list[dict] = []

        for idx, row in df.iterrows():
            plate = str(row.get("车牌号", "")).strip()
            if not plate:
                continue

            excel_line = idx + header_row_idx + 2

            # Check for duplicates within the same Excel file
            if plate in seen_in_excel:
                errors.append(f"第{excel_line}行: 车牌号 {plate} 在 Excel 中重复")
                continue
            seen_in_excel.add(plate)

            existing = existing_by_plate.get(plate)
            if existing:
                if existing.is_deleted:
                    # Restore soft-deleted record with updated fields
                    existing.is_deleted = False
                    existing.brand = str(row.get("品牌", "")).strip() or existing.brand
                    existing.model = str(row.get("型号", "")).strip() or existing.model
                    existing.color = str(row.get("颜色", "")).strip() or existing.color
                    existing.status = (
                        str(row.get("状态", "可用")).strip() or existing.status
                    )
                    existing.owner_department = (
                        str(row.get("所属部门", "")).strip()
                        or existing.owner_department
                    )
                    existing.remarks = (
                        str(row.get("备注", "")).strip() or existing.remarks
                    )
                    mileage_val = row.get("行驶里程")
                    if pd.notna(mileage_val):
                        existing.mileage = int(mileage_val)
                    restored += 1
                else:
                    errors.append(f"第{excel_line}行: 车牌号 {plate} 已存在于数据库")
                continue

            data = VehicleCreate(
                plate_number=plate,
                brand=str(row.get("品牌", "")).strip() or None,
                model=str(row.get("型号", "")).strip() or None,
                color=str(row.get("颜色", "")).strip() or None,
                mileage=int(row.get("行驶里程", 0))
                if pd.notna(row.get("行驶里程"))
                else None,
                status=str(row.get("状态", "可用")).strip() or "可用",
                owner_department=str(row.get("所属部门", "")).strip() or None,
                remarks=str(row.get("备注", "")).strip() or None,
            )
            rows_to_insert.append(data.model_dump(exclude_unset=True))

        if rows_to_insert:
            stmt = pg_insert(Vehicle).values(rows_to_insert)
            stmt = stmt.on_conflict_do_nothing(index_elements=["plate_number"])
            result = await self.repo.session.execute(stmt)
            created = (
                result.rowcount if result.rowcount is not None else len(rows_to_insert)
            )

        return {
            "created": created,
            "restored": restored,
            "failed": len(errors),
            "errors": errors,
        }


class VehicleRequestService:
    def __init__(self, session: AsyncSession):
        self.repo = VehicleRequestRepository(session)

    async def list_requests(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        return await self.repo.list(
            keyword=keyword, status=status, page=page, page_size=page_size
        )

    async def get_request(self, request_id: UUID) -> VehicleRequest:
        request = await self.repo.get_by_id(request_id)
        if not request:
            raise ValueError("用车申请不存在")
        return request

    async def create_request(self, data: VehicleRequestCreate) -> VehicleRequest:
        return await self.repo.create(data)

    async def update_request(
        self, request_id: UUID, data: VehicleRequestUpdate
    ) -> VehicleRequest:
        request = await self.get_request(request_id)
        return await self.repo.update(request, data)

    async def delete_request(self, request_id: UUID) -> None:
        request = await self.get_request(request_id)
        await self.repo.delete(request)

    async def sync_from_feishu(self) -> dict:
        """从飞书多维表格同步用车申请数据到本地数据库.

        车辆多维表归 wz 机器人(FEISHU_VEHICLE_APP_*)所有，需要在 .env 中配置
        FEISHU_BITABLE_VEHICLE_REQUEST_APP_TOKEN 和 FEISHU_BITABLE_VEHICLE_REQUEST_TABLE_ID.
        """
        vehicle_app_token = (
            _settings.feishu.vehicle.bitable_request_app_token
            or _settings.feishu.hr_bitable.app_token
        )
        if (
            not vehicle_app_token
            or not _settings.feishu.vehicle.bitable_request_table_id
        ):
            raise RuntimeError(
                "飞书多维表格未配置，请在 .env 中设置 "
                "FEISHU_BITABLE_VEHICLE_REQUEST_APP_TOKEN 和 "
                "FEISHU_BITABLE_VEHICLE_REQUEST_TABLE_ID"
            )

        try:
            from app.platform.integrations.feishu.auth import FeishuAuth
            from app.platform.integrations.feishu.bitable import BitableClient

            bitable = BitableClient(
                auth=FeishuAuth.vehicle(),
                app_token=vehicle_app_token,
            )
            records = await bitable.search_records(
                _settings.feishu.vehicle.bitable_request_table_id,
                page_size=500,
            )

            created = 0
            updated = 0
            failed = 0

            for record in records:
                fields = record.get("fields", {})
                try:
                    # 字段映射（根据实际飞书表格字段名调整）
                    data = VehicleRequestCreate(
                        applicant_name=fields.get("申请人", ""),
                        applicant_department=fields.get("部门", ""),
                        applicant_phone=fields.get("联系电话", ""),
                        purpose=fields.get("用车事由", ""),
                        destination=fields.get("目的地", ""),
                        start_time=datetime.now(),  # 根据实际字段解析
                        end_time=datetime.now(),  # 根据实际字段解析
                        passengers=int(fields.get("乘车人数", 1)),
                        remarks=fields.get("备注", ""),
                    )
                    await self.repo.create(data)
                    created += 1
                except Exception as e:
                    logger.error("同步飞书记录失败: %s", e)
                    failed += 1

            return {
                "created": created,
                "updated": updated,
                "failed": failed,
                "total": len(records),
            }
        except Exception as e:
            logger.error("从飞书同步用车申请失败: %s", e)
            raise


class ITServiceTicketService:
    def __init__(self, session: AsyncSession):
        self.repo = ITServiceTicketRepository(session)

    async def list_tickets(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        ticket_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        return await self.repo.list(
            keyword=keyword,
            status=status,
            ticket_type=ticket_type,
            page=page,
            page_size=page_size,
        )

    async def get_ticket(self, ticket_id: UUID) -> ITServiceTicket:
        ticket = await self.repo.get_by_id(ticket_id)
        if not ticket:
            raise ValueError("IT工单不存在")
        return ticket

    async def create_ticket(self, data: ITServiceTicketCreate) -> ITServiceTicket:
        return await self.repo.create(data)

    async def update_ticket(
        self, ticket_id: UUID, data: ITServiceTicketUpdate
    ) -> ITServiceTicket:
        ticket = await self.get_ticket(ticket_id)
        return await self.repo.update(ticket, data)

    async def delete_ticket(self, ticket_id: UUID) -> None:
        ticket = await self.get_ticket(ticket_id)
        await self.repo.delete(ticket)


class GiftInventoryService:
    def __init__(self, session: AsyncSession):
        # session is ignored; repository uses its own asyncpg connection to gift_inventory DB
        self.repo = GiftInventoryRepository()

    async def list_inventories(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        return await self.repo.list(
            keyword=keyword, status=status, page=page, page_size=page_size
        )

    async def get_inventory(self, inventory_id: UUID) -> dict:
        inventory = await self.repo.get_by_id(inventory_id)
        if not inventory:
            raise ValueError("库存记录不存在")
        return inventory

    async def create_inventory(self, data: GiftInventoryCreate) -> dict:
        return await self.repo.create(data)

    async def update_inventory(
        self, inventory_id: UUID, data: GiftInventoryUpdate
    ) -> dict:
        return await self.repo.update(inventory_id, data)

    async def delete_inventory(self, inventory_id: UUID) -> None:
        await self.repo.delete(inventory_id)


class GiftRequisitionService:
    def __init__(self, session: AsyncSession):
        self.repo = GiftRequisitionRepository()

    async def list_requisitions(
        self,
        *,
        department: str | None = None,
        item_name: str | None = None,
        recipient: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        return await self.repo.list(
            department=department,
            item_name=item_name,
            recipient=recipient,
            page=page,
            page_size=page_size,
        )

    async def get_requisition(self, req_id: UUID) -> dict:
        req = await self.repo.get_by_id(req_id)
        if not req:
            raise ValueError("领用记录不存在")
        return req

    async def create_requisition(self, data: GiftRequisitionCreate) -> dict:
        return await self.repo.create(data)

    async def update_requisition(
        self, req_id: UUID, data: GiftRequisitionUpdate
    ) -> dict:
        return await self.repo.update(req_id, data)

    async def delete_requisition(self, req_id: UUID) -> None:
        await self.repo.delete(req_id)
