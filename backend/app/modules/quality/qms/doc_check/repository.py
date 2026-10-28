"""Doc Check 模块数据访问层

复用 sop_ai 模块的三张表：sop_ai_config / sop_ai_check_main / sop_ai_check_problem。
"""

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.quality.sop_ai.models import (
    SopAiCheckMain,
    SopAiCheckProblem,
)
from app.modules.quality.sop_ai.models import (
    SopAiConfig as DocCheckConfig,
)


class DocCheckRepository:
    """Doc Check 模块仓库"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ============ 配置操作 ============

    async def get_configs(self) -> list[DocCheckConfig]:
        """获取配置列表"""
        query = (
            select(DocCheckConfig)
            .where(DocCheckConfig.is_deleted.is_(False))
            .order_by(DocCheckConfig.sort_order, DocCheckConfig.config_key)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_config_by_id(self, config_id: str) -> DocCheckConfig | None:
        """根据主键获取配置"""
        query = select(DocCheckConfig).where(
            DocCheckConfig.id == config_id,
            DocCheckConfig.is_deleted.is_(False),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_config_by_key(self, config_key: str) -> DocCheckConfig | None:
        """根据配置键获取配置"""
        query = select(DocCheckConfig).where(
            DocCheckConfig.config_key == config_key,
            DocCheckConfig.is_deleted.is_(False),
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

    async def update_config(self, config_id: str, data: dict[str, Any]) -> DocCheckConfig | None:
        """更新配置

        直接改写已加载的 ORM 对象，避免 UPDATE ... RETURNING 命中身份映射时返回旧值。
        """
        config = await self.get_config_by_id(config_id)
        if config is None:
            return None
        for key, value in data.items():
            setattr(config, key, value)
        await self.session.flush()
        return config

    # ============ 校验主表操作 ============

    async def get_checks(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        file_type: str | None = None,
        operator: str | None = None,
    ) -> tuple[list[SopAiCheckMain], int]:
        """获取校验列表"""
        conditions = [SopAiCheckMain.is_deleted.is_(False)]
        if status:
            conditions.append(SopAiCheckMain.status == status)
        if file_type:
            conditions.append(SopAiCheckMain.file_type == file_type)
        if operator:
            conditions.append(SopAiCheckMain.operator == operator)

        count_query = select(func.count(SopAiCheckMain.id)).where(*conditions)
        total = await self.session.scalar(count_query)

        query = (
            select(SopAiCheckMain)
            .where(*conditions)
            .order_by(SopAiCheckMain.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_check_by_id(self, check_id: str) -> SopAiCheckMain | None:
        """获取校验详情（含问题明细）"""
        query = (
            select(SopAiCheckMain)
            .options(selectinload(SopAiCheckMain.problems))
            .where(
                SopAiCheckMain.id == check_id,
                SopAiCheckMain.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_check(self, data: dict[str, Any]) -> SopAiCheckMain:
        """创建校验任务"""
        payload = dict(data)
        payload.setdefault("id", str(uuid.uuid4()))
        check = SopAiCheckMain(**payload)
        self.session.add(check)
        await self.session.flush()
        await self.session.refresh(check)
        return check

    async def update_check(self, check_id: str, data: dict[str, Any]) -> SopAiCheckMain | None:
        """更新校验任务（改写已加载对象，保证返回值是最新值）"""
        check = await self.get_check_by_id(check_id)
        if check is None:
            return None
        for key, value in data.items():
            setattr(check, key, value)
        await self.session.flush()
        return check

    async def delete_check(self, check_id: str) -> bool:
        """删除校验任务（软删除）"""
        query = (
            update(SopAiCheckMain)
            .where(
                SopAiCheckMain.id == check_id,
                SopAiCheckMain.is_deleted.is_(False),
            )
            .values(is_deleted=True)
            .returning(SopAiCheckMain.id)
        )
        result = await self.session.execute(query)
        return result.first() is not None

    # ============ 问题明细操作 ============

    async def get_problems_by_check(self, main_id: str) -> list[SopAiCheckProblem]:
        """获取校验任务下的问题列表"""
        query = (
            select(SopAiCheckProblem)
            .where(
                SopAiCheckProblem.main_id == main_id,
                SopAiCheckProblem.is_deleted.is_(False),
            )
            .order_by(SopAiCheckProblem.created_at)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_problem_by_id(self, problem_id: str) -> SopAiCheckProblem | None:
        """获取单条问题"""
        query = select(SopAiCheckProblem).where(
            SopAiCheckProblem.id == problem_id,
            SopAiCheckProblem.is_deleted.is_(False),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_problems_bulk(
        self,
        main_id: str,
        problems_data: list[dict[str, Any]],
    ) -> list[SopAiCheckProblem]:
        """批量创建问题"""
        problems = [SopAiCheckProblem(main_id=main_id, **item) for item in problems_data]
        self.session.add_all(problems)
        await self.session.flush()
        return problems

    async def soft_delete_problems_by_check(self, main_id: str) -> None:
        """软删除校验任务下的全部问题"""
        query = (
            update(SopAiCheckProblem)
            .where(
                SopAiCheckProblem.main_id == main_id,
                SopAiCheckProblem.is_deleted.is_(False),
            )
            .values(is_deleted=True)
        )
        await self.session.execute(query)

    async def update_problem(self, problem_id: str, data: dict[str, Any]) -> SopAiCheckProblem | None:
        """更新单条问题（改写已加载对象，保证返回值是最新值）"""
        problem = await self.get_problem_by_id(problem_id)
        if problem is None:
            return None
        for key, value in data.items():
            setattr(problem, key, value)
        await self.session.flush()
        return problem
