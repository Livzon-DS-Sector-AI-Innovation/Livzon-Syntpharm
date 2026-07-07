"""SOP AI 模块数据访问层

提供数据库操作的封装，包括配置、校验记录和问题明细的数据访问。
"""

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sop_ai.models import (
    SopAiConfig,
    SopAiCheckMain,
    SopAiCheckProblem,
    CheckStatus,
    HandleStatus,
)

logger = logging.getLogger(__name__)


class SopAiConfigRepository:
    """配置数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_key(self, config_key: str) -> Optional[SopAiConfig]:
        """根据键获取配置"""
        result = await self.session.execute(
            select(SopAiConfig).where(SopAiConfig.config_key == config_key)
        )
        return result.scalars().first()

    async def get_all(self) -> list[SopAiConfig]:
        """获取所有配置"""
        result = await self.session.execute(
            select(SopAiConfig).order_by(SopAiConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        config_key: str,
        config_value: str,
        description: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> SopAiConfig:
        """创建配置"""
        config = SopAiConfig(
            config_key=config_key,
            config_value=config_value,
            description=description,
            operator=operator,
        )
        self.session.add(config)
        await self.session.flush()
        return config

    async def update(
        self,
        config_key: str,
        config_value: str,
        description: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> Optional[SopAiConfig]:
        """更新配置"""
        config = await self.get_by_key(config_key)
        if config:
            config.config_value = config_value
            if description is not None:
                config.description = description
            if operator is not None:
                config.operator = operator
            config.updated_at = datetime.now()
            await self.session.flush()
        return config

    async def upsert(
        self,
        config_key: str,
        config_value: str,
        description: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> SopAiConfig:
        """创建或更新配置"""
        config = await self.get_by_key(config_key)
        if config:
            return await self.update(config_key, config_value, description, operator)
        return await self.create(config_key, config_value, description, operator)


class SopAiCheckMainRepository:
    """校验主表数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: str) -> Optional[SopAiCheckMain]:
        """根据ID获取记录"""
        result = await self.session.execute(
            select(SopAiCheckMain).where(SopAiCheckMain.id == id)
        )
        return result.scalars().first()

    async def get_by_file_code(self, file_code: str) -> Optional[SopAiCheckMain]:
        """根据文件编号获取记录"""
        result = await self.session.execute(
            select(SopAiCheckMain).where(SopAiCheckMain.file_code == file_code)
        )
        return result.scalars().first()

    async def list(
        self,
        status: Optional[str] = None,
        file_code: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SopAiCheckMain], int]:
        """查询列表"""
        conditions = []

        if status:
            conditions.append(SopAiCheckMain.status == status)
        if file_code:
            conditions.append(SopAiCheckMain.file_code.like(f"%{file_code}%"))
        if start_date:
            conditions.append(SopAiCheckMain.created_at >= start_date)
        if end_date:
            conditions.append(SopAiCheckMain.created_at <= end_date)

        where_clause = and_(*conditions) if conditions else True

        # 查询语句
        query = (
            select(SopAiCheckMain)
            .where(where_clause)
            .order_by(SopAiCheckMain.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        # 统计语句
        count_query = select(func.count()).select_from(SopAiCheckMain).where(where_clause)

        result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)

        items = list(result.scalars().all())
        total = total_result.scalar() or 0

        return items, total

    async def create(
        self,
        file_code: Optional[str] = None,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
        check_type: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> SopAiCheckMain:
        """创建记录"""
        record = SopAiCheckMain(
            file_code=file_code,
            file_name=file_name,
            file_type=file_type,
            check_type=check_type,
            status=CheckStatus.PENDING,
            operator=operator,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def update_status(
        self,
        id: str,
        status: CheckStatus,
        result_summary: Optional[str] = None,
    ) -> Optional[SopAiCheckMain]:
        """更新状态"""
        record = await self.get_by_id(id)
        if record:
            record.status = status
            if result_summary is not None:
                record.result_summary = result_summary
            record.updated_at = datetime.now()
            await self.session.flush()
        return record

    async def update_result(
        self,
        id: str,
        result_summary: Optional[str] = None,
        total_problems: int = 0,
        risk_high: int = 0,
        risk_medium: int = 0,
        risk_low: int = 0,
    ) -> Optional[SopAiCheckMain]:
        """更新结果汇总"""
        record = await self.get_by_id(id)
        if record:
            if result_summary is not None:
                record.result_summary = result_summary
            record.total_problems = total_problems
            record.risk_high = risk_high
            record.risk_medium = risk_medium
            record.risk_low = risk_low
            record.updated_at = datetime.now()
            await self.session.flush()
        return record


class SopAiCheckProblemRepository:
    """问题明细数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: str) -> Optional[SopAiCheckProblem]:
        """根据ID获取问题"""
        result = await self.session.execute(
            select(SopAiCheckProblem).where(SopAiCheckProblem.id == id)
        )
        return result.scalars().first()

    async def get_by_main_id(self, main_id: str) -> list[SopAiCheckProblem]:
        """根据主记录ID获取问题列表"""
        result = await self.session.execute(
            select(SopAiCheckProblem)
            .where(SopAiCheckProblem.main_id == main_id)
            .order_by(
                # 高风险优先
                SopAiCheckProblem.risk_level.desc(),
                SopAiCheckProblem.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def create(
        self,
        main_id: str,
        problem_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        source_file: Optional[str] = None,
        suggestion: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> SopAiCheckProblem:
        """创建问题记录"""
        problem = SopAiCheckProblem(
            main_id=main_id,
            problem_type=problem_type,
            risk_level=risk_level,
            location=location,
            description=description,
            source_file=source_file,
            suggestion=suggestion,
            handle_status=HandleStatus.PENDING,
            operator=operator,
        )
        self.session.add(problem)
        await self.session.flush()
        return problem

    async def create_batch(
        self,
        problems_data: list[dict],
    ) -> list[SopAiCheckProblem]:
        """批量创建问题"""
        problems = []
        for data in problems_data:
            problem = SopAiCheckProblem(
                main_id=data["main_id"],
                problem_type=data.get("problem_type"),
                risk_level=data.get("risk_level"),
                location=data.get("location"),
                description=data.get("description"),
                source_file=data.get("source_file"),
                suggestion=data.get("suggestion"),
                handle_status=HandleStatus.PENDING,
                operator=data.get("operator"),
            )
            self.session.add(problem)
            problems.append(problem)

        await self.session.flush()
        return problems

    async def update_handle_status(
        self,
        id: str,
        handle_status: HandleStatus,
        ignore_reason: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> Optional[SopAiCheckProblem]:
        """更新处理状态"""
        problem = await self.get_by_id(id)
        if problem:
            problem.handle_status = handle_status
            if ignore_reason is not None:
                problem.ignore_reason = ignore_reason
            if operator is not None:
                problem.operator = operator
            problem.updated_at = datetime.now()
            await self.session.flush()
        return problem

    async def count_by_main_id(self, main_id: str) -> dict:
        """统计问题数量"""
        result = await self.session.execute(
            select(
                func.count().label("total"),
                func.sum(
                    func.case(
                        (SopAiCheckProblem.risk_level == "high", 1), else_=0
                    )
                ).label("high"),
                func.sum(
                    func.case(
                        (SopAiCheckProblem.risk_level == "medium", 1), else_=0
                    )
                ).label("medium"),
                func.sum(
                    func.case(
                        (SopAiCheckProblem.risk_level == "low", 1), else_=0
                    )
                ).label("low"),
            )
            .where(SopAiCheckProblem.main_id == main_id)
        )
        row = result.first()
        return {
            "total": row.total or 0,
            "high": row.high or 0,
            "medium": row.medium or 0,
            "low": row.low or 0,
        }