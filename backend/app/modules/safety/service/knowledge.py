"""Safety business workflows."""

import logging
import os
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import delete_object
from app.core.storage import is_enabled as minio_enabled
from app.modules.safety.models import (
    SafetyKnowledgeArticle,
)
from app.modules.safety.repository import SafetyRepository
from app.modules.safety.schemas import (
    SafetyKnowledgeArticleCreate,
    SafetyKnowledgeArticleUpdate,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """安全知识库业务服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SafetyRepository(session)

    @staticmethod
    def _cleanup_file(file_path: str | None) -> None:
        """Delete a single file from MinIO or local disk."""
        if not file_path:
            return
        try:
            if minio_enabled():
                try:
                    delete_object("safety", file_path)
                except Exception:
                    logger.warning("Failed to delete file from MinIO: %s", file_path, exc_info=True)
            else:
                abs_path = os.path.abspath(file_path)
                if os.path.exists(abs_path):
                    os.remove(abs_path)
        except OSError:
            pass

    async def get_articles(
        self,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[SafetyKnowledgeArticle], int]:
        """获取知识库文章列表"""
        return await self.repo.get_knowledge_articles(skip, limit, category, status, keyword)

    async def get_article(self, article_id: uuid.UUID) -> SafetyKnowledgeArticle | None:
        """获取文章详情（浏览计数+1）"""
        article = await self.repo.get_knowledge_article_by_id(article_id)
        if article:
            await self.repo.update_knowledge_article(article_id, {"view_count": article.view_count + 1})
        return article

    async def create_article(self, data: SafetyKnowledgeArticleCreate) -> SafetyKnowledgeArticle:
        """创建知识库文章"""
        article_data = data.model_dump()
        return await self.repo.create_knowledge_article(article_data)

    async def update_article(
        self, article_id: uuid.UUID, data: SafetyKnowledgeArticleUpdate
    ) -> SafetyKnowledgeArticle | None:
        """更新知识库文章"""
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        return await self.repo.update_knowledge_article(article_id, update_data)

    async def delete_article(self, article_id: uuid.UUID) -> bool:
        """删除知识库文章"""
        article = await self.repo.get_knowledge_article_by_id(article_id)
        result = await self.repo.delete_knowledge_article(article_id)
        if result and article:
            self._cleanup_file(article.attachment_path)
        return result

    async def publish_article(self, article_id: uuid.UUID) -> SafetyKnowledgeArticle | None:
        """发布文章（草稿→已发布）"""
        article = await self.repo.get_knowledge_article_by_id(article_id)
        if not article or article.status != "draft":
            return None
        return await self.repo.update_knowledge_article(article_id, {"status": "published"})

    async def archive_article(self, article_id: uuid.UUID) -> SafetyKnowledgeArticle | None:
        """归档文章（已发布→已归档）"""
        article = await self.repo.get_knowledge_article_by_id(article_id)
        if not article or article.status != "published":
            return None
        return await self.repo.update_knowledge_article(article_id, {"status": "archived"})

    # ==================== 风险作业报备 Services ====================

    # ── AI 生成 ──

    async def generate_card(self, article_id: uuid.UUID) -> dict[str, Any]:
        """使用 AI 从文章内容生成知识卡片"""
        from app.core.llm import llm_client
        from app.core.llm.exceptions import LLMConfigError

        article = await self.repo.get_knowledge_article_by_id(article_id)
        if not article:
            raise ValueError("文章不存在")
        if not article.content:
            raise ValueError("文章内容为空，无法生成知识卡片")

        try:
            prompt = f"""请为以下法规文档生成一张结构化知识卡片（JSON 格式）。

文档标题：{article.title}
文档分类：{article.category}

文档内容：
{article.content[:3000] if article.content else ""}

请以 JSON 格式返回：
{{
  "title": "文档标题",
  "key_points": ["要点1", "要点2", "要点3"],
  "applicable_scope": "适用范围",
  "important_deadlines": ["重要期限1", "重要期限2"],
  "responsible_parties": ["责任主体1", "责任主体2"],
  "penalties": ["违规后果1", "违规后果2"],
  "summary": "200字以内的摘要"
}}"""
            card = await llm_client.chat_json(
                messages=[{"role": "user", "content": prompt}],
                expected_keys=["title", "key_points", "summary"],
            )
            return {"card": card, "message": "知识卡片生成成功"}
        except LLMConfigError:
            # 降级方案：提取基础信息
            card = {
                "title": article.title,
                "key_points": [],
                "summary": article.content[:500] if article.content else "",
                "message": "AI 服务未配置，已生成基础卡片",
            }
            if article.content:
                for sep in ["。", "；", ";", ".", "\n"]:
                    last_sep = card["summary"].rfind(sep)
                    if last_sep > 100:
                        card["summary"] = card["summary"][: last_sep + 1]
                        break
            return card
        except Exception:
            logger.exception("知识卡片生成失败: article_id=%s", article_id)
            raise

    async def generate_summary(self, article_id: uuid.UUID) -> dict[str, Any]:
        """使用 AI 从文章内容生成摘要"""
        from app.core.llm import llm_client
        from app.core.llm.exceptions import LLMConfigError

        article = await self.repo.get_knowledge_article_by_id(article_id)
        if not article:
            raise ValueError("文章不存在")
        if not article.content:
            raise ValueError("文章内容为空，无法生成摘要")

        try:
            prompt = f"""请为以下法规文档生成结构化摘要。

文档标题：{article.title}
文档分类：{article.category}

文档内容：
{article.content[:3000] if article.content else ""}

请生成 200-500 字的摘要，包含：
1. 文档的核心目的和适用范围
2. 主要内容和关键条款
3. 重要要求和注意事项

直接返回摘要文本，不需要 JSON 格式。"""
            summary = await llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format=None,
            )
            await self.repo.update_knowledge_article(article_id, {"summary": summary})
            return {"summary": summary, "message": "摘要生成成功"}
        except LLMConfigError:
            # 降级方案：提取前 500 字符作为摘要
            summary = article.content[:500]
            for sep in ["。", "；", ";", ".", "\n"]:
                last_sep = summary.rfind(sep)
                if last_sep > 100:
                    summary = summary[: last_sep + 1]
                    break
            if len(article.content) > 500:
                summary += "..."
            await self.repo.update_knowledge_article(article_id, {"summary": summary})
            return {"summary": summary, "message": "AI 服务未配置，已生成基础摘要"}
        except Exception:
            logger.exception("摘要生成失败: article_id=%s", article_id)
            raise

    async def get_ppt_history(self, article_id: uuid.UUID, skip: int = 0, limit: int = 20) -> tuple[list[Any], int]:
        """查询某文章的 PPT 生成历史"""
        return await self.repo.get_ppt_generation_records(article_id, skip, limit)
