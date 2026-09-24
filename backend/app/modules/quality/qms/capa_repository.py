"""CAPA Repository"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.capa_models import Capa


class CapaRepository:
    """CAPA Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict[str, Any]) -> Capa:
        """创建 CAPA"""
        capa = Capa(**data)
        self.session.add(capa)
        await self.session.flush()
        await self.session.refresh(capa)
        return capa

    async def get_by_id(self, capa_id: UUID) -> Capa | None:
        """获取 CAPA 详情"""
        result = await self.session.execute(
            select(Capa).where(Capa.id == capa_id, Capa.is_deleted == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, capa_code: str) -> Capa | None:
        """通过编号获取 CAPA"""
        result = await self.session.execute(
            select(Capa).where(Capa.capa_code == capa_code, Capa.is_deleted == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def update(self, capa_id: UUID, data: dict[str, Any]) -> Capa | None:
        """更新 CAPA"""
        capa = await self.get_by_id(capa_id)
        if not capa:
            return None

        for key, value in data.items():
            if hasattr(capa, key):
                setattr(capa, key, value)

        await self.session.flush()
        await self.session.refresh(capa)
        return capa

    async def delete(self, capa_id: UUID) -> bool:
        """删除 CAPA（软删除）"""
        capa = await self.get_by_id(capa_id)
        if not capa:
            return False
        capa.is_deleted = True
        await self.session.flush()
        return True

    async def list_with_filter(
        self,
        capa_code: str | None = None,
        source: str | None = None,
        category: str | None = None,
        status: str | None = None,
        deviation_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Capa], int]:
        """带筛选条件的列表查询"""
        query = select(Capa).where(Capa.is_deleted == False)  # noqa: E712

        conditions: list[ColumnElement[bool]] = []
        if capa_code:
            conditions.append(Capa.capa_code.ilike(f"%{capa_code}%"))
        if source:
            conditions.append(Capa.source == source)
        if category:
            conditions.append(Capa.category == category)
        if status:
            conditions.append(Capa.status == status)
        if deviation_id:
            conditions.append(Capa.deviation_id == deviation_id)
        if start_date:
            conditions.append(Capa.created_at >= start_date)
        if end_date:
            conditions.append(Capa.created_at <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # 分页
        query = query.order_by(Capa.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        capas = list(result.scalars().all())

        return capas, total  # type: ignore[return-value]

    async def get_next_capa_code(self) -> str:
        """生成下一个 CAPA 编号"""
        # 获取当前年份
        year = datetime.now().year

        # 查询当前年份的最大编号
        result = await self.session.execute(
            select(Capa.capa_code).where(Capa.capa_code.like(f"CAPA-{year}-%")).order_by(Capa.capa_code.desc()).limit(1)
        )
        last_code = result.scalar_one_or_none()

        if last_code:
            # 提取序号并加1
            last_num = int(last_code.split("-")[-1])
            next_num = last_num + 1
        else:
            next_num = 1

        return f"CAPA-{year}-{next_num:04d}"
