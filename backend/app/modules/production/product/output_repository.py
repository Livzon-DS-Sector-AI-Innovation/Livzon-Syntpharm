"""Product output database queries."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.product.output_models import ProductOutput


class ProductOutputRepository:
    """Product output repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

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
    ) -> tuple[list[ProductOutput], int]:
        """获取产量记录列表"""
        query = select(ProductOutput).where(
            ProductOutput.is_deleted == False  # noqa: E712
        )
        count_query = select(func.count(ProductOutput.id)).where(
            ProductOutput.is_deleted == False  # noqa: E712
        )

        if workshop:
            query = query.where(ProductOutput.workshop == workshop)
            count_query = count_query.where(ProductOutput.workshop == workshop)
        if product_id:
            query = query.where(ProductOutput.product_id == product_id)
            count_query = count_query.where(ProductOutput.product_id == product_id)
        if product_name:
            query = query.where(ProductOutput.product_name.contains(product_name))
            count_query = count_query.where(ProductOutput.product_name.contains(product_name))
        if batch_no:
            query = query.where(ProductOutput.batch_no.contains(batch_no))
            count_query = count_query.where(ProductOutput.batch_no.contains(batch_no))
        if start_date:
            query = query.where(ProductOutput.production_date >= start_date)
            count_query = count_query.where(ProductOutput.production_date >= start_date)
        if end_date:
            query = query.where(ProductOutput.production_date <= end_date)
            count_query = count_query.where(ProductOutput.production_date <= end_date)

        total = await self.session.scalar(count_query) or 0
        sort_column = getattr(ProductOutput, sort_by, None) if sort_by else None
        if sort_column is not None:
            order_expr = sort_column.desc() if sort_order == "desc" else sort_column.asc()
            query = query.offset(skip).limit(limit).order_by(order_expr, ProductOutput.created_at.desc())
        else:
            query = (
                query.offset(skip)
                .limit(limit)
                .order_by(
                    ProductOutput.production_date.desc(),
                    ProductOutput.created_at.desc(),
                )
            )
        result = await self.session.execute(query)
        records = list(result.scalars().all())
        return records, total

    async def get_by_id(self, record_id: uuid.UUID) -> ProductOutput | None:
        """获取单条记录"""
        query = select(ProductOutput).where(
            ProductOutput.id == record_id,
            ProductOutput.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> ProductOutput:
        """创建记录"""
        record = ProductOutput(**data)
        self.session.add(record)
        await self.session.flush()
        stmt = select(ProductOutput).where(ProductOutput.id == record.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, record_id: uuid.UUID, data: dict[str, Any]) -> ProductOutput | None:
        """更新记录"""
        query = (
            update(ProductOutput)
            .where(
                ProductOutput.id == record_id,
                ProductOutput.is_deleted == False,  # noqa: E712
            )
            .values(**data)
            .returning(ProductOutput)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete(self, record_id: uuid.UUID) -> bool:
        """软删除记录"""
        query = (
            update(ProductOutput)
            .where(
                ProductOutput.id == record_id,
                ProductOutput.is_deleted == False,  # noqa: E712
            )
            .values(is_deleted=True)
        )
        result = await self.session.execute(query)
        return result.rowcount > 0  # type: ignore[attr-defined,no-any-return]  # type: ignore[attr-defined,no-any-return]

    async def batch_create(self, records_data: list[dict[str, Any]]) -> list[ProductOutput]:
        """批量创建"""
        records = [ProductOutput(**data) for data in records_data]
        self.session.add_all(records)
        await self.session.flush()
        return records

    async def get_summary(
        self,
        target_date: date | None = None,
        month: str | None = None,
        year: int | None = None,
        workshop: str | None = None,
        product_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """获取汇总统计 - 按结束日期计算产量"""
        # 使用 end_date，如果 end_date 为 null 则用 production_date
        output_date = case(
            (ProductOutput.end_date.isnot(None), ProductOutput.end_date),
            else_=ProductOutput.production_date,
        )

        base_query = (
            select(
                ProductOutput.workshop,
                func.coalesce(func.sum(ProductOutput.weight), 0).label("total_weight"),
            )
            .where(ProductOutput.is_deleted == False)  # noqa: E712
            .group_by(ProductOutput.workshop)
        )

        if target_date:
            base_query = base_query.where(output_date == target_date)
        if month:
            base_query = base_query.where(func.to_char(output_date, "YYYY-MM") == month)
        if year:
            base_query = base_query.where(func.extract("year", output_date) == year)
        if workshop:
            base_query = base_query.where(ProductOutput.workshop == workshop)
        if product_id:
            base_query = base_query.where(ProductOutput.product_id == product_id)
        if start_date:
            base_query = base_query.where(output_date >= start_date)
        if end_date:
            base_query = base_query.where(output_date <= end_date)

        result = await self.session.execute(base_query)
        rows = result.all()
        return [
            {
                "workshop": row.workshop,
                "total_weight": float(row.total_weight),
            }
            for row in rows
        ]

    async def get_batch_count(
        self,
        target_date: date | None = None,
        month: str | None = None,
        year: int | None = None,
        product_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """获取批次统计 - 按产品分组统计批次数"""
        output_date = case(
            (ProductOutput.end_date.isnot(None), ProductOutput.end_date),
            else_=ProductOutput.production_date,
        )

        base_query = (
            select(
                ProductOutput.product_id,
                func.count(func.distinct(ProductOutput.batch_no)).label("batch_count"),
            )
            .where(ProductOutput.is_deleted == False)  # noqa: E712
            .group_by(ProductOutput.product_id)
        )

        if target_date:
            base_query = base_query.where(output_date == target_date)
        if month:
            base_query = base_query.where(func.to_char(output_date, "YYYY-MM") == month)
        if year:
            base_query = base_query.where(func.extract("year", output_date) == year)
        if product_id:
            base_query = base_query.where(ProductOutput.product_id == product_id)
        if start_date:
            base_query = base_query.where(output_date >= start_date)
        if end_date:
            base_query = base_query.where(output_date <= end_date)

        result = await self.session.execute(base_query)
        rows = result.all()
        return [
            {
                "product_id": row.product_id,
                "batch_count": int(row.batch_count),
            }
            for row in rows
        ]

    async def get_monthly_trend(self, year: int) -> list[dict[str, Any]]:
        """获取月度趋势 - 当年和去年对比"""
        output_date = case(
            (ProductOutput.end_date.isnot(None), ProductOutput.end_date),
            else_=ProductOutput.production_date,
        )

        query = (
            select(
                func.extract("year", output_date).label("year"),
                func.extract("month", output_date).label("month"),
                func.coalesce(func.sum(ProductOutput.weight), 0).label("total_weight"),
            )
            .where(
                ProductOutput.is_deleted == False,  # noqa: E712
                func.extract("year", output_date).in_([year, year - 1]),
            )
            .group_by("year", "month")
            .order_by("year", "month")
        )

        result = await self.session.execute(query)
        rows = result.all()
        return [
            {
                "year": int(row.year),
                "month": int(row.month),
                "total_weight": float(row.total_weight),
            }
            for row in rows
        ]

    async def get_workshop_ranking(self, year: int) -> list[dict[str, Any]]:
        """获取车间年度排名"""
        output_date = case(
            (ProductOutput.end_date.isnot(None), ProductOutput.end_date),
            else_=ProductOutput.production_date,
        )

        query = (
            select(
                ProductOutput.workshop,
                func.coalesce(func.sum(ProductOutput.weight), 0).label("total_weight"),
                func.count(func.distinct(ProductOutput.batch_no)).label("batch_count"),
            )
            .where(
                ProductOutput.is_deleted == False,  # noqa: E712
                func.extract("year", output_date) == year,
            )
            .group_by(ProductOutput.workshop)
            .order_by(func.sum(ProductOutput.weight).desc())
        )

        result = await self.session.execute(query)
        rows = result.all()
        return [
            {
                "workshop": row.workshop,
                "total_weight": float(row.total_weight),
                "batch_count": int(row.batch_count),
            }
            for row in rows
        ]

    async def get_top_products(self, year: int, limit: int = 10) -> list[dict[str, Any]]:
        """获取年度TOP产品"""
        output_date = case(
            (ProductOutput.end_date.isnot(None), ProductOutput.end_date),
            else_=ProductOutput.production_date,
        )

        query = (
            select(
                ProductOutput.product_name,
                ProductOutput.workshop,
                func.coalesce(func.sum(ProductOutput.weight), 0).label("total_weight"),
                func.count(func.distinct(ProductOutput.batch_no)).label("batch_count"),
            )
            .where(
                ProductOutput.is_deleted == False,  # noqa: E712
                func.extract("year", output_date) == year,
            )
            .group_by(ProductOutput.product_name, ProductOutput.workshop)
            .order_by(func.sum(ProductOutput.weight).desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()
        return [
            {
                "product_name": row.product_name,
                "workshop": row.workshop,
                "total_weight": float(row.total_weight),
                "batch_count": int(row.batch_count),
                "avg_weight": float(row.total_weight) / row.batch_count if row.batch_count > 0 else 0,
            }
            for row in rows
        ]

    async def get_annual_stats(self, year: int) -> dict[str, Any]:
        """获取年度统计数据"""
        output_date = case(
            (ProductOutput.end_date.isnot(None), ProductOutput.end_date),
            else_=ProductOutput.production_date,
        )

        # 当年统计
        current_query = (
            select(
                func.coalesce(func.sum(ProductOutput.weight), 0).label("total_weight"),
                func.count(func.distinct(ProductOutput.batch_no)).label("batch_count"),
                func.count(func.distinct(ProductOutput.workshop)).label("workshop_count"),
                func.count(func.distinct(ProductOutput.product_name)).label("product_count"),
            )
            .where(
                ProductOutput.is_deleted == False,  # noqa: E712
                func.extract("year", output_date) == year,
            )
        )
        current_result = await self.session.execute(current_query)
        current_row = current_result.one()

        # 去年统计
        previous_query = (
            select(
                func.coalesce(func.sum(ProductOutput.weight), 0).label("total_weight"),
                func.count(func.distinct(ProductOutput.batch_no)).label("batch_count"),
            )
            .where(
                ProductOutput.is_deleted == False,  # noqa: E712
                func.extract("year", output_date) == year - 1,
            )
        )
        previous_result = await self.session.execute(previous_query)
        previous_row = previous_result.one()

        return {
            "total_weight": float(current_row.total_weight),
            "batch_count": int(current_row.batch_count),
            "workshop_count": int(current_row.workshop_count),
            "product_count": int(current_row.product_count),
            "previous_weight": float(previous_row.total_weight),
            "previous_batch_count": int(previous_row.batch_count),
        }
