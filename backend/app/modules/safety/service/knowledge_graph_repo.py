"""Knowledge Graph repository — database access for graph nodes and edges."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.models import GraphKnowledgeEdge, GraphKnowledgeNode


class KnowledgeGraphRepository:
    """Repository for knowledge graph nodes and edges."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Node operations ──

    async def get_nodes(
        self,
        conditions: list[Any],
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[GraphKnowledgeNode], int]:
        """Get nodes matching conditions with pagination."""
        count_stmt = select(func.count()).select_from(GraphKnowledgeNode).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(GraphKnowledgeNode)
            .where(and_(*conditions))
            .order_by(GraphKnowledgeNode.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_node(self, node_id: uuid.UUID) -> GraphKnowledgeNode | None:
        """Get a single node by ID."""
        stmt = select(GraphKnowledgeNode).where(
            GraphKnowledgeNode.id == node_id,
            GraphKnowledgeNode.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search_nodes(self, conditions: list[Any], limit: int = 50) -> list[GraphKnowledgeNode]:
        """Search nodes matching conditions."""
        stmt = (
            select(GraphKnowledgeNode)
            .where(and_(*conditions))
            .order_by(GraphKnowledgeNode.name)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_nodes_unordered(self, conditions: list[Any], limit: int = 500) -> list[GraphKnowledgeNode]:
        """Get nodes matching conditions (ordered by created_at ASC, with limit)."""
        stmt = (
            select(GraphKnowledgeNode)
            .where(and_(*conditions))
            .order_by(GraphKnowledgeNode.created_at)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_node(self, node: GraphKnowledgeNode) -> None:
        """Add a new node."""
        self.db.add(node)
        await self.db.flush()

    async def find_node(self, conditions: list[Any]) -> GraphKnowledgeNode | None:
        """Find a single node matching conditions."""
        stmt = select(GraphKnowledgeNode).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Edge operations ──

    async def get_edges(
        self,
        conditions: list[Any],
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[GraphKnowledgeEdge], int]:
        """Get edges matching conditions with pagination."""
        count_stmt = select(func.count()).select_from(GraphKnowledgeEdge).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(GraphKnowledgeEdge)
            .where(and_(*conditions))
            .order_by(GraphKnowledgeEdge.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_edges_unordered(self, conditions: list[Any], limit: int = 2000) -> list[GraphKnowledgeEdge]:
        """Get edges matching conditions (ordered by created_at ASC, with limit)."""
        stmt = (
            select(GraphKnowledgeEdge)
            .where(and_(*conditions))
            .order_by(GraphKnowledgeEdge.created_at)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_edge(self, edge: GraphKnowledgeEdge) -> None:
        """Add a new edge."""
        self.db.add(edge)

    async def flush(self) -> None:
        """Flush pending changes."""
        await self.db.flush()
