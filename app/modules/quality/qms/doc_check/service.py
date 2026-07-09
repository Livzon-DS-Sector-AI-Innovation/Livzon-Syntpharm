"""Doc Check 模块业务逻辑层

提供文档合规校验的核心业务逻辑，包括 AI 调用、问题解析等。
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.doc_check.models import (
    CheckStatus,
    ProblemCategory,
    ProblemSeverity,
)
from app.modules.quality.qms.doc_check.repository import DocCheckRepository
from app.modules.quality.qms.doc_check.schemas import (
    DocCheckConfigCreate,
    DocCheckConfigUpdate,
    DocCheckCreate,
    DocCheckUpdate,
)
from app.modules.quality.ai.minimax_util import MinimaxAiUtil

logger = logging.getLogger(__name__)


class DocCheckService:
    """Doc Check 模块服务层"""

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """你是一位专业的GMP文档审核专家，负责审核制药企业的SOP文档、质量标准等文件。
请根据以下维度对文档进行审核：
1. 格式规范：检查文档格式是否符合企业规范
2. 内容完整性：检查必要章节是否完整
3. 合规性：检查是否符合GMP法规要求
4. 逻辑性：检查流程和步骤是否合理
5. 风险识别：识别潜在的质量风险

请以JSON格式返回审核结果，格式如下：
{
    "status": "completed",
    "check_result": {...},
    "ai_suggestion": "改进建议...",
    "problems": [
        {
            "problem_no": 1,
            "category": "format|content|compliance|logic|missing",
            "severity": "info|warning|error|critical",
            "title": "问题标题",
            "description": "问题描述",
            "location": "位置信息",
            "suggestion": "改进建议",
            "reference": "参考依据"
        }
    ]
}"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DocCheckRepository(session)

    # ============ 配置操作 ============

    async def get_configs(self) -> list[Any]:
        """获取配置列表"""
        return await self.repo.get_configs()

    async def get_config_by_key(self, config_key: str) -> Any | None:
        """根据键获取配置"""
        return await self.repo.get_config_by_key(config_key)

    async def create_config(self, data: DocCheckConfigCreate) -> Any:
        """创建配置"""
        config_data = {
            "config_key": data.config_key,
            "config_value": data.config_value,
            "description": data.description,
        }
        return await self.repo.create_config(config_data)

    async def update_config(
        self, config_id: uuid.UUID, data: DocCheckConfigUpdate
    ) -> Any | None:
        """更新配置"""
        update_data = {}
        if data.config_value is not None:
            update_data["config_value"] = data.config_value
        if data.description is not None:
            update_data["description"] = data.description

        return await self.repo.update_config(config_id, update_data)

    # ============ 校验操作 ============

    async def get_checks(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        doc_type: str | None = None,
        operator: str | None = None,
    ) -> tuple[list, int]:
        """获取校验列表"""
        return await self.repo.get_checks(
            skip=skip,
            limit=limit,
            status=status,
            doc_type=doc_type,
            operator=operator,
        )

    async def get_check(self, check_id: uuid.UUID) -> Any | None:
        """获取校验详情"""
        return await self.repo.get_check_by_id(check_id)

    async def create_check(
        self,
        data: DocCheckCreate,
        operator: str | None = None,
    ) -> Any:
        """创建校验任务"""
        # 生成校验单号
        file_code = await self._generate_check_no(data.doc_type)

        # 如果有file_id，从上传存储中获取文档内容
        doc_content = data.doc_content
        if data.file_id and not doc_content:
            from app.modules.quality.qms.doc_check.api import _upload_store

            upload_data = _upload_store.get(data.file_id)
            if upload_data:
                doc_content = upload_data.get("content", "")
                data.doc_title = upload_data.get("file_name", data.doc_title)

        # 构建主表数据
        check_data = {
            "file_code": file_code,
            "file_type": data.doc_type or "SOP",
            "file_name": data.doc_title,
            "status": CheckStatus.PENDING.value,
            "operator": operator,
        }

        # 创建主表记录
        check = await self.repo.create_check(check_data)

        # 如果有文档内容，保存到result_summary
        if doc_content:
            await self.repo.update_check(
                check.id,
                {
                    "result_summary": doc_content[:10000]
                    if doc_content
                    else None,  # 限制长度
                },
            )

        # 返回完整数据
        return await self.repo.get_check_by_id(check.id)

    async def execute_check(
        self,
        check_id: uuid.UUID,
        operator: str | None = None,
    ) -> Any:
        """执行校验（调用 AI）"""
        # 获取校验任务
        check = await self.repo.get_check_by_id(check_id)
        if not check:
            return None

        # 更新状态为处理中
        await self.repo.update_check(
            check_id,
            {
                "status": CheckStatus.PROCESSING.value,
            },
        )

        try:
            # 获取系统提示词配置
            system_prompt = await self._get_system_prompt()

            # 构建用户消息
            user_message = self._build_check_prompt(
                check.file_type,
                check.file_name or "",
                check.doc_content,
            )

            # 调用 AI
            start_time = time.time()
            ai_util = MinimaxAiUtil()
            ai_response = ai_util.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.7,
                max_tokens=4096,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            # 解析 AI 响应
            result = self._parse_ai_response(ai_response)

            # 更新主表
            update_data = {
                "status": result.get("status", CheckStatus.COMPLETED.value),
                "check_result": json.dumps(
                    result.get("check_result", {}), ensure_ascii=False
                ),
                "ai_suggestion": result.get("ai_suggestion"),
            }

            # 计算向量（若 pgvector 可用则存储，否则降级）
            try:
                vector = self.repo.compute_simple_vector(check.doc_content)
                update_data["content_vector"] = vector
                update_data["vector_storage_type"] = "text"
            except Exception as e:
                logger.warning(f"向量生成失败: {e}")

            # 统计问题数量
            problems = result.get("problems", [])
            problem_count = len(problems)
            critical_count = sum(1 for p in problems if p.get("severity") == "critical")
            error_count = sum(1 for p in problems if p.get("severity") == "error")
            warning_count = sum(1 for p in problems if p.get("severity") == "warning")

            update_data.update(
                {
                    "problem_count": problem_count,
                    "critical_count": critical_count,
                    "error_count": error_count,
                    "warning_count": warning_count,
                }
            )

            await self.repo.update_check(check_id, update_data)

            # 保存问题明细
            if problems:
                await self.repo.delete_problems_by_check(check_id)
                problems_data = []
                for i, prob in enumerate(problems, 1):
                    problems_data.append(
                        {
                            "problem_no": prob.get("problem_no", i),
                            "category": prob.get(
                                "category", ProblemCategory.CONTENT.value
                            ),
                            "severity": prob.get(
                                "severity", ProblemSeverity.WARNING.value
                            ),
                            "title": prob.get("title", ""),
                            "description": prob.get("description", ""),
                            "location": prob.get("location"),
                            "suggestion": prob.get("suggestion"),
                            "reference": prob.get("reference"),
                        }
                    )
                await self.repo.create_problems_bulk(check_id, problems_data)

            logger.info(
                f"文档校验完成: file_code={check.file_code}, "
                f"problem_count={problem_count}, latency_ms={latency_ms}"
            )

            # 返回更新后的数据
            return await self.repo.get_check_by_id(check_id)

        except Exception as e:
            logger.error(f"文档校验失败: {e}")
            # 更新状态为失败
            await self.repo.update_check(
                check_id,
                {
                    "status": CheckStatus.FAILED.value,
                    "check_result": json.dumps({"error": str(e)}, ensure_ascii=False),
                },
            )
            raise

    async def update_check(
        self, check_id: uuid.UUID, data: DocCheckUpdate
    ) -> Any | None:
        """更新校验任务"""
        check = await self.repo.get_check_by_id(check_id)
        if not check:
            return None

        # 状态更新（取消/确认通过）- 允许任何状态
        if data.status is not None:
            # 取消操作：pending/running -> cancelled
            if data.status == "cancelled" and check.status in [
                CheckStatus.PENDING.value,
                CheckStatus.PROCESSING.value,
            ]:
                return await self.repo.update_check(check_id, {"status": data.status})
            # 确认通过：completed -> confirmed
            if (
                data.status == "confirmed"
                and check.status == CheckStatus.COMPLETED.value
            ):
                return await self.repo.update_check(check_id, {"status": data.status})
            # 其他状态更新需要验证
            if check.status != CheckStatus.PENDING.value:
                raise ValueError("只有待处理状态的任务才能编辑")

        update_data = {}
        if data.doc_type is not None:
            update_data["doc_type"] = data.doc_type
        if data.doc_title is not None:
            update_data["doc_title"] = data.doc_title
        if data.doc_content is not None:
            update_data["doc_content"] = data.doc_content

        return await self.repo.update_check(check_id, update_data)

    async def delete_check(self, check_id: uuid.UUID) -> bool:
        """删除校验任务"""
        check = await self.repo.get_check_by_id(check_id)
        if not check:
            return False

        # 只有待处理状态可以删除
        if check.status != CheckStatus.PENDING.value:
            raise ValueError("只有待处理状态的任务才能删除")

        return await self.repo.delete_check(check_id)

    # ============ 问题操作 ============

    async def get_problems(
        self,
        check_main_id: uuid.UUID,
    ) -> list[Any]:
        """获取问题列表"""
        return await self.repo.get_problems_by_check(check_main_id)

    # ============ 向量缓存操作 ============

    async def get_vector_cache(
        self,
        doc_type: str | None = None,
        doc_hash: str | None = None,
    ) -> list[Any]:
        """获取向量缓存"""
        return await self.repo.get_vector_cache(doc_type=doc_type, doc_hash=doc_hash)

    async def get_vector_cache_by_doc(
        self, doc_type: str, doc_content: str
    ) -> Any | None:
        """根据文档获取向量缓存"""
        doc_hash = self.repo.compute_doc_hash(doc_content)
        return await self.repo.get_vector_cache_by_doc(doc_type, doc_hash)

    # ============ 辅助方法 ============

    async def _generate_check_no(self, doc_type: str) -> str:
        """生成校验单号"""
        # 格式: DC-文档类型-时间戳
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"DC-{doc_type}-{timestamp}"

    async def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        config = await self.repo.get_config_by_key("system_prompt")
        if config and config.config_value:
            try:
                return json.loads(config.config_value).get(
                    "prompt", self.DEFAULT_SYSTEM_PROMPT
                )
            except Exception:
                pass
        return self.DEFAULT_SYSTEM_PROMPT

    def _build_check_prompt(
        self, doc_type: str, doc_title: str, doc_content: str
    ) -> str:
        """构建校��提示词"""
        return f"""请审核以下{doc_type}文档：

文档标题：{doc_title}

文档内容：
{doc_content}

请进行合规性审核并返回JSON格式的审核结果。"""

    def _parse_ai_response(self, ai_response: str) -> dict[str, Any]:
        """解析 AI 响应"""
        try:
            # 尝试直接解析 JSON
            result = json.loads(ai_response)
            return result
        except Exception:
            pass

        try:
            # 尝试从文本中提取 JSON
            import re

            json_match = re.search(r"\{.*\}", ai_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except Exception:
            pass

        # 解析失败，返回错误结果
        logger.warning(f"AI 响应解析失败: {ai_response[:200]}")
        return {
            "status": CheckStatus.FAILED.value,
            "check_result": {"raw_response": ai_response},
            "ai_suggestion": "AI 响应解析失败，请检查格式",
            "problems": [],
        }
