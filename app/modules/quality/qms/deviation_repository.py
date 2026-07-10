"""偏差管理 Repository"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.quality.qms.deviation_models import (
    Deviation,
    DeviationApproval,
    DeviationClosing,
    DeviationCorrection,
    DeviationInvestigation,
)


class DeviationRepository:
    """偏差 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Deviation:
        """创建偏差"""
        deviation = Deviation(**data)
        self.session.add(deviation)
        await self.session.flush()
        await self.session.refresh(deviation)
        return deviation

    async def get_by_id(self, deviation_id: UUID) -> Deviation | None:
        """获取偏差详情"""
        result = await self.session.execute(
            select(Deviation)
            .options(
                selectinload(Deviation.investigation),
                selectinload(Deviation.correction),
                selectinload(Deviation.closing),
                selectinload(Deviation.approvals),
            )
            .where(Deviation.id == deviation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_no(self, deviation_no: str) -> Deviation | None:
        """通过编号获取偏差"""
        result = await self.session.execute(
            select(Deviation).where(Deviation.deviation_no == deviation_no)
        )
        return result.scalar_one_or_none()

    async def update(self, deviation_id: UUID, data: dict) -> Deviation | None:
        """更新偏差"""
        deviation = await self.get_by_id(deviation_id)
        if not deviation:
            return None

        for key, value in data.items():
            if hasattr(deviation, key):
                setattr(deviation, key, value)

        await self.session.flush()
        await self.session.refresh(deviation)
        return deviation

    async def delete(self, deviation_id: UUID) -> bool:
        """删除偏差"""
        deviation = await self.get_by_id(deviation_id)
        if not deviation:
            return False
        await self.session.delete(deviation)
        return True

    async def list_with_filter(
        self,
        deviation_no: str | None = None,
        deviation_type: str | None = None,
        deviation_level: str | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_batch: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Deviation], int]:
        """带筛选条件的列表查询"""
        query = select(Deviation).options(
            selectinload(Deviation.investigation),
            selectinload(Deviation.correction),
            selectinload(Deviation.closing),
        )

        conditions = []
        if deviation_no:
            conditions.append(Deviation.deviation_no.ilike(f"%{deviation_no}%"))
        if deviation_type:
            conditions.append(Deviation.deviation_type == deviation_type)
        if deviation_level:
            conditions.append(Deviation.deviation_level == deviation_level)
        if status:
            conditions.append(Deviation.status == status)
        if start_date:
            conditions.append(Deviation.occurrence_date >= start_date)
        if end_date:
            conditions.append(Deviation.occurrence_date <= end_date)
        if product_batch:
            conditions.append(Deviation.production_batch.ilike(f"%{product_batch}%"))
        if department:
            conditions.append(Deviation.discovering_department.ilike(f"%{department}%"))

        if conditions:
            query = query.where(and_(*conditions))

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # 分页
        query = query.order_by(Deviation.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        deviations = list(result.scalars().all())

        return deviations, total

    async def get_statistics(self) -> dict:
        """获取统计数据"""
        # 总数
        total_result = await self.session.execute(
            select(func.count()).select_from(Deviation)
        )
        total = total_result.scalar()

        # 按类型统计
        type_result = await self.session.execute(
            select(Deviation.deviation_type, func.count()).group_by(
                Deviation.deviation_type
            )
        )
        by_type = {row[0]: row[1] for row in type_result.all()}

        # 按等级统计
        level_result = await self.session.execute(
            select(Deviation.deviation_level, func.count()).group_by(
                Deviation.deviation_level
            )
        )
        by_level = {row[0]: row[1] for row in level_result.all()}

        # 按状态统计
        status_result = await self.session.execute(
            select(Deviation.status, func.count()).group_by(Deviation.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        return {
            "total_count": total,
            "by_type": by_type,
            "by_level": by_level,
            "by_status": by_status,
            "monthly_trend": [],
        }


class InvestigationRepository:
    """偏差调查 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, deviation_id: UUID, data: dict) -> DeviationInvestigation:
        """创建调查"""
        investigation = DeviationInvestigation(deviation_id=deviation_id, **data)
        self.session.add(investigation)
        await self.session.flush()
        await self.session.refresh(investigation)
        return investigation

    async def get_by_deviation_id(
        self, deviation_id: UUID
    ) -> DeviationInvestigation | None:
        """通过偏差ID获取调查"""
        result = await self.session.execute(
            select(DeviationInvestigation).where(
                DeviationInvestigation.deviation_id == deviation_id
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self, deviation_id: UUID, data: dict
    ) -> DeviationInvestigation | None:
        """更新调查"""
        investigation = await self.get_by_deviation_id(deviation_id)
        if not investigation:
            return None

        for key, value in data.items():
            if hasattr(investigation, key):
                setattr(investigation, key, value)

        await self.session.flush()
        await self.session.refresh(investigation)
        return investigation

    async def list_pending(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DeviationInvestigation], int]:
        """待调查列表"""
        query = (
            select(DeviationInvestigation)
            .options(selectinload(DeviationInvestigation.deviation))
            .where(DeviationInvestigation.status.in_(["pending", "in_progress"]))
        )

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        query = query.order_by(DeviationInvestigation.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        investigations = list(result.scalars().all())

        return investigations, total


class CorrectionRepository:
    """偏差整改 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _parse_date(self, value):
        """解析日期，支持字符串和date格式"""
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            # datetime.date 或 datetime.datetime 对象，转换为 datetime
            from datetime import datetime

            if isinstance(value, datetime):
                return value
            return datetime.combine(value, datetime.min.time())
        if isinstance(value, str):
            # 字符串格式转换为 datetime
            from datetime import datetime

            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return value

    async def create(self, deviation_id: UUID, data: dict) -> DeviationCorrection:
        """创建整改"""
        # 处理日期字段
        if "plan_completion_date" in data:
            data["plan_completion_date"] = self._parse_date(
                data["plan_completion_date"]
            )

        correction = DeviationCorrection(deviation_id=deviation_id, **data)
        self.session.add(correction)
        await self.session.flush()
        await self.session.refresh(correction)
        return correction

    async def get_by_deviation_id(
        self, deviation_id: UUID
    ) -> DeviationCorrection | None:
        """通过偏差ID获取整改"""
        result = await self.session.execute(
            select(DeviationCorrection).where(
                DeviationCorrection.deviation_id == deviation_id
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self, deviation_id: UUID, data: dict
    ) -> DeviationCorrection | None:
        """更新整改"""
        correction = await self.get_by_deviation_id(deviation_id)
        if not correction:
            return None

        # 处理日期字段
        if "plan_completion_date" in data:
            data["plan_completion_date"] = self._parse_date(
                data["plan_completion_date"]
            )

        for key, value in data.items():
            if hasattr(correction, key):
                setattr(correction, key, value)

        await self.session.flush()
        await self.session.refresh(correction)
        return correction

    async def list_pending(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DeviationCorrection], int]:
        """待整改列表"""
        query = (
            select(DeviationCorrection)
            .options(selectinload(DeviationCorrection.deviation))
            .where(DeviationCorrection.status.in_(["pending", "in_progress"]))
        )

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        query = query.order_by(DeviationCorrection.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        corrections = list(result.scalars().all())

        return corrections, total


class ClosingRepository:
    """偏差关闭 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, deviation_id: UUID, data: dict) -> DeviationClosing:
        """创建关闭"""
        closing = DeviationClosing(deviation_id=deviation_id, **data)
        self.session.add(closing)
        await self.session.flush()
        await self.session.refresh(closing)
        return closing

    async def get_by_deviation_id(self, deviation_id: UUID) -> DeviationClosing | None:
        """通过偏差ID获取关闭"""
        result = await self.session.execute(
            select(DeviationClosing).where(
                DeviationClosing.deviation_id == deviation_id
            )
        )
        return result.scalar_one_or_none()

    async def update(self, deviation_id: UUID, data: dict) -> DeviationClosing | None:
        """更新关闭"""
        closing = await self.get_by_deviation_id(deviation_id)
        if not closing:
            return None

        for key, value in data.items():
            if hasattr(closing, key):
                setattr(closing, key, value)

        await self.session.flush()
        await self.session.refresh(closing)
        return closing

    async def list_pending(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DeviationClosing], int]:
        """待关闭列表"""
        query = select(DeviationClosing).options(
            selectinload(DeviationClosing.deviation)
        )

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        query = query.order_by(DeviationClosing.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        closings = list(result.scalars().all())

        return closings, total


class ApprovalRepository:
    """偏差审批 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> DeviationApproval:
        """创建审批记录"""
        approval = DeviationApproval(**data)
        self.session.add(approval)
        await self.session.flush()
        await self.session.refresh(approval)
        return approval

    async def get_by_deviation_id(self, deviation_id: UUID) -> list[DeviationApproval]:
        """获取偏差的所有审批记录"""
        result = await self.session.execute(
            select(DeviationApproval)
            .where(DeviationApproval.deviation_id == deviation_id)
            .order_by(DeviationApproval.created_at)
        )
        return list(result.scalars().all())
