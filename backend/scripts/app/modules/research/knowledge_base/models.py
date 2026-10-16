"""研发项目知识库 ORM 模型（schema=research）。

设计取舍：真实的切片、向量索引与召回由外部 RAGFlow 服务承担，本地只保存
「项目 ↔ 数据集」映射、解析状态与计数。同一份资料不在两处各存一份解析结果，
避免两边进度不一致时无从判断以谁为准。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel

# 知识库状态：creating = 已请求 RAGFlow 建库但尚未拿到数据集 ID（失败可重试）
KB_STATUS_VALUES = ("creating", "active", "failed")
# RAGFlow 文档解析状态（TaskStatus）
DOC_RUN_VALUES = ("UNSTART", "RUNNING", "DONE", "FAIL", "CANCEL")
# 「尚未出结果」的状态：前端轮询进度就是等它们收敛到 DONE / FAIL
DOC_PENDING_VALUES = ("UNSTART", "RUNNING")


class RdKnowledgeBase(BaseModel):
    """研发项目知识库：一个研发项目至多一个有效知识库（软删后可重建）。"""

    __tablename__ = "rd_knowledge_bases"
    __table_args__ = (
        Index("ix_research_rd_knowledge_bases_project", "project_id"),
        Index("ix_research_rd_knowledge_bases_dataset", "ragflow_dataset_id"),
        {"schema": "research"},
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="关联研发项目"
    )
    name: Mapped[str] = mapped_column(String(200), comment="知识库名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="用途说明")
    provider: Mapped[str] = mapped_column(String(32), default="ragflow", comment="知识库提供方")
    ragflow_dataset_id: Mapped[str] = mapped_column(String(64), default="", comment="RAGFlow 数据集 ID")
    embedding_model: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="向量模型标识")
    chunk_method: Mapped[str] = mapped_column(String(32), default="naive", comment="切片方式")
    parser_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="解析参数快照")
    status: Mapped[str] = mapped_column(String(32), default="creating", comment="creating/active/failed")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近一次失败原因")
    document_count: Mapped[int] = mapped_column(Integer, default=0, comment="文档数")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="切片数")
    token_count: Mapped[int] = mapped_column(Integer, default=0, comment="token 数")
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近一次与 RAGFlow 对账时间"
    )


class RdKbDocument(BaseModel):
    """知识库文档：本地只留 RAGFlow 文档 ID 与解析状态，供列表与进度展示。"""

    __tablename__ = "rd_kb_documents"
    __table_args__ = (
        Index("ix_research_rd_kb_documents_kb", "kb_id"),
        Index("ix_research_rd_kb_documents_ragflow", "ragflow_document_id"),
        {"schema": "research"},
    )

    kb_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.rd_knowledge_bases.id"), comment="所属知识库"
    )
    ragflow_document_id: Mapped[str] = mapped_column(String(64), comment="RAGFlow 文档 ID")
    file_name: Mapped[str] = mapped_column(String(500), comment="原始文件名")
    file_ext: Mapped[str] = mapped_column(String(32), default="", comment="扩展名（小写，含点）")
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, comment="字节数")
    sha256: Mapped[str] = mapped_column(String(64), default="", comment="内容哈希（重复上传提示用）")
    run_status: Mapped[str] = mapped_column(String(16), default="UNSTART", comment="UNSTART/RUNNING/DONE/FAIL/CANCEL")
    progress: Mapped[float] = mapped_column(Float, default=0.0, comment="解析进度 0~1")
    progress_msg: Mapped[str | None] = mapped_column(Text, nullable=True, comment="解析日志（RAGFlow 原文）")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="切片数")
    token_count: Mapped[int] = mapped_column(Integer, default=0, comment="token 数")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="解析失败原因")
    parse_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="提交解析时间"
    )
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="解析完成时间")


class RdKbChunk(BaseModel):
    """知识库切片索引：把 RAGFlow 的切片镜像到本地，供事实抽取与离线召回使用。

    为什么需要它：RAGFlow 检索是「按槽位问」，问不到的信息永远不进视野；
    先遍历全库切片建索引，事实抽取才有稳定的数据底座。切片内容的真相仍在
    RAGFlow，本地以 ``content_hash`` 做增量判断（内容未变不会重复抽事实）。
    """

    __tablename__ = "rd_kb_chunks"
    __table_args__ = (
        Index("ix_research_rd_kb_chunks_kb", "kb_id"),
        Index("ix_research_rd_kb_chunks_document", "ragflow_document_id"),
        {"schema": "research"},
    )

    kb_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.rd_knowledge_bases.id"), comment="所属知识库"
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.rd_kb_documents.id"), nullable=True, comment="本地文档行（可空）"
    )
    ragflow_document_id: Mapped[str] = mapped_column(String(64), default="", comment="RAGFlow 文档 ID")
    ragflow_chunk_id: Mapped[str] = mapped_column(String(64), default="", comment="RAGFlow 切片 ID")
    file_name: Mapped[str] = mapped_column(String(500), default="", comment="文档名（证据展示用）")
    content: Mapped[str] = mapped_column(Text, comment="切片原文")
    content_hash: Mapped[str] = mapped_column(String(64), default="", comment="内容哈希（增量判断）")
    char_count: Mapped[int] = mapped_column(Integer, default=0, comment="字符数")
    facts_extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="事实抽取完成时间（空=未抽或内容已变）"
    )
    facts_count: Mapped[int] = mapped_column(Integer, default=0, comment="本切片抽出的事实数")


class RdKbFact(BaseModel):
    """知识库事实：与模板解耦的结构化事实，跨任务复用。

    抽取不依赖任何模板，因此模板没问到的信息也会进库；同一条事实可被多个
    填充项复用。人工确认过的事实（``locked=True``）不会被自动流程覆盖或删除。
    """

    __tablename__ = "rd_kb_facts"
    __table_args__ = (
        Index("ix_research_rd_kb_facts_kb", "kb_id"),
        Index("ix_research_rd_kb_facts_chunk", "chunk_id"),
        {"schema": "research"},
    )

    kb_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.rd_knowledge_bases.id"), comment="所属知识库"
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.rd_kb_chunks.id"), nullable=True, comment="来源切片"
    )
    document_name: Mapped[str] = mapped_column(String(500), default="", comment="来源文档名")
    subject: Mapped[str] = mapped_column(String(300), default="", comment="主体（对象）")
    predicate: Mapped[str] = mapped_column(String(300), default="", comment="谓词（属性/关系）")
    value: Mapped[str] = mapped_column(Text, comment="值")
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="单位")
    quote: Mapped[str] = mapped_column(Text, comment="原文引用（证据）")
    confidence: Mapped[float] = mapped_column(Float, default=0.7, comment="抽取置信度 0~1")
    source: Mapped[str] = mapped_column(String(16), default="auto", comment="auto/human")
    locked: Mapped[bool] = mapped_column(Boolean, default=False, comment="人工确认后锁定，自动流程不得覆盖")
