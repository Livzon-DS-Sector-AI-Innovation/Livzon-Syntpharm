"""原料报告单 Repository"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.quality.qms.material_report_models import (
    MaterialReport,
    MaterialReportItem,
    ReportImage,
    ReportTemplate,
)


class MaterialReportRepository:
    """报告单 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict[str, Any]) -> MaterialReport:
        """创建报告单"""
        report = MaterialReport(**data)
        self.session.add(report)
        await self.session.flush()
        await self.session.refresh(report)
        return report

    async def get_by_id(self, report_id: UUID) -> MaterialReport | None:
        """获取报告单详情"""
        result = await self.session.execute(
            select(MaterialReport)
            .options(
                selectinload(MaterialReport.template),
                selectinload(MaterialReport.items),
            )
            .where(MaterialReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def get_by_no(self, report_no: str) -> MaterialReport | None:
        """通过编号获取报告单"""
        result = await self.session.execute(select(MaterialReport).where(MaterialReport.report_no == report_no))
        return result.scalar_one_or_none()

    async def update(self, report_id: UUID, data: dict[str, Any]) -> MaterialReport | None:
        """更新报告单"""
        report = await self.get_by_id(report_id)
        if not report:
            return None

        for key, value in data.items():
            if hasattr(report, key):
                setattr(report, key, value)

        await self.session.flush()
        await self.session.refresh(report)
        return report

    async def delete(self, report_id: UUID) -> bool:
        """删除报告单"""
        report = await self.get_by_id(report_id)
        if not report:
            return False
        await self.session.delete(report)
        return True

    async def list_with_filter(
        self,
        template_id: UUID | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MaterialReport], int]:
        """带筛选条件的列表查询"""
        query = select(MaterialReport).options(
            selectinload(MaterialReport.template),
            selectinload(MaterialReport.items),
        )

        conditions = []
        if template_id:
            conditions.append(MaterialReport.template_id == template_id)
        if status:
            conditions.append(MaterialReport.status == status)
        if start_date:
            conditions.append(MaterialReport.report_date >= start_date)
        if end_date:
            conditions.append(MaterialReport.report_date <= end_date)
        if keyword:
            conditions.append(
                or_(
                    MaterialReport.report_no.ilike(f"%{keyword}%"),
                    MaterialReport.report_title.ilike(f"%{keyword}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # 分页
        query = query.order_by(MaterialReport.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        reports = list(result.scalars().all())

        return reports, total  # type: ignore[return-value]

    async def get_statistics(self) -> dict[str, Any]:
        """获取统计数据"""
        # 总数
        total_result = await self.session.execute(select(func.count()).select_from(MaterialReport))
        total = total_result.scalar()

        # 按状态统计
        status_result = await self.session.execute(
            select(MaterialReport.status, func.count()).group_by(MaterialReport.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        return {
            "total_count": total,
            "draft_count": by_status.get("draft", 0),
            "completed_count": by_status.get("completed", 0),
            "approved_count": by_status.get("approved", 0),
            "by_template": {},
        }

    async def get_next_report_no(self) -> str:
        """生成下一个报告单编号"""
        # 获取今天的日期前缀
        today = datetime.now().strftime("%Y%m%d")

        # 查询今天最大的编号
        result = await self.session.execute(
            select(MaterialReport.report_no)
            .where(MaterialReport.report_no.like(f"MR-{today}%"))
            .order_by(MaterialReport.report_no.desc())
            .limit(1)
        )
        last_no = result.scalar_one_or_none()

        if last_no:
            # 提取序号并递增
            try:
                seq = int(last_no.split("-")[-1]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1

        return f"MR-{today}{seq:04d}"


class MaterialReportItemRepository:
    """报告单明细 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report_id: UUID, data: dict[str, Any]) -> MaterialReportItem:
        """创建明细"""
        item = MaterialReportItem(report_id=report_id, **data)
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def batch_create(self, report_id: UUID, items: list[dict[str, Any]]) -> list[MaterialReportItem]:
        """批量创建明细"""
        # 先删除现有明细
        await self.session.execute(select(MaterialReportItem).where(MaterialReportItem.report_id == report_id))
        from sqlalchemy import delete

        await self.session.execute(delete(MaterialReportItem).where(MaterialReportItem.report_id == report_id))

        # 创建新明细
        created_items = []
        for item_data in items:
            item = MaterialReportItem(report_id=report_id, **item_data)
            self.session.add(item)
            created_items.append(item)

        await self.session.flush()
        for item in created_items:
            await self.session.refresh(item)
        return created_items

    async def get_by_report_id(self, report_id: UUID) -> list[MaterialReportItem]:
        """获取报告单的所有明细"""
        result = await self.session.execute(
            select(MaterialReportItem)
            .where(MaterialReportItem.report_id == report_id)
            .order_by(MaterialReportItem.row_index)
        )
        return list(result.scalars().all())

    async def delete_by_report_id(self, report_id: UUID) -> bool:
        """删除报告单的所有明细"""
        from sqlalchemy import delete

        await self.session.execute(delete(MaterialReportItem).where(MaterialReportItem.report_id == report_id))
        return True


class ReportTemplateRepository:
    """报告单模板 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict[str, Any]) -> ReportTemplate:
        """创建模板"""
        template = ReportTemplate(**data)
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def get_by_id(self, template_id: UUID) -> ReportTemplate | None:
        """获取模板详情"""
        result = await self.session.execute(select(ReportTemplate).where(ReportTemplate.id == template_id))
        return result.scalar_one_or_none()

    async def update(self, template_id: UUID, data: dict[str, Any]) -> ReportTemplate | None:
        """更新模板"""
        template = await self.get_by_id(template_id)
        if not template:
            return None

        for key, value in data.items():
            if hasattr(template, key):
                setattr(template, key, value)

        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def delete(self, template_id: UUID) -> bool:
        """删除模板（软删除）"""
        template = await self.get_by_id(template_id)
        if not template:
            return False

        template.is_deleted = True
        await self.session.flush()
        return True

    async def list_active(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReportTemplate], int]:
        """获取启用的模板列表"""
        query = select(ReportTemplate).where(ReportTemplate.is_active)

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # 分页
        query = query.order_by(ReportTemplate.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        templates = list(result.scalars().all())

        return templates, total  # type: ignore[return-value]


class ReportImageRepository:
    """报告单图片 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict[str, Any]) -> ReportImage:
        """创建图片记录"""
        image = ReportImage(**data)
        self.session.add(image)
        await self.session.flush()
        await self.session.refresh(image)
        return image

    async def get_by_id(self, image_id: int) -> ReportImage | None:
        """获取图片记录"""
        result = await self.session.execute(select(ReportImage).where(ReportImage.id == image_id))
        return result.scalar_one_or_none()

    async def get_by_report_id(self, report_id: UUID) -> list[ReportImage]:
        """获取报告单的所有图片记录"""
        result = await self.session.execute(
            select(ReportImage).where(ReportImage.report_id == report_id).order_by(ReportImage.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, image_id: int, data: dict[str, Any]) -> ReportImage | None:
        """更新图片记录"""
        image = await self.get_by_id(image_id)
        if not image:
            return None

        for key, value in data.items():
            if hasattr(image, key):
                setattr(image, key, value)

        await self.session.flush()
        await self.session.refresh(image)
        return image

    async def delete(self, image_id: int) -> bool:
        """删除图片记录"""
        image = await self.get_by_id(image_id)
        if not image:
            return False

        await self.session.delete(image)
        return True

    async def delete_by_report_id(self, report_id: UUID) -> bool:
        """删除报告单的所有图片记录"""
        from sqlalchemy import delete

        await self.session.execute(delete(ReportImage).where(ReportImage.report_id == report_id))
        return True

    async def list_all(
        self,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReportTemplate], int]:
        """获取所有模板列表"""
        query = select(ReportTemplate)

        if is_active is not None:
            query = query.where(ReportTemplate.is_active == is_active)

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # 分页
        query = query.order_by(ReportTemplate.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        templates = list(result.scalars().all())

        return templates, total  # type: ignore[return-value]
