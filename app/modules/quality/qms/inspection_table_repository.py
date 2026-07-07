"""原料检验数据表 Repository"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.quality.qms.inspection_table_models import (
    InspectionTable,
    InspectionTableRow,
)


class InspectionTableRepository:
    """检验数据表 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> InspectionTable:
        """创建数据表"""
        table = InspectionTable(**data)
        self.session.add(table)
        await self.session.flush()
        await self.session.refresh(table)
        return table

    async def get_by_id(self, table_id: UUID) -> Optional[InspectionTable]:
        """获取数据表详情"""
        result = await self.session.execute(
            select(InspectionTable)
            .options(selectinload(InspectionTable.rows))
            .where(InspectionTable.id == table_id)
        )
        return result.scalar_one_or_none()

    async def update(self, table_id: UUID, data: dict) -> Optional[InspectionTable]:
        """更新数据表"""
        table = await self.get_by_id(table_id)
        if not table:
            return None

        for key, value in data.items():
            if hasattr(table, key):
                setattr(table, key, value)

        await self.session.flush()
        await self.session.refresh(table)
        return table

    async def delete(self, table_id: UUID) -> bool:
        """删除数据表"""
        table = await self.get_by_id(table_id)
        if not table:
            return False

        await self.session.delete(table)
        return True

    async def list_all(
        self,
        is_active: Optional[bool] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[InspectionTable], int]:
        """获取数据表列表"""
        query = select(InspectionTable)

        conditions = []
        if is_active is not None:
            conditions.append(InspectionTable.is_active == is_active)
        if keyword:
            conditions.append(
                InspectionTable.table_name.ilike(f"%{keyword}%")
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # 分页
        query = query.order_by(InspectionTable.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        tables = list(result.scalars().all())

        return tables, total


class InspectionTableRowRepository:
    """检验数据表行 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, table_id: UUID, data: dict) -> InspectionTableRow:
        """创建数据行"""
        # 获取最大排序号
        result = await self.session.execute(
            select(func.max(InspectionTableRow.sort_order))
            .where(InspectionTableRow.table_id == table_id)
        )
        max_order = result.scalar() or 0

        row = InspectionTableRow(
            table_id=table_id,
            sort_order=max_order + 1,
            **data
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def batch_create(self, table_id: UUID, rows: list[dict]) -> list[InspectionTableRow]:
        """批量创建数据行"""
        # 获取最大排序号
        result = await self.session.execute(
            select(func.max(InspectionTableRow.sort_order))
            .where(InspectionTableRow.table_id == table_id)
        )
        max_order = result.scalar() or 0

        created_rows = []
        for i, row_data in enumerate(rows):
            row = InspectionTableRow(
                table_id=table_id,
                sort_order=max_order + i + 1,
                row_data=row_data
            )
            self.session.add(row)
            created_rows.append(row)

        await self.session.flush()
        for row in created_rows:
            await self.session.refresh(row)
        return created_rows

    async def update(self, row_id: int, data: dict) -> Optional[InspectionTableRow]:
        """更新数据行"""
        result = await self.session.execute(
            select(InspectionTableRow).where(InspectionTableRow.id == row_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None

        for key, value in data.items():
            if hasattr(row, key):
                setattr(row, key, value)

        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def delete(self, row_id: int) -> bool:
        """删除数据行"""
        result = await self.session.execute(
            select(InspectionTableRow).where(InspectionTableRow.id == row_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False

        await self.session.delete(row)
        return True

    async def get_by_table_id(self, table_id: UUID) -> list[InspectionTableRow]:
        """获取表的所有数据行"""
        result = await self.session.execute(
            select(InspectionTableRow)
            .where(InspectionTableRow.table_id == table_id)
            .order_by(InspectionTableRow.sort_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, row_id: int) -> Optional[InspectionTableRow]:
        """根据ID获取数据行"""
        result = await self.session.execute(
            select(InspectionTableRow).where(InspectionTableRow.id == row_id)
        )
        return result.scalar_one_or_none()

    async def delete_by_table_id(self, table_id: UUID) -> bool:
        """删除表的所有数据行"""
        from sqlalchemy import delete
        await self.session.execute(
            delete(InspectionTableRow).where(InspectionTableRow.table_id == table_id)
        )
        return True
