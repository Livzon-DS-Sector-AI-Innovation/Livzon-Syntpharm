#!/usr/bin/env python3
"""
知识图谱 Mock 数据种子脚本
用于测试知识图谱功能，插入模拟的法规知识图谱数据
"""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.safety.models import GraphKnowledgeNode, GraphKnowledgeEdge


# Mock 数据定义
MOCK_NODES = [
    # 分类节点 (category)
    {
        "id": "cat-001",
        "name": "法律法规",
        "node_type": "category",
        "status": "human_confirmed",
        "confidence": 1.0,
    },
    {
        "id": "cat-002",
        "name": "标准规范",
        "node_type": "category",
        "status": "human_confirmed",
        "confidence": 1.0,
    },
    {
        "id": "cat-003",
        "name": "管理制度",
        "node_type": "category",
        "status": "human_confirmed",
        "confidence": 1.0,
    },
    {
        "id": "cat-004",
        "name": "应急预案",
        "node_type": "category",
        "status": "human_confirmed",
        "confidence": 1.0,
    },
    # 文档节点 (document)
    {
        "id": "doc-001",
        "name": "安全生产法",
        "node_type": "document",
        "entity_type": "standard",
        "ai_summary": "中华人民共和国安全生产法，规范生产经营单位的安全生产行为",
        "status": "ai_generated",
        "confidence": 0.95,
    },
    {
        "id": "doc-002",
        "name": "危险化学品安全管理条例",
        "node_type": "document",
        "entity_type": "standard",
        "ai_summary": "规范危险化学品的生产、储存、使用、经营和运输安全",
        "status": "ai_generated",
        "confidence": 0.92,
    },
    {
        "id": "doc-003",
        "name": "GB/T 36000-2015 社会责任指南",
        "node_type": "document",
        "entity_type": "standard",
        "ai_summary": "国家标准，指导企业履行社会责任",
        "status": "ai_generated",
        "confidence": 0.88,
    },
    {
        "id": "doc-004",
        "name": "企业安全生产责任制",
        "node_type": "document",
        "entity_type": "standard",
        "ai_summary": "明确企业各级人员的安全生产职责",
        "status": "ai_generated",
        "confidence": 0.90,
    },
    {
        "id": "doc-005",
        "name": "化学品泄漏应急预案",
        "node_type": "document",
        "entity_type": "standard",
        "ai_summary": "针对化学品泄漏事故的应急处置方案",
        "status": "ai_generated",
        "confidence": 0.85,
    },
    # 条款节点 (clause)
    {
        "id": "clause-001",
        "name": "第四条 生产经营单位的基本义务",
        "node_type": "clause",
        "ai_summary": "生产经营单位必须遵守本法和其他有关安全生产的法律、法规",
        "status": "ai_generated",
        "confidence": 0.87,
    },
    {
        "id": "clause-002",
        "name": "第二十一条 安全生产管理机构",
        "node_type": "clause",
        "ai_summary": "矿山、金属冶炼、建筑施工、道路运输单位和危险物品的生产、经营、储存单位，应当设置安全生产管理机构",  # noqa: E501  # noqa: E501
        "status": "ai_generated",
        "confidence": 0.89,
    },
    {
        "id": "clause-003",
        "name": "第十条 危险化学品登记",
        "node_type": "clause",
        "ai_summary": "国家实行危险化学品登记制度，为危险化学品安全管理以及事故预防提供技术支持",
        "status": "ai_generated",
        "confidence": 0.86,
    },
    # 实体节点 (entity)
    {
        "id": "entity-001",
        "name": "安全生产责任制",
        "node_type": "entity",
        "entity_type": "concept",
        "ai_summary": "企业各级领导、职能部门、工程技术人员和生产工人在生产中应负的安全责任",
        "status": "ai_generated",
        "confidence": 0.82,
    },
    {
        "id": "entity-002",
        "name": "危险化学品",
        "node_type": "entity",
        "entity_type": "concept",
        "ai_summary": "具有毒害、腐蚀、爆炸、燃烧、助燃等性质，对人体、设施、环境具有危害的剧毒化学品和其他化学品",
        "status": "ai_generated",
        "confidence": 0.91,
    },
    {
        "id": "entity-003",
        "name": "应急预案体系",
        "node_type": "entity",
        "entity_type": "concept",
        "ai_summary": "由综合应急预案、专项应急预案和现场处置方案构成的应急体系",
        "status": "ai_generated",
        "confidence": 0.84,
    },
]

MOCK_EDGES = [
    # belongs_to 关系 (文档属于分类)
    {
        "id": "edge-001",
        "source_node_id": "doc-001",
        "target_node_id": "cat-001",
        "relation_type": "belongs_to",
        "description": "安全生产法属于法律法规",
        "confidence": 0.95,
        "status": "ai_generated",
    },
    {
        "id": "edge-002",
        "source_node_id": "doc-002",
        "target_node_id": "cat-001",
        "relation_type": "belongs_to",
        "description": "危险化学品安全管理条例属于法律法规",
        "confidence": 0.93,
        "status": "ai_generated",
    },
    {
        "id": "edge-003",
        "source_node_id": "doc-003",
        "target_node_id": "cat-002",
        "relation_type": "belongs_to",
        "description": "GB/T 36000-2015属于标准规范",
        "confidence": 0.90,
        "status": "ai_generated",
    },
    {
        "id": "edge-004",
        "source_node_id": "doc-004",
        "target_node_id": "cat-003",
        "relation_type": "belongs_to",
        "description": "企业安全生产责任制属于管理制度",
        "confidence": 0.92,
        "status": "ai_generated",
    },
    {
        "id": "edge-005",
        "source_node_id": "doc-005",
        "target_node_id": "cat-004",
        "relation_type": "belongs_to",
        "description": "化学品泄漏应急预案属于应急预案",
        "confidence": 0.88,
        "status": "ai_generated",
    },
    # contains 关系 (文档包含条款)
    {
        "id": "edge-006",
        "source_node_id": "doc-001",
        "target_node_id": "clause-001",
        "relation_type": "contains",
        "description": "安全生产法包含第四条",
        "confidence": 0.90,
        "status": "ai_generated",
    },
    {
        "id": "edge-007",
        "source_node_id": "doc-001",
        "target_node_id": "clause-002",
        "relation_type": "contains",
        "description": "安全生产法包含第二十一条",
        "confidence": 0.90,
        "status": "ai_generated",
    },
    {
        "id": "edge-008",
        "source_node_id": "doc-002",
        "target_node_id": "clause-003",
        "relation_type": "contains",
        "description": "危险化学品安全管理条例包含第十条",
        "confidence": 0.88,
        "status": "ai_generated",
    },
    # references 关系 (条款引用实体)
    {
        "id": "edge-009",
        "source_node_id": "clause-001",
        "target_node_id": "entity-001",
        "relation_type": "references",
        "description": "第四条引用安全生产责任制概念",
        "confidence": 0.85,
        "status": "ai_generated",
    },
    {
        "id": "edge-010",
        "source_node_id": "clause-003",
        "target_node_id": "entity-002",
        "relation_type": "references",
        "description": "第十条引用危险化学品概念",
        "confidence": 0.87,
        "status": "ai_generated",
    },
    {
        "id": "edge-011",
        "source_node_id": "doc-005",
        "target_node_id": "entity-003",
        "relation_type": "references",
        "description": "化学品泄漏应急预案引用应急预案体系",
        "confidence": 0.83,
        "status": "ai_generated",
    },
    # related_to 关系 (实体间关联)
    {
        "id": "edge-012",
        "source_node_id": "entity-001",
        "target_node_id": "entity-002",
        "relation_type": "related_to",
        "description": "安全生产责任制与危险化学品管理相关",
        "confidence": 0.75,
        "status": "ai_generated",
    },
    {
        "id": "edge-013",
        "source_node_id": "entity-002",
        "target_node_id": "entity-003",
        "relation_type": "related_to",
        "description": "危险化学品需要应急预案体系",
        "confidence": 0.80,
        "status": "ai_generated",
    },
]


def parse_uuid(id_str: str) -> uuid.UUID:
    """将字符串 ID 转换为 UUID"""
    # 使用简单的哈希生成确定性 UUID
    import hashlib

    hash_bytes = hashlib.md5(id_str.encode()).digest()
    return uuid.UUID(bytes=hash_bytes[:16])


async def seed_knowledge_graph():
    """插入知识图谱 mock 数据"""
    async with async_session_factory() as session:
        # 检查是否已有数据
        result = await session.execute(select(GraphKnowledgeNode).limit(1))
        if result.scalar_one_or_none():
            print("⚠️  知识图谱已有数据，跳过插入")
            return

        print("🌱 开始插入知识图谱 mock 数据...")

        # 插入节点
        node_map = {}
        for node_data in MOCK_NODES:
            node = GraphKnowledgeNode(
                id=parse_uuid(node_data["id"]),
                name=node_data["name"],
                node_type=node_data["node_type"],
                entity_type=node_data.get("entity_type"),
                ai_summary=node_data.get("ai_summary"),
                confidence=node_data.get("confidence", 0.8),
                status=node_data.get("status", "ai_generated"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_deleted=False,
            )
            session.add(node)
            node_map[node_data["id"]] = node.id
            print(f"  ✓ 节点: {node.name} ({node.node_type})")

        await session.flush()

        # 插入边
        for edge_data in MOCK_EDGES:
            edge = GraphKnowledgeEdge(
                id=parse_uuid(edge_data["id"]),
                source_node_id=node_map[edge_data["source_node_id"]],
                target_node_id=node_map[edge_data["target_node_id"]],
                relation_type=edge_data["relation_type"],
                description=edge_data.get("description"),
                confidence=edge_data.get("confidence", 0.8),
                status=edge_data.get("status", "ai_generated"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_deleted=False,
            )
            session.add(edge)
            print(f"  ✓ 边: {edge.relation_type}")

        await session.commit()
        print(f"\n✅ 成功插入 {len(MOCK_NODES)} 个节点和 {len(MOCK_EDGES)} 条边")


if __name__ == "__main__":
    asyncio.run(seed_knowledge_graph())
