"""Product output business logic."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.product.output_models import WORKSHOP_CHOICES
from app.modules.production.product.output_repository import ProductOutputRepository

if TYPE_CHECKING:
    from app.modules.production.product.output_schemas import AnnualReviewResponse
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
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Any], int]:
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
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_by_id(self, record_id: uuid.UUID) -> Any:
        """获取详情"""
        return await self.repo.get_by_id(record_id)

    async def create(self, data: ProductOutputCreate) -> Any:
        """创建记录"""
        return await self.repo.create(data.model_dump())

    async def update(self, record_id: uuid.UUID, data: ProductOutputUpdate) -> Any:
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
            daily_rows = await self.repo.get_summary(target_date=target_date, product_id=product_id)
            month_str = target_date.strftime("%Y-%m")
            monthly_rows = await self.repo.get_summary(month=month_str, product_id=product_id)
            yearly_rows = await self.repo.get_summary(year=target_date.year, product_id=product_id)

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
            monthly_rows = await self.repo.get_summary(month=month, product_id=product_id)
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

    async def get_annual_review(self, year: int) -> AnnualReviewResponse:
        """获取年度回顾数据"""
        from app.modules.production.product.output_schemas import (
            AnnualOverview,
            AnnualReviewResponse,
            MonthlyTrend,
            TopProduct,
            WorkshopRanking,
        )

        # 获取年度统计
        stats = await self.repo.get_annual_stats(year)

        # 计算同比
        weight_yoy = 0.0
        if stats["previous_weight"] > 0:
            weight_yoy = ((stats["total_weight"] - stats["previous_weight"]) / stats["previous_weight"]) * 100

        batch_yoy = 0.0
        if stats["previous_batch_count"] > 0:
            batch_yoy = ((stats["batch_count"] - stats["previous_batch_count"]) / stats["previous_batch_count"]) * 100

        overview = AnnualOverview(
            total_weight=stats["total_weight"],
            previous_year_weight=stats["previous_weight"],
            weight_yoy=round(weight_yoy, 2),
            total_batches=stats["batch_count"],
            previous_year_batches=stats["previous_batch_count"],
            batch_yoy=round(batch_yoy, 2),
            active_workshops=stats["workshop_count"],
            active_products=stats["product_count"],
        )

        # 获取月度趋势
        monthly_data = await self.repo.get_monthly_trend(year)
        monthly_trend = []
        for month in range(1, 13):
            current_weight = 0.0
            previous_weight = 0.0
            for row in monthly_data:
                if row["month"] == month:
                    if row["year"] == year:
                        current_weight = row["total_weight"]
                    elif row["year"] == year - 1:
                        previous_weight = row["total_weight"]
            monthly_trend.append(
                MonthlyTrend(
                    month=month,
                    current_year_weight=current_weight,
                    previous_year_weight=previous_weight,
                )
            )

        # 获取车间排名
        workshop_data = await self.repo.get_workshop_ranking(year)
        workshop_ranking = [
            WorkshopRanking(
                workshop=row["workshop"],
                total_weight=row["total_weight"],
                batch_count=row["batch_count"],
            )
            for row in workshop_data
        ]

        # 获取TOP产品
        top_products_data = await self.repo.get_top_products(year, limit=10)
        top_products = [
            TopProduct(
                rank=i + 1,
                product_name=row["product_name"],
                workshop=row["workshop"],
                total_weight=row["total_weight"],
                batch_count=row["batch_count"],
                avg_weight=round(row["avg_weight"], 2),
            )
            for i, row in enumerate(top_products_data)
        ]

        return AnnualReviewResponse(
            year=year,
            overview=overview,
            monthly_trend=monthly_trend,
            workshop_ranking=workshop_ranking,
            top_products=top_products,
        )
