"""原料检验数据表 Service"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.inspection_table_repository import (
    InspectionTableRepository,
    InspectionTableRowRepository,
)


class InspectionTableService:
    """检验数据表服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.table_repo = InspectionTableRepository(session)
        self.row_repo = InspectionTableRowRepository(session)

    async def create_table(
        self, table_name: str, table_description: str, columns_config: list
    ) -> dict:
        """创建数据表"""
        # 检查表名是否已存在
        existing = await self.table_repo.list_all(keyword=table_name)
        if existing[0]:
            for t in existing[0]:
                if t.table_name == table_name:
                    raise ValueError(f"数据表 '{table_name}' 已存在")

        table = await self.table_repo.create(
            {
                "table_name": table_name,
                "table_description": table_description,
                "columns_config": columns_config,
            }
        )

        return self._format_table(table)

    async def get_table(self, table_id: UUID) -> dict | None:
        """获取数据表详情"""
        table = await self.table_repo.get_by_id(table_id)
        if not table:
            return None

        result = self._format_table(table)

        # 添加数据行
        rows = await self.row_repo.get_by_table_id(table_id)
        result["rows"] = [self._format_row(row) for row in rows]

        return result

    async def get_table_simple(self, table_id: UUID) -> dict | None:
        """获取数据表基本信息（不包含数据行）"""
        table = await self.table_repo.get_by_id(table_id)
        if not table:
            return None
        return self._format_table(table)

    async def get_row(self, row_id: int) -> dict | None:
        """获取单条数据行"""
        row = await self.row_repo.get_by_id(row_id)
        if not row:
            return None
        return self._format_row(row)

    async def get_rows_by_table(self, table_id: UUID) -> list[dict]:
        """获取表的所有数据行"""
        rows = await self.row_repo.get_by_table_id(table_id)
        return [self._format_row(row) for row in rows]

    async def update_table(self, table_id: UUID, data: dict) -> dict | None:
        """更新数据表"""
        table = await self.table_repo.update(table_id, data)
        if not table:
            return None

        return self._format_table(table)

    async def delete_table(self, table_id: UUID) -> bool:
        """删除数据表"""
        return await self.table_repo.delete(table_id)

    async def list_tables(
        self,
        is_active: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取数据表列表"""
        tables, total = await self.table_repo.list_all(
            is_active=is_active,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

        result = []
        for table in tables:
            item = self._format_table(table)
            # 统计行数
            rows = await self.row_repo.get_by_table_id(table.id)
            item["row_count"] = len(rows)
            result.append(item)

        return result, total

    async def add_row(self, table_id: UUID, row_data: dict) -> dict:
        """添加数据行"""
        table = await self.table_repo.get_by_id(table_id)
        if not table:
            raise ValueError("数据表不存在")

        row = await self.row_repo.create(table_id, {"row_data": row_data})
        return self._format_row(row)

    async def update_row(self, row_id: int, row_data: dict) -> dict | None:
        """更新数据行"""
        row = await self.row_repo.update(row_id, {"row_data": row_data})
        if not row:
            return None
        return self._format_row(row)

    async def delete_row(self, row_id: int) -> bool:
        """删除数据行"""
        return await self.row_repo.delete(row_id)

    async def batch_save_rows(self, table_id: UUID, rows: list[dict]) -> list[dict]:
        """批量保存数据行（先清空再插入）"""
        # 先删除现有行
        await self.row_repo.delete_by_table_id(table_id)

        # 批量插入新行
        if rows:
            created_rows = await self.row_repo.batch_create(table_id, rows)
            return [self._format_row(row) for row in created_rows]
        return []

    def _format_table(self, table) -> dict:
        """格式化数据表"""
        return {
            "id": str(table.id),
            "table_name": table.table_name,
            "table_description": table.table_description,
            "columns_config": table.columns_config or [],
            "is_active": table.is_active,
            "template_path": table.template_path,
            "template_name": table.template_name,
            "created_at": table.created_at.isoformat() if table.created_at else None,
            "updated_at": table.updated_at.isoformat() if table.updated_at else None,
        }

    def _format_row(self, row) -> dict:
        """格式化数据行"""
        return {
            "id": row.id,
            "table_id": str(row.table_id),
            "row_data": row.row_data or {},
            "sort_order": row.sort_order,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
