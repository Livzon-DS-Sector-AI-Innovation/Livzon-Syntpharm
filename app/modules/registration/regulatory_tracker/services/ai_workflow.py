"""
AI 分析工作流抽象层

提供 AI 分析任务的调度和执行接口。
V1 实现：顺序执行（在后台线程中）
未来可替换为：Celery/Redis 队列
"""

import logging
from typing import Protocol
from uuid import UUID

from app.modules.registration.regulatory_tracker.models.regulatory_document import RegulatoryDocument
from app.modules.registration.regulatory_tracker.services.ai_analysis_service import (
    analyze_and_update,
)

logger = logging.getLogger(__name__)


class AIWorkflow(Protocol):
    """AI 工作流接口"""

    async def submit_documents(self, document_ids: list[UUID]) -> None:
        """提交文档进行 AI 分析"""
        ...


class SequentialAIWorkflow:
    """
    顺序执行的 AI 工作流（V1 实现）

    在后台任务中顺序处理文档，不阻塞主流程。
    未来可替换为队列实现。
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def submit_documents(self, document_ids: list[UUID]) -> None:
        """
        提交文档进行 AI 分析

        Args:
            document_ids: 待分析的文档 ID 列表
        """
        if not document_ids:
            logger.info("没有需要分析的文档")
            return

        logger.info(f"开始处理 {len(document_ids)} 个文档的 AI 分析")

        success_count = 0
        fail_count = 0

        for doc_id in document_ids:
            try:
                async with self.session_factory() as session:
                    # 查询文档
                    from sqlalchemy import select

                    result = await session.execute(
                        select(RegulatoryDocument).where(
                            RegulatoryDocument.id == doc_id
                        )
                    )
                    document = result.scalar_one_or_none()

                    if not document:
                        logger.warning(f"文档不存在: {doc_id}")
                        continue

                    # 执行分析
                    success = await analyze_and_update(session, document)

                    if success:
                        success_count += 1
                    else:
                        fail_count += 1

            except Exception as e:
                fail_count += 1
                logger.error(f"处理文档 {doc_id} 失败: {e}", exc_info=True)

        logger.info(f"AI 分析完成: 成功={success_count}, 失败={fail_count}")


# 全局工作流实例（延迟初始化）
_workflow_instance: SequentialAIWorkflow | None = None


def get_ai_workflow() -> SequentialAIWorkflow:
    """获取 AI 工作流实例"""
    global _workflow_instance
    if _workflow_instance is None:
        from app.core.database import async_session_factory

        _workflow_instance = SequentialAIWorkflow(async_session_factory)
    return _workflow_instance
