"""Knowledge Graph Service — 知识图谱数据服务"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.models import GraphKnowledgeEdge, GraphKnowledgeNode


class KnowledgeGraphService:
    """知识图谱服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 节点操作 ──────────────────────────────────────────

    async def get_nodes(
        self,
        node_type: str | None = None,
        entity_type: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[GraphKnowledgeNode], int]:
        """获取节点列表（分页）"""
        conditions = [GraphKnowledgeNode.is_deleted == False]  # noqa: E712
        if node_type:
            conditions.append(GraphKnowledgeNode.node_type == node_type)
        if entity_type:
            conditions.append(GraphKnowledgeNode.entity_type == entity_type)
        if status:
            conditions.append(GraphKnowledgeNode.status == status)
        if keyword:
            conditions.append(GraphKnowledgeNode.name.ilike(f"%{keyword}%"))

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
        """获取单个节点"""
        stmt = select(GraphKnowledgeNode).where(
            GraphKnowledgeNode.id == node_id,
            GraphKnowledgeNode.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search_nodes(
        self,
        query: str,
        node_types: str | None = None,
        limit: int = 50,
    ) -> list[GraphKnowledgeNode]:
        """搜索节点"""
        conditions = [
            GraphKnowledgeNode.is_deleted == False,  # noqa: E712
            GraphKnowledgeNode.name.ilike(f"%{query}%"),
        ]
        if node_types:
            types = [t.strip() for t in node_types.split(",") if t.strip()]
            if types:
                conditions.append(GraphKnowledgeNode.node_type.in_(types))

        stmt = select(GraphKnowledgeNode).where(and_(*conditions)).order_by(GraphKnowledgeNode.name).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── 边操作 ────────────────────────────────────────────

    async def get_edges(
        self,
        relation_type: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[GraphKnowledgeEdge], int]:
        """获取边列表（分页）"""
        conditions = [GraphKnowledgeEdge.is_deleted == False]  # noqa: E712
        if relation_type:
            conditions.append(GraphKnowledgeEdge.relation_type == relation_type)
        if status:
            conditions.append(GraphKnowledgeEdge.status == status)

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

    # ── 完整图谱 ──────────────────────────────────────────

    async def get_full_graph(
        self,
        node_types: str | None = None,
        relation_types: str | None = None,
        max_nodes: int = 500,
    ) -> dict[str, Any]:
        """获取完整图谱数据"""
        node_conditions = [GraphKnowledgeNode.is_deleted == False]  # noqa: E712
        if node_types:
            types = [t.strip() for t in node_types.split(",") if t.strip()]
            if types:
                node_conditions.append(GraphKnowledgeNode.node_type.in_(types))

        node_stmt = (
            select(GraphKnowledgeNode)
            .where(and_(*node_conditions))
            .order_by(GraphKnowledgeNode.created_at)
            .limit(max_nodes)
        )
        node_result = await self.db.execute(node_stmt)
        nodes = list(node_result.scalars().all())
        node_ids = {n.id for n in nodes}

        edge_conditions = [
            GraphKnowledgeEdge.is_deleted == False,  # noqa: E712
            GraphKnowledgeEdge.source_node_id.in_(node_ids),
            GraphKnowledgeEdge.target_node_id.in_(node_ids),
        ]
        if relation_types:
            rel_types = [t.strip() for t in relation_types.split(",") if t.strip()]
            if rel_types:
                edge_conditions.append(GraphKnowledgeEdge.relation_type.in_(rel_types))

        edge_stmt = select(GraphKnowledgeEdge).where(and_(*edge_conditions))
        edge_result = await self.db.execute(edge_stmt)
        edges = list(edge_result.scalars().all())

        # 统计
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for n in nodes:
            by_type[n.node_type] = by_type.get(n.node_type, 0) + 1
            by_status[n.status] = by_status.get(n.status, 0) + 1

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "by_type": by_type,
                "by_status": by_status,
            },
        }

    # ─ 节点展开（邻居） ─────────────────────────────────

    async def expand_node(
        self,
        node_id: uuid.UUID,
        hops: int = 1,
        relation_types: str | None = None,
        max_nodes: int = 30,
    ) -> dict[str, Any]:
        """展开指定节点的邻居"""
        center = await self.get_node(node_id)
        if not center:
            return {
                "nodes": [],
                "edges": [],
                "stats": {"total_nodes": 0, "total_edges": 0, "by_type": {}, "by_status": {}},
            }

        visited_ids: set[uuid.UUID] = {node_id}
        all_node_ids: set[uuid.UUID] = {node_id}
        all_edge_ids: set[uuid.UUID] = set()

        current_ids = {node_id}
        for _ in range(hops):
            if not current_ids:
                break
            edge_conditions = [
                GraphKnowledgeEdge.is_deleted == False,  # noqa: E712
                or_(
                    GraphKnowledgeEdge.source_node_id.in_(current_ids),
                    GraphKnowledgeEdge.target_node_id.in_(current_ids),
                ),
            ]
            if relation_types:
                rel_types = [t.strip() for t in relation_types.split(",") if t.strip()]
                if rel_types:
                    edge_conditions.append(GraphKnowledgeEdge.relation_type.in_(rel_types))

            edge_stmt = select(GraphKnowledgeEdge).where(and_(*edge_conditions))
            edge_result = await self.db.execute(edge_stmt)
            batch_edges = list(edge_result.scalars().all())

            next_ids: set[uuid.UUID] = set()
            for e in batch_edges:
                all_edge_ids.add(e.id)
                if e.source_node_id not in visited_ids:
                    next_ids.add(e.source_node_id)
                if e.target_node_id not in visited_ids:
                    next_ids.add(e.target_node_id)

            visited_ids.update(next_ids)
            all_node_ids.update(next_ids)
            current_ids = next_ids

            if len(all_node_ids) >= max_nodes:
                break

        # 获取所有节点
        node_stmt = (
            select(GraphKnowledgeNode)
            .where(
                GraphKnowledgeNode.id.in_(all_node_ids),
                GraphKnowledgeNode.is_deleted == False,  # noqa: E712
            )
            .limit(max_nodes)
        )
        node_result = await self.db.execute(node_stmt)
        nodes = list(node_result.scalars().all())

        edge_stmt = select(GraphKnowledgeEdge).where(
            GraphKnowledgeEdge.id.in_(all_edge_ids),
            GraphKnowledgeEdge.is_deleted == False,  # noqa: E712
        )
        edge_result = await self.db.execute(edge_stmt)
        edges = list(edge_result.scalars().all())

        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for n in nodes:
            by_type[n.node_type] = by_type.get(n.node_type, 0) + 1
            by_status[n.status] = by_status.get(n.status, 0) + 1

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "by_type": by_type,
                "by_status": by_status,
            },
        }

    # ── AI 生成图谱 ──────────────────────────────────────

    async def generate_graph(
        self,
        document_ids: list[uuid.UUID] | None = None,
        force_rebuild: bool = False,
    ) -> dict[str, Any]:
        """
        从知识库文章生成知识图谱。
        当前版本：基于已有文章创建分类节点和文档节点。
        """
        from app.modules.safety.models import SafetyKnowledgeArticle

        errors: list[str] = []
        nodes_created = 0
        edges_created = 0

        # 1. 获取文章
        article_conditions = [
            SafetyKnowledgeArticle.is_deleted == False,  # noqa: E712
            SafetyKnowledgeArticle.status == "published",
        ]
        if document_ids:
            article_conditions.append(SafetyKnowledgeArticle.id.in_(document_ids))

        article_stmt = select(SafetyKnowledgeArticle).where(and_(*article_conditions))
        article_result = await self.db.execute(article_stmt)
        articles = list(article_result.scalars().all())

        if not articles:
            return {"status": "no_data", "nodes_created": 0, "edges_created": 0, "errors": ["没有已发布的文章"]}

        # 2. 按分类创建/获取 category 节点
        category_map: dict[str, GraphKnowledgeNode] = {}
        for article in articles:
            cat = article.category or "other"
            if cat not in category_map:
                existing = await self._find_or_create_category(cat)
                category_map[cat] = existing

        # 3. 为每篇文章创建 document 节点 + belongs_to 边
        for article in articles:
            # 检查是否已存在
            doc_existing = await self._find_document_node(article.id)
            if doc_existing and not force_rebuild:
                continue

            doc_node = GraphKnowledgeNode(
                name=article.title,
                node_type="document",
                article_id=article.id,
                entity_type="standard" if article.category in ("laws_regulations", "standards") else None,
                ai_summary=article.summary,
                confidence=0.9,
                status="ai_generated",
            )
            self.db.add(doc_node)
            await self.db.flush()
            nodes_created += 1

            # belongs_to 边
            cat = article.category or "other"
            if cat in category_map:
                edge = GraphKnowledgeEdge(
                    source_node_id=doc_node.id,
                    target_node_id=category_map[cat].id,
                    relation_type="belongs_to",
                    description=f"{article.title} 属于 {cat}",
                    confidence=0.95,
                    status="ai_generated",
                )
                self.db.add(edge)
                edges_created += 1

        await self.db.flush()

        return {
            "status": "success",
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "errors": errors,
        }

    async def _find_or_create_category(self, category: str) -> GraphKnowledgeNode:
        """查找或创建分类节点"""
        cat_labels = {
            "laws_regulations": "法律法规",
            "standards": "标准规范",
            "management_systems": "管理制度",
            "accident_cases": "事故案例",
            "emergency_plans": "应急预案",
            "sds": "化学品安全技术说明书",
            "training_materials": "培训教材",
            "other": "其他",
        }
        name = cat_labels.get(category, category)

        stmt = select(GraphKnowledgeNode).where(
            GraphKnowledgeNode.node_type == "category",
            GraphKnowledgeNode.name == name,
            GraphKnowledgeNode.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        node = GraphKnowledgeNode(
            name=name,
            node_type="category",
            confidence=1.0,
            status="human_confirmed",
        )
        self.db.add(node)
        await self.db.flush()
        return node

    async def _find_document_node(self, article_id: uuid.UUID) -> GraphKnowledgeNode | None:
        """查找文章对应的文档节点"""
        stmt = select(GraphKnowledgeNode).where(
            GraphKnowledgeNode.node_type == "document",
            GraphKnowledgeNode.article_id == article_id,
            GraphKnowledgeNode.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
