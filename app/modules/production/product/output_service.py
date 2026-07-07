"""Product output business logic."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.product.output_models import WORKSHOP_CHOICES
from app.modules.production.product.output_repository import ProductOutputRepository
from app.modules.production.product.output_schemas import (
    ProductOutputCreate,
    ProductOutputUpdate,
    SummaryResponse,
    WorkshopSummary,
)


class ProductOutputService:
    """Product output service"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProductOutputRepository(session)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        workshop: str | None = None,
        product_id: uuid.UUID | None = None,
        product_name: str | None = None,
        batch_no: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list, int]:
        """获取列表"""
        return await self.repo.get_list(
            skip=skip,
            limit=limit,
            workshop=workshop,
            product_id=product_id,
            product_name=product_name,
            batch_no=batch_no,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_by_id(self, record_id: uuid.UUID):
        """获取详情"""
        return await self.repo.get_by_id(record_id)

    async def create(self, data: ProductOutputCreate):
        """创建记录"""
        return await self.repo.create(data.model_dump())

    async def update(self, record_id: uuid.UUID, data: ProductOutputUpdate):
        """更新记录"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.repo.get_by_id(record_id)
        return await self.repo.update(record_id, update_data)

    async def delete(self, record_id: uuid.UUID) -> bool:
        """删除记录"""
        return await self.repo.delete(record_id)

    async def batch_import(self, records_data: list[dict[str, Any]]) -> int:
        """批量导入"""
        records = await self.repo.batch_create(records_data)
        return len(records)

    async def get_summary(
        self,
        target_date: date | None = None,
        month: str | None = None,
        year: int | None = None,
        product_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> SummaryResponse:
        """获取汇总统计"""
        rows = await self.repo.get_summary(
            target_date=target_date,
            month=month,
            year=year,
            product_id=product_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Build summary for all workshops, filling missing ones with 0
        weight_map = {row["workshop"]: row["total_weight"] for row in rows}
        workshops: list[WorkshopSummary] = []
        grand_total = 0.0

        # For daily summary, we need daily/monthly/yearly per workshop
        if target_date:
            daily_rows = await self.repo.get_summary(
                target_date=target_date, product_id=product_id
            )
            month_str = target_date.strftime("%Y-%m")
            monthly_rows = await self.repo.get_summary(
                month=month_str, product_id=product_id
            )
            yearly_rows = await self.repo.get_summary(
                year=target_date.year, product_id=product_id
            )

            daily_map = {r["workshop"]: r["total_weight"] for r in daily_rows}
            monthly_map = {r["workshop"]: r["total_weight"] for r in monthly_rows}
            yearly_map = {r["workshop"]: r["total_weight"] for r in yearly_rows}

            for ws in WORKSHOP_CHOICES:
                daily = daily_map.get(ws, 0.0)
                monthly = monthly_map.get(ws, 0.0)
                yearly = yearly_map.get(ws, 0.0)
                grand_total += daily
                workshops.append(
                    WorkshopSummary(
                        workshop=ws,
                        daily_total=daily,
                        monthly_total=monthly,
                        yearly_total=yearly,
                    )
                )
        elif month:
            monthly_rows = await self.repo.get_summary(
                month=month, product_id=product_id
            )
            monthly_map = {r["workshop"]: r["total_weight"] for r in monthly_rows}
            for ws in WORKSHOP_CHOICES:
                total = monthly_map.get(ws, 0.0)
                grand_total += total
                workshops.append(WorkshopSummary(workshop=ws, monthly_total=total))
        elif year:
            yearly_rows = await self.repo.get_summary(year=year, product_id=product_id)
            yearly_map = {r["workshop"]: r["total_weight"] for r in yearly_rows}
            for ws in WORKSHOP_CHOICES:
                total = yearly_map.get(ws, 0.0)
                grand_total += total
                workshops.append(WorkshopSummary(workshop=ws, yearly_total=total))
        else:
            for ws in WORKSHOP_CHOICES:
                total = weight_map.get(ws, 0.0)
                grand_total += total
                workshops.append(WorkshopSummary(workshop=ws))

        return SummaryResponse(
            target_date=target_date,
            month=month,
            year=year,
            workshops=workshops,
            grand_total=grand_total,
        )

    async def get_batch_count(
        self,
        target_date: date | None = None,
        month: str | None = None,
        year: int | None = None,
        product_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """获取批次统计"""
        return await self.repo.get_batch_count(
            target_date=target_date,
            month=month,
            year=year,
            product_id=product_id,
            start_date=start_date,
            end_date=end_date,
        )
