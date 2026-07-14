"""Instrument Calibration Repository (仪器校准管理数据访问层)

提供仪器设备台账、校准规则配置、校准记录、审批记录的数据库操作
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.quality.qms.instrument_models import (
    CalibrationReminderConfig,
    InstrumentCalibration,
    InstrumentCalibrationApproval,
    InstrumentCalibrationRecord,
    InstrumentCalibrationRule,
)


class InstrumentRepository:
    """仪器设备Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, instrument_data: dict[str, Any]) -> InstrumentCalibration:
        """创建仪器"""
        instrument = InstrumentCalibration(**instrument_data)
        self.session.add(instrument)
        await self.session.flush()
        await self.session.refresh(instrument)
        return instrument

    async def get_by_id(self, instrument_id: UUID) -> InstrumentCalibration | None:
        """根据ID获取仪器"""
        result = await self.session.execute(
            select(InstrumentCalibration).where(
                and_(
                    InstrumentCalibration.id == instrument_id,
                    ~InstrumentCalibration.is_deleted,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_no(self, instrument_no: str) -> InstrumentCalibration | None:
        """根据编号获取仪器"""
        result = await self.session.execute(
            select(InstrumentCalibration).where(
                and_(
                    InstrumentCalibration.instrument_no == instrument_no,
                    ~InstrumentCalibration.is_deleted,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(self, instrument_id: UUID, update_data: dict[str, Any]) -> InstrumentCalibration | None:
        """更新仪器"""
        update_data["updated_at"] = datetime.now()
        await self.session.execute(
            update(InstrumentCalibration).where(InstrumentCalibration.id == instrument_id).values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_id(instrument_id)

    async def delete(self, instrument_id: UUID) -> bool:
        """删除仪器"""
        await self.session.execute(
            update(InstrumentCalibration)
            .where(InstrumentCalibration.id == instrument_id)
            .values(is_deleted=True, updated_at=datetime.now())
        )
        await self.session.flush()
        return True

    async def list_with_filter(
        self,
        instrument_no: str | None = None,
        instrument_name: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        status: str | None = None,
        is_overdue: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[InstrumentCalibration], int]:
        """带筛选条件的列表查询"""
        # 构建基础查询
        query = select(InstrumentCalibration).where(~InstrumentCalibration.is_deleted)

        # 添加筛选条件
        if instrument_no:
            query = query.where(InstrumentCalibration.instrument_no.ilike(f"%{instrument_no}%"))
        if instrument_name:
            query = query.where(InstrumentCalibration.instrument_name.ilike(f"%{instrument_name}%"))
        if category:
            query = query.where(InstrumentCalibration.category == category)
        if is_active is not None:
            query = query.where(InstrumentCalibration.is_active == is_active)
        if status:
            query = query.where(InstrumentCalibration.status == status)

        # 查询总数
        count_result = await self.session.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        # 分页查询
        query = query.order_by(InstrumentCalibration.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        instruments = result.scalars().all()

        return list(instruments), total  # type: ignore[return-value]

    async def get_overdue_instruments(self) -> list[InstrumentCalibration]:
        """获取已超期仪器"""
        now = datetime.now()
        # 子查询：获取有校准规则且下次校准日期已过期的仪器
        subquery = (
            select(InstrumentCalibrationRule.instrument_id).where(
                and_(
                    InstrumentCalibrationRule.is_active,
                    InstrumentCalibrationRule.next_calibration_date < now,
                )
            )
        ).distinct()

        result = await self.session.execute(
            select(InstrumentCalibration).where(
                and_(
                    ~InstrumentCalibration.is_deleted,
                    InstrumentCalibration.is_active,
                    InstrumentCalibration.id.in_(subquery),
                )
            )
        )
        return list(result.scalars().all())


class CalibrationRuleRepository:
    """校准规则Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, rule_data: dict[str, Any]) -> InstrumentCalibrationRule:
        """创建校准规则"""
        rule = InstrumentCalibrationRule(**rule_data)
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def get_by_id(self, rule_id: UUID) -> InstrumentCalibrationRule | None:
        """根据ID获取规则"""
        result = await self.session.execute(
            select(InstrumentCalibrationRule).where(InstrumentCalibrationRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_by_instrument_id(self, instrument_id: UUID) -> InstrumentCalibrationRule | None:
        """根据仪器ID获取规则"""
        result = await self.session.execute(
            select(InstrumentCalibrationRule).where(
                and_(
                    InstrumentCalibrationRule.instrument_id == instrument_id,
                    InstrumentCalibrationRule.is_active,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(self, rule_id: UUID, update_data: dict[str, Any]) -> InstrumentCalibrationRule | None:
        """更新规则"""
        update_data["updated_at"] = datetime.now()
        await self.session.execute(
            update(InstrumentCalibrationRule).where(InstrumentCalibrationRule.id == rule_id).values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_id(rule_id)

    async def delete(self, rule_id: UUID) -> bool:
        """删除规则"""
        await self.session.execute(
            update(InstrumentCalibrationRule)
            .where(InstrumentCalibrationRule.id == rule_id)
            .values(is_active=False, updated_at=datetime.now())
        )
        await self.session.flush()
        return True

    async def get_upcoming_calibrations(self, days: int = 30) -> list[InstrumentCalibrationRule]:
        """获取即将到期的校准计划"""
        now = datetime.now()
        from datetime import timedelta

        future_date = now + timedelta(days=days)

        result = await self.session.execute(
            select(InstrumentCalibrationRule)
            .options(selectinload(InstrumentCalibrationRule.instrument))
            .where(
                and_(
                    InstrumentCalibrationRule.is_active,
                    InstrumentCalibrationRule.next_calibration_date.isnot(None),
                    InstrumentCalibrationRule.next_calibration_date <= future_date,
                )
            )
            .order_by(InstrumentCalibrationRule.next_calibration_date)
        )
        return list(result.scalars().all())

    async def list_by_instrument(self, instrument_id: str | UUID | None = None) -> list[InstrumentCalibrationRule]:
        """根据仪器ID获取校准规则列表"""
        query = select(InstrumentCalibrationRule).where(InstrumentCalibrationRule.is_active)

        if instrument_id:
            if isinstance(instrument_id, str):
                try:
                    instrument_id = UUID(instrument_id)
                except ValueError:
                    pass
            if isinstance(instrument_id, UUID):
                query = query.where(InstrumentCalibrationRule.instrument_id == instrument_id)

        query = query.order_by(InstrumentCalibrationRule.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())


class CalibrationRecordRepository:
    """校准记录Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, record_data: dict[str, Any]) -> InstrumentCalibrationRecord:
        """创建校准记录"""
        record = InstrumentCalibrationRecord(**record_data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get_by_id(self, record_id: UUID) -> InstrumentCalibrationRecord | None:
        """根据ID获取记录"""
        result = await self.session.execute(
            select(InstrumentCalibrationRecord).where(
                and_(
                    InstrumentCalibrationRecord.id == record_id,
                    ~InstrumentCalibrationRecord.is_deleted,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_no(self, calibration_no: str) -> InstrumentCalibrationRecord | None:
        """根据编号获取记录"""
        result = await self.session.execute(
            select(InstrumentCalibrationRecord).where(
                and_(
                    InstrumentCalibrationRecord.calibration_no == calibration_no,
                    ~InstrumentCalibrationRecord.is_deleted,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(self, record_id: UUID, update_data: dict[str, Any]) -> InstrumentCalibrationRecord | None:
        """更新记录"""
        update_data["updated_at"] = datetime.now()
        await self.session.execute(
            update(InstrumentCalibrationRecord).where(InstrumentCalibrationRecord.id == record_id).values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_id(record_id)

    async def delete(self, record_id: UUID) -> bool:
        """删除记录"""
        await self.session.execute(
            update(InstrumentCalibrationRecord)
            .where(InstrumentCalibrationRecord.id == record_id)
            .values(is_deleted=True, updated_at=datetime.now())
        )
        await self.session.flush()
        return True

    async def list_with_filter(
        self,
        instrument_id: str | UUID | None = None,
        rule_id: str | UUID | None = None,
        calibration_no: str | None = None,
        calibration_result: str | None = None,
        status: str | None = None,
        calibration_method: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[InstrumentCalibrationRecord], int]:
        """带筛选条件的列表查询"""
        # 构建基础查询
        query = select(InstrumentCalibrationRecord).where(~InstrumentCalibrationRecord.is_deleted)

        # 添加筛选条件
        if instrument_id:
            # 支持字符串或UUID格式的instrument_id
            if isinstance(instrument_id, str):
                try:
                    instrument_id = UUID(instrument_id)
                except ValueError:
                    pass  # 无效UUID，跳过此条件
            if isinstance(instrument_id, UUID):
                query = query.where(InstrumentCalibrationRecord.instrument_id == instrument_id)
        if rule_id:
            # 支持字符串或UUID格式的rule_id
            if isinstance(rule_id, str):
                try:
                    rule_id = UUID(rule_id)
                except ValueError:
                    pass  # 无效UUID，跳过此条件
            if isinstance(rule_id, UUID):
                query = query.where(InstrumentCalibrationRecord.rule_id == rule_id)
        if calibration_no:
            query = query.where(InstrumentCalibrationRecord.calibration_no.ilike(f"%{calibration_no}%"))
        if calibration_result:
            query = query.where(InstrumentCalibrationRecord.calibration_result == calibration_result)
        if status:
            query = query.where(InstrumentCalibrationRecord.status == status)
        if calibration_method:
            query = query.where(InstrumentCalibrationRecord.calibration_method == calibration_method)
        if start_date:
            query = query.where(InstrumentCalibrationRecord.calibration_date >= start_date)
        if end_date:
            query = query.where(InstrumentCalibrationRecord.calibration_date <= end_date)

        # 查询总数
        count_result = await self.session.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        # 分页查询
        query = query.order_by(InstrumentCalibrationRecord.calibration_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        records = result.scalars().all()

        return list(records), total  # type: ignore[return-value]

    async def get_latest_by_instrument(self, instrument_id: UUID) -> InstrumentCalibrationRecord | None:
        """获取仪器最新校准记录（按calibration_date降序取最新的）"""
        result = await self.session.execute(
            select(InstrumentCalibrationRecord)
            .where(
                and_(
                    InstrumentCalibrationRecord.instrument_id == instrument_id,
                    ~InstrumentCalibrationRecord.is_deleted,
                    InstrumentCalibrationRecord.calibration_result == "qualified",  # 只查询合格记录
                )
            )
            .order_by(InstrumentCalibrationRecord.calibration_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_upcoming_records(self, days: int = 30) -> list[InstrumentCalibrationRecord]:
        """获取即将到期的校准记录（只返回每个仪器的最新校准记录）"""
        from datetime import timedelta

        # 使用 UTC 时间以匹配数据库存储格式
        now = datetime.now(UTC)
        future_date = now + timedelta(days=days)

        # 首先获取所有仪器的最新合格校准记录
        subquery = (
            select(
                InstrumentCalibrationRecord.instrument_id,
                func.max(InstrumentCalibrationRecord.calibration_date).label("max_date"),
            )
            .where(
                and_(
                    ~InstrumentCalibrationRecord.is_deleted,
                    InstrumentCalibrationRecord.calibration_result == "qualified",
                )
            )
            .group_by(InstrumentCalibrationRecord.instrument_id)
            .subquery()
        )

        # 查询每个仪器的最新校准记录中即将到期的
        result = await self.session.execute(
            select(InstrumentCalibrationRecord)
            .options(selectinload(InstrumentCalibrationRecord.instrument))
            .join(
                subquery,
                and_(
                    InstrumentCalibrationRecord.instrument_id == subquery.c.instrument_id,
                    InstrumentCalibrationRecord.calibration_date == subquery.c.max_date,
                ),
            )
            .where(
                and_(
                    ~InstrumentCalibrationRecord.is_deleted,
                    InstrumentCalibrationRecord.calibration_result == "qualified",
                    InstrumentCalibrationRecord.valid_until.isnot(None),
                    InstrumentCalibrationRecord.valid_until >= now,
                    InstrumentCalibrationRecord.valid_until <= future_date,
                )
            )
            .order_by(InstrumentCalibrationRecord.valid_until)
        )
        return list(result.scalars().all())

    async def get_overdue_records(self) -> list[InstrumentCalibrationRecord]:
        """获取已超期的校准记录（只返回每个仪器的最新校准记录）"""

        now = datetime.now(UTC)

        # 首先获取所有仪器的最新合格校准记录
        subquery = (
            select(
                InstrumentCalibrationRecord.instrument_id,
                func.max(InstrumentCalibrationRecord.calibration_date).label("max_date"),
            )
            .where(
                and_(
                    ~InstrumentCalibrationRecord.is_deleted,
                    InstrumentCalibrationRecord.calibration_result == "qualified",
                )
            )
            .group_by(InstrumentCalibrationRecord.instrument_id)
            .subquery()
        )

        # 查询每个仪器的最新校准记录中已超期的
        result = await self.session.execute(
            select(InstrumentCalibrationRecord)
            .options(selectinload(InstrumentCalibrationRecord.instrument))
            .join(
                subquery,
                and_(
                    InstrumentCalibrationRecord.instrument_id == subquery.c.instrument_id,
                    InstrumentCalibrationRecord.calibration_date == subquery.c.max_date,
                ),
            )
            .where(
                and_(
                    ~InstrumentCalibrationRecord.is_deleted,
                    InstrumentCalibrationRecord.calibration_result == "qualified",
                    InstrumentCalibrationRecord.valid_until.isnot(None),
                    InstrumentCalibrationRecord.valid_until < now,
                )
            )
            .order_by(InstrumentCalibrationRecord.valid_until)
        )
        return list(result.scalars().all())


class CalibrationApprovalRepository:
    """审批记录Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, approval_data: dict[str, Any]) -> InstrumentCalibrationApproval:
        """创建审批记录"""
        approval = InstrumentCalibrationApproval(**approval_data)
        self.session.add(approval)
        await self.session.flush()
        await self.session.refresh(approval)
        return approval

    async def get_by_id(self, approval_id: UUID) -> InstrumentCalibrationApproval | None:
        """根据ID获取审批记录"""
        result = await self.session.execute(
            select(InstrumentCalibrationApproval).where(InstrumentCalibrationApproval.id == approval_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_approvals(self, related_type: str, related_id: UUID) -> list[InstrumentCalibrationApproval]:
        """获取待审批记录"""
        result = await self.session.execute(
            select(InstrumentCalibrationApproval)
            .where(
                and_(
                    InstrumentCalibrationApproval.related_type == related_type,
                    InstrumentCalibrationApproval.related_id == related_id,
                    InstrumentCalibrationApproval.status == "pending",
                )
            )
            .order_by(InstrumentCalibrationApproval.sequence)
        )
        return list(result.scalars().all())

    async def update(self, approval_id: UUID, update_data: dict[str, Any]) -> InstrumentCalibrationApproval | None:
        """更新审批记录"""
        update_data["updated_at"] = datetime.now()
        await self.session.execute(
            update(InstrumentCalibrationApproval)
            .where(InstrumentCalibrationApproval.id == approval_id)
            .values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_id(approval_id)


class ReminderConfigRepository:
    """提醒配置Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, config_data: dict[str, Any]) -> CalibrationReminderConfig:
        """创建提醒配置"""
        config = CalibrationReminderConfig(**config_data)
        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def get_by_id(self, config_id: UUID) -> CalibrationReminderConfig | None:
        """根据ID获取配置"""
        result = await self.session.execute(
            select(CalibrationReminderConfig).where(CalibrationReminderConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[CalibrationReminderConfig]:
        """获取所有配置"""
        result = await self.session.execute(
            select(CalibrationReminderConfig).order_by(CalibrationReminderConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active(self) -> list[CalibrationReminderConfig]:
        """获取所有启用的配置"""
        result = await self.session.execute(
            select(CalibrationReminderConfig)
            .where(CalibrationReminderConfig.is_active)
            .order_by(CalibrationReminderConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, config_id: UUID, update_data: dict[str, Any]) -> CalibrationReminderConfig | None:
        """更新配置"""
        update_data["updated_at"] = datetime.now()
        await self.session.execute(
            update(CalibrationReminderConfig).where(CalibrationReminderConfig.id == config_id).values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_id(config_id)

    async def delete(self, config_id: UUID) -> bool:
        """删除配置"""
        await self.session.execute(
            update(CalibrationReminderConfig)
            .where(CalibrationReminderConfig.id == config_id)
            .values(is_active=False, updated_at=datetime.now())
        )
        await self.session.flush()
        return True
