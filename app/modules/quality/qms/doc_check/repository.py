"""Doc Check 模块数据访问层

提供文档校验相关的数据操作，包括 CRUD、向量存储等。
"""

import hashlib
import random
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.sop_ai.models import (
    SopAiCheckMain,
    SopAiCheckProblem,
    SopAiConfig as DocCheckConfig,
)


class DocCheckRepository:
    """Doc Check 模块仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============ 配置操作 ============

    async def get_configs(
        self,
        is_enabled: bool | None = None,
    ) -> list[DocCheckConfig]:
        """获取配置列表"""
        # SopAiConfig 表结构简单，不使用软删除
        query = select(DocCheckConfig).order_by(DocCheckConfig.config_key)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_config_by_key(self, config_key: str) -> DocCheckConfig | None:
        """根据键获取配置"""
        query = select(DocCheckConfig).where(
            DocCheckConfig.config_key == config_key,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_config(self, data: dict[str, Any]) -> DocCheckConfig:
        """创建配置"""
        config = DocCheckConfig(**data)
        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def update_config(
        self, config_id: uuid.UUID, data: dict[str, Any]
    ) -> DocCheckConfig | None:
        """更新配置"""
        query = (
            update(DocCheckConfig)
            .where(DocCheckConfig.id == config_id)
            .values(**data)
            .returning(DocCheckConfig)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # ============ 校验主表操作 ============

    async def get_checks(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        doc_type: str | None = None,
        operator: str | None = None,
    ) -> tuple[list[SopAiCheckMain], int]:
        """获取校验列表"""
        query = select(SopAiCheckMain).where(SopAiCheckMain.is_deleted == False)

        if status:
            query = query.where(SopAiCheckMain.status == status)
        if doc_type:
            query = query.where(SopAiCheckMain.file_type == doc_type)
        if operator:
            query = query.where(SopAiCheckMain.operator == operator)

        count_query = select(func.count(SopAiCheckMain.id)).where(
            SopAiCheckMain.is_deleted == False
        )
        if status:
            count_query = count_query.where(SopAiCheckMain.status == status)
        if doc_type:
            count_query = count_query.where(SopAiCheckMain.file_type == doc_type)
        if operator:
            count_query = count_query.where(SopAiCheckMain.operator == operator)

        total = await self.session.scalar(count_query)
        query = query.offset(skip).limit(limit).order_by(SopAiCheckMain.created_at.desc())
        result = await self.session.execute(query)
        checks = list(result.scalars().all())
        return checks, total or 0

    async def get_check_by_id(
        self, check_id: uuid.UUID
    ) -> SopAiCheckMain | None:
        """获取校验详情"""
        query = (
            select(SopAiCheckMain)
            .options(selectinload(SopAiCheckMain.problems))
            .where(
                SopAiCheckMain.id == check_id,
                SopAiCheckMain.is_deleted == False,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_check_by_no(self, check_no: str) -> SopAiCheckMain | None:
        """根据单号获取校验"""
        query = (
            select(SopAiCheckMain)
            .options(selectinload(SopAiCheckMain.problems))
            .where(
                SopAiCheckMain.check_no == check_no,
                SopAiCheckMain.is_deleted == False,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_check(
        self, data: dict[str, Any]
    ) -> SopAiCheckMain:
        """创建校验"""
        import uuid
        # 确保 id 字段是有效的 UUID
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        check = SopAiCheckMain(**data)
        self.session.add(check)
        await self.session.flush()
        await self.session.refresh(check)
        return check

    async def update_check(
        self, check_id: uuid.UUID, data: dict[str, Any]
    ) -> SopAiCheckMain | None:
        """更新校验"""
        query = (
            update(SopAiCheckMain)
            .where(
                SopAiCheckMain.id == check_id,
                SopAiCheckMain.is_deleted == False,
            )
            .values(**data)
            .returning(SopAiCheckMain)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete_check(self, check_id: uuid.UUID) -> bool:
        """删除校验(软删除)"""
        query = (
            update(SopAiCheckMain)
            .where(
                SopAiCheckMain.id == check_id,
                SopAiCheckMain.is_deleted == False,
            )
            .values(is_deleted=True)
        )
        result = await self.session.execute(query)
        return result.rowcount > 0

    # ============ 问题明细操作 ============

    async def get_problems_by_check(
        self, check_main_id: uuid.UUID
    ) -> list[SopAiCheckProblem]:
        """获取校验问题列表"""
        query = (
            select(SopAiCheckProblem)
            .where(
                SopAiCheckProblem.check_main_id == check_main_id,
                SopAiCheckProblem.is_deleted == False,
            )
            .order_by(SopAiCheckProblem.problem_no)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_problem(
        self, data: dict[str, Any]
    ) -> SopAiCheckProblem:
        """创建问题"""
        problem = SopAiCheckProblem(**data)
        self.session.add(problem)
        await self.session.flush()
        await self.session.refresh(problem)
        return problem

    async def create_problems_bulk(
        self, check_main_id: uuid.UUID, problems_data: list[dict[str, Any]]
    ) -> list[SopAiCheckProblem]:
        """批量创建问题"""
        problems = []
        for prob_data in problems_data:
            problem = SopAiCheckProblem(check_main_id=check_main_id, **prob_data)
            self.session.add(problem)
            problems.append(problem)
        await self.session.flush()
        for problem in problems:
            await self.session.refresh(problem)
        return problems

    async def delete_problems_by_check(self, check_main_id: uuid.UUID) -> bool:
        """删除校验下的所有问题"""
        query = (
            update(SopAiCheckProblem)
            .where(SopAiCheckProblem.check_main_id == check_main_id)
            .values(is_deleted=True)
        )
        await self.session.execute(query)
        return True

    # ============ 向量缓存操作（暂时禁用，因数据库无此表）===========
    # TODO: 后续如需启用向量缓存功能，需创建 sop_ai_vector_cache 表
    #
    # async def get_vector_cache(
    #     self,
    #     doc_type: str | None = None,
    #     doc_hash: str | None = None,
    # ) -> list[DocCheckVectorCache]:
    #     """获取向量缓存列表"""
    #     ...
    #
    # async def get_vector_cache_by_doc(
    #     self, doc_type: str, doc_hash: str
    # ) -> DocCheckVectorCache | None:
    #     """根据文档类型和哈希获取向量缓存"""
    #     ...
    #
    # async def create_vector_cache(
    #     self, data: dict[str, Any]
    # ) -> DocCheckVectorCache:
    #     """创建向量缓存"""
    #     ...
    #
    # async def update_vector_cache(
    #     self, cache_id: uuid.UUID, data: dict[str, Any]
    # ) -> DocCheckVectorCache | None:
    #     """更新向量缓存"""
    #     ...
    #
    # async def increment_hit_count(self, cache_id: uuid.UUID) -> bool:
    #     """增加命中次数"""
    #     ...
    #
    # @staticmethod
    # def compute_doc_hash(doc_content: str) -> str:
    #     """计算文档哈希"""
    #     return hashlib.sha256(doc_content.encode("utf-8")).hexdigest()
    #
    # @staticmethod
    # def compute_simple_vector(
    #     doc_content: str, dimension: int = 1536
    # ) -> list[int]:
    #     """计算简易向量（仅用于占位，实际应使用embedding模型）"""
    #     ...

    @staticmethod
    def compute_doc_hash(doc_content: str) -> str:
        """计算文档哈希"""
        import hashlib
        return hashlib.sha256(doc_content.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_simple_vector(
        doc_content: str, dimension: int = 1536
    ) -> list[int]:
        """计算简易向量（仅用于占位，实际应使用embedding模型）

        当 pgvector 扩展未启用时，使用此方法生成占位向量。
        实际生产环境应调用 AI 服务获取真实 embedding。
        """
        import hashlib
        import random
        # 简单的基于内容的哈希分布生成伪向量
        hash_bytes = hashlib.md5(doc_content.encode("utf-8")).digest()
        hash_val = int.from_bytes(hash_bytes[:4], "big")
        # 生成伪随机但确定的向量
        random.seed(hash_val)
        return [random.randint(-128, 127) for _ in range(dimension)]