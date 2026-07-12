"""Static Data Module - Repository

Database access layer for static data tables.
"""

from datetime import date
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.static_data.models import (
    ChromColumn,
    HplcReference,
    HplcReferenceUsage,
    Medium,
    Standard,
    StorageCondition,
)


class StaticDataRepository:
    """Repository for static data operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== HPLC Reference Substance ==========

    async def list_hplc_reference(
        self,
        skip: int = 0,
        limit: int = 20,
        ref_code: str | None = None,
        ref_name: str | None = None,
        project_name: str | None = None,
        ref_status: int | None = None,
        has_coa: bool | None = None,
    ) -> tuple[list[HplcReference], int]:
        """List HPLC reference substances with filters"""
        query = select(HplcReference).where(HplcReference.del_flag == 0)
        count_query = select(func.count(HplcReference.id)).where(HplcReference.del_flag == 0)

        if ref_code:
            query = query.where(HplcReference.ref_code.like(f"%{ref_code}%"))
            count_query = count_query.where(HplcReference.ref_code.like(f"%{ref_code}%"))
        if ref_name:
            query = query.where(HplcReference.ref_name.like(f"%{ref_name}%"))
            count_query = count_query.where(HplcReference.ref_name.like(f"%{ref_name}%"))
        if project_name:
            query = query.where(HplcReference.project_name.like(f"%{project_name}%"))
            count_query = count_query.where(HplcReference.project_name.like(f"%{project_name}%"))
        if ref_status is not None:
            query = query.where(HplcReference.ref_status == ref_status)
            count_query = count_query.where(HplcReference.ref_status == ref_status)
        if has_coa is not None:
            query = query.where(HplcReference.has_coa == has_coa)
            count_query = count_query.where(HplcReference.has_coa == has_coa)

        query = query.order_by(HplcReference.id.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        return items, total

    async def get_hplc_reference(self, id: int) -> HplcReference | None:
        """Get single HPLC reference substance by ID"""
        result = await self.db.execute(
            select(HplcReference).where(and_(HplcReference.id == id, HplcReference.del_flag == 0))
        )
        return result.scalar_one_or_none()

    async def get_hplc_reference_by_code(self, ref_code: str) -> HplcReference | None:
        """Get HPLC reference substance by code"""
        result = await self.db.execute(
            select(HplcReference).where(and_(HplcReference.ref_code == ref_code, HplcReference.del_flag == 0))
        )
        return result.scalar_one_or_none()

    async def create_hplc_reference(self, data: dict[str, Any]) -> HplcReference:
        """Create new HPLC reference substance"""
        obj = HplcReference(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    @staticmethod
    def _recompute_need_recal(obj: HplcReference) -> None:
        """根据剩余量与阈值动态重算 need_recal 标记"""
        threshold = float(obj.recal_threshold or 0)
        remaining = float(obj.remaining_amount or 0)
        # 阈值 > 0 且剩余量 <= 阈值 时标记需要复标；否则清除标记
        obj.need_recal = threshold > 0 and remaining <= threshold

    async def update_hplc_reference(self, id: int, data: dict[str, Any]) -> HplcReference | None:
        """Update HPLC reference substance"""
        obj = await self.get_hplc_reference(id)
        if not obj:
            return None
        for key, value in data.items():
            if value is not None or key in ["ref_status", "remark"]:
                setattr(obj, key, value)
        # 更新后重算 need_recal（用户可能调整了阈值或剩余量）
        self._recompute_need_recal(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_hplc_reference(self, id: int) -> bool:
        """Soft delete HPLC reference substance"""
        obj = await self.get_hplc_reference(id)
        if not obj:
            raise ValueError(f"HPLC reference substance {id} not found")
        obj.del_flag = 1
        await self.db.flush()
        return True

    async def adjust_hplc_reference_quantity(self, id: int, quantity_change: int) -> HplcReference | None:
        """Adjust HPLC reference quantity (positive = in, negative = out)"""
        obj = await self.get_hplc_reference(id)
        if not obj:
            return None
        current = obj.quantity or 0
        new_quantity = current + quantity_change
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative")
        obj.quantity = new_quantity
        # 调整瓶数后也重算 need_recal
        self._recompute_need_recal(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def use_hplc_reference(
        self,
        id: int,
        usage_amount: float,
        usage_unit: str,
        usage_person: str | None,
        usage_purpose: str | None,
        remark: str | None,
        user_id: int,
    ) -> tuple[HplcReference, HplcReferenceUsage]:
        """Use HPLC reference substance (扣减剩余量并记录领用)"""
        obj = await self.get_hplc_reference(id)
        if not obj:
            raise ValueError(f"HPLC reference {id} not found")

        # 计算剩余量
        current_remaining = float(obj.remaining_amount or obj.total_amount or 0)
        new_remaining = current_remaining - usage_amount
        if new_remaining < 0:
            raise ValueError(f"剩余量不足: 当前 {current_remaining}{usage_unit}, 需领用 {usage_amount}{usage_unit}")

        # 更新剩余量
        obj.remaining_amount = new_remaining  # type: ignore[assignment]
        obj.remaining_unit = usage_unit

        # 重算 need_recal 标记（剩余量恢复到阈值以上时自动清除）
        self._recompute_need_recal(obj)

        obj.update_by = user_id
        await self.db.flush()
        await self.db.refresh(obj)

        # 创建领用记录
        usage_log = HplcReferenceUsage(
            ref_id=id,
            ref_code=obj.ref_code,
            ref_name=obj.ref_name,
            usage_amount=usage_amount,
            usage_unit=usage_unit,
            remaining_after=new_remaining,
            usage_person=usage_person,
            usage_purpose=usage_purpose,
            usage_date=date.today(),
            remark=remark,
            create_by=user_id,
        )
        self.db.add(usage_log)
        await self.db.flush()
        await self.db.refresh(usage_log)

        return obj, usage_log

    async def list_hplc_reference_usage(
        self,
        ref_id: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[HplcReferenceUsage], int]:
        """查询领用记录"""
        query = select(HplcReferenceUsage).where(HplcReferenceUsage.del_flag == 0)
        count_query = select(func.count(HplcReferenceUsage.id)).where(HplcReferenceUsage.del_flag == 0)

        if ref_id:
            query = query.where(HplcReferenceUsage.ref_id == ref_id)
            count_query = count_query.where(HplcReferenceUsage.ref_id == ref_id)

        query = query.order_by(HplcReferenceUsage.id.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        return items, total

    async def get_hplc_references_need_recal(self) -> list[HplcReference]:
        """查询需要复标的对照品（动态计算：剩余量 <= 复标阈值）"""
        result = await self.db.execute(
            select(HplcReference).where(
                and_(
                    HplcReference.del_flag == 0,
                    HplcReference.ref_status == 0,
                    HplcReference.recal_threshold > 0,
                    HplcReference.remaining_amount <= HplcReference.recal_threshold,
                )
            )
        )
        return list(result.scalars().all())

    # ========== Chromatography Column ==========

    async def list_chrom_column(
        self,
        skip: int = 0,
        limit: int = 20,
        col_code: str | None = None,
        col_type: str | None = None,
        manufacturer: str | None = None,
        spec: str | None = None,
        col_status: int | None = None,
        column_category: int | None = None,
    ) -> tuple[list[ChromColumn], int]:
        """List chromatography columns with filters"""
        query = select(ChromColumn).where(ChromColumn.del_flag == 0)
        count_query = select(func.count(ChromColumn.id)).where(ChromColumn.del_flag == 0)

        if col_code:
            query = query.where(ChromColumn.col_code.like(f"%{col_code}%"))
            count_query = count_query.where(ChromColumn.col_code.like(f"%{col_code}%"))
        if col_type:
            query = query.where(ChromColumn.col_type.like(f"%{col_type}%"))
            count_query = count_query.where(ChromColumn.col_type.like(f"%{col_type}%"))
        if manufacturer:
            query = query.where(ChromColumn.manufacturer.like(f"%{manufacturer}%"))
            count_query = count_query.where(ChromColumn.manufacturer.like(f"%{manufacturer}%"))
        if spec:
            query = query.where(ChromColumn.spec.like(f"%{spec}%"))
            count_query = count_query.where(ChromColumn.spec.like(f"%{spec}%"))
        if col_status is not None:
            query = query.where(ChromColumn.col_status == col_status)
            count_query = count_query.where(ChromColumn.col_status == col_status)
        if column_category is not None:
            query = query.where(ChromColumn.column_category == column_category)
            count_query = count_query.where(ChromColumn.column_category == column_category)

        query = query.order_by(ChromColumn.id.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        return items, total

    async def get_chrom_column(self, id: int) -> ChromColumn | None:
        """Get single chromatography column by ID"""
        result = await self.db.execute(select(ChromColumn).where(and_(ChromColumn.id == id, ChromColumn.del_flag == 0)))
        return result.scalar_one_or_none()

    async def get_chrom_column_by_code(self, col_code: str) -> ChromColumn | None:
        """Get chromatography column by code"""
        result = await self.db.execute(
            select(ChromColumn).where(and_(ChromColumn.col_code == col_code, ChromColumn.del_flag == 0))
        )
        return result.scalar_one_or_none()

    async def create_chrom_column(self, data: dict[str, Any]) -> ChromColumn:
        """Create new chromatography column"""
        obj = ChromColumn(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_chrom_column(self, id: int, data: dict[str, Any]) -> ChromColumn | None:
        """Update chromatography column"""
        obj = await self.get_chrom_column(id)
        if not obj:
            return None
        for key, value in data.items():
            if value is not None or key in ["col_status", "remark"]:
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_chrom_column(self, id: int) -> bool:
        """Soft delete chromatography column"""
        obj = await self.get_chrom_column(id)
        if not obj:
            raise ValueError(f"Chromatography column {id} not found")
        obj.del_flag = 1
        await self.db.flush()
        return True

    async def increment_chrom_column_usage(self, id: int) -> ChromColumn | None:
        """Increment usage count of a chromatography column"""
        obj = await self.get_chrom_column(id)
        if not obj:
            return None
        obj.used_times += 1
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    # ========== Medium (培养基) ==========

    async def list_medium(
        self,
        skip: int = 0,
        limit: int = 20,
        medium_code: str | None = None,
        medium_name: str | None = None,
        medium_type: str | None = None,
        manufacturer: str | None = None,
        verify_status: str | None = None,
        status: int | None = None,
    ) -> tuple[list[Medium], int]:
        """List medium with filters"""
        query = select(Medium).where(Medium.del_flag == 0)
        count_query = select(func.count(Medium.id)).where(Medium.del_flag == 0)

        if medium_code:
            query = query.where(Medium.medium_code.like(f"%{medium_code}%"))
            count_query = count_query.where(Medium.medium_code.like(f"%{medium_code}%"))
        if medium_name:
            query = query.where(Medium.medium_name.like(f"%{medium_name}%"))
            count_query = count_query.where(Medium.medium_name.like(f"%{medium_name}%"))
        if medium_type:
            query = query.where(Medium.medium_type == medium_type)
            count_query = count_query.where(Medium.medium_type == medium_type)
        if manufacturer:
            query = query.where(Medium.manufacturer.like(f"%{manufacturer}%"))
            count_query = count_query.where(Medium.manufacturer.like(f"%{manufacturer}%"))
        if verify_status:
            query = query.where(Medium.verify_status == verify_status)
            count_query = count_query.where(Medium.verify_status == verify_status)
        if status is not None:
            query = query.where(Medium.status == status)
            count_query = count_query.where(Medium.status == status)

        query = query.order_by(Medium.id.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        return items, total

    async def get_medium(self, id: int) -> Medium | None:
        """Get single medium by ID"""
        result = await self.db.execute(select(Medium).where(and_(Medium.id == id, Medium.del_flag == 0)))
        return result.scalar_one_or_none()

    async def get_medium_by_code(self, medium_code: str) -> Medium | None:
        """Get medium by code"""
        result = await self.db.execute(
            select(Medium).where(and_(Medium.medium_code == medium_code, Medium.del_flag == 0))
        )
        return result.scalar_one_or_none()

    async def create_medium(self, data: dict[str, Any]) -> Medium:
        """Create new medium"""
        obj = Medium(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_medium(self, id: int, data: dict[str, Any]) -> Medium | None:
        """Update medium"""
        obj = await self.get_medium(id)
        if not obj:
            return None
        for key, value in data.items():
            if value is not None or key in ["status", "remark", "stock_num"]:
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_medium(self, id: int) -> bool:
        """Soft delete medium"""
        obj = await self.get_medium(id)
        if not obj:
            raise ValueError(f"Medium {id} not found")
        obj.del_flag = 1
        await self.db.flush()
        return True

    async def adjust_medium_stock(self, id: int, quantity: int) -> Medium | None:
        """Adjust medium stock quantity"""
        obj = await self.get_medium(id)
        if not obj:
            return None
        obj.stock_num += quantity
        if obj.stock_num < 0:
            obj.stock_num = 0
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    # ========== Standard (标准品) ==========

    async def list_standard(
        self,
        skip: int = 0,
        limit: int = 20,
        std_code: str | None = None,
        std_name: str | None = None,
        std_type: str | None = None,
        manufacturer: str | None = None,
        std_status: int | None = None,
    ) -> tuple[list[Standard], int]:
        """List standards with filters"""
        query = select(Standard).where(Standard.del_flag == 0)
        count_query = select(func.count(Standard.id)).where(Standard.del_flag == 0)

        if std_code:
            query = query.where(Standard.std_code.like(f"%{std_code}%"))
            count_query = count_query.where(Standard.std_code.like(f"%{std_code}%"))
        if std_name:
            query = query.where(Standard.std_name.like(f"%{std_name}%"))
            count_query = count_query.where(Standard.std_name.like(f"%{std_name}%"))
        if std_type:
            query = query.where(Standard.std_type == std_type)
            count_query = count_query.where(Standard.std_type == std_type)
        if manufacturer:
            query = query.where(Standard.manufacturer.like(f"%{manufacturer}%"))
            count_query = count_query.where(Standard.manufacturer.like(f"%{manufacturer}%"))
        if std_status is not None:
            query = query.where(Standard.std_status == std_status)
            count_query = count_query.where(Standard.std_status == std_status)

        query = query.order_by(Standard.id.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        return items, total

    async def get_standard(self, id: int) -> Standard | None:
        """Get single standard by ID"""
        result = await self.db.execute(select(Standard).where(and_(Standard.id == id, Standard.del_flag == 0)))
        return result.scalar_one_or_none()

    async def get_standard_by_code(self, std_code: str) -> Standard | None:
        """Get standard by code"""
        result = await self.db.execute(
            select(Standard).where(and_(Standard.std_code == std_code, Standard.del_flag == 0))
        )
        return result.scalar_one_or_none()

    async def create_standard(self, data: dict[str, Any]) -> Standard:
        """Create new standard"""
        obj = Standard(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_standard(self, id: int, data: dict[str, Any]) -> Standard | None:
        """Update standard"""
        obj = await self.get_standard(id)
        if not obj:
            return None
        for key, value in data.items():
            if value is not None or key in ["std_status", "remark", "quantity"]:
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_standard(self, id: int) -> bool:
        """Soft delete standard"""
        obj = await self.get_standard(id)
        if not obj:
            raise ValueError(f"Standard {id} not found")
        obj.del_flag = 1
        await self.db.flush()
        return True

    async def adjust_standard_quantity(self, id: int, quantity: int) -> Standard | None:
        """Adjust standard quantity"""
        obj = await self.get_standard(id)
        if not obj:
            return None
        obj.quantity += quantity
        if obj.quantity < 0:
            obj.quantity = 0
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    # ========== Storage Condition (贮存条件) ==========

    async def list_storage_condition(
        self,
        skip: int = 0,
        limit: int = 20,
        cond_code: str | None = None,
        cond_name: str | None = None,
        status: int | None = None,
    ) -> tuple[list[StorageCondition], int]:
        """List storage conditions with filters"""
        query = select(StorageCondition).where(StorageCondition.del_flag == 0)
        count_query = select(func.count(StorageCondition.id)).where(StorageCondition.del_flag == 0)

        if cond_code:
            query = query.where(StorageCondition.cond_code.like(f"%{cond_code}%"))
            count_query = count_query.where(StorageCondition.cond_code.like(f"%{cond_code}%"))
        if cond_name:
            query = query.where(StorageCondition.cond_name.like(f"%{cond_name}%"))
            count_query = count_query.where(StorageCondition.cond_name.like(f"%{cond_name}%"))
        if status is not None:
            query = query.where(StorageCondition.status == status)
            count_query = count_query.where(StorageCondition.status == status)

        query = query.order_by(StorageCondition.id.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        return items, total

    async def get_storage_condition(self, id: int) -> StorageCondition | None:
        """Get single storage condition by ID"""
        result = await self.db.execute(
            select(StorageCondition).where(and_(StorageCondition.id == id, StorageCondition.del_flag == 0))
        )
        return result.scalar_one_or_none()

    async def get_storage_condition_by_code(self, cond_code: str) -> StorageCondition | None:
        """Get storage condition by code"""
        result = await self.db.execute(
            select(StorageCondition).where(
                and_(
                    StorageCondition.cond_code == cond_code,
                    StorageCondition.del_flag == 0,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_storage_condition(self, data: dict[str, Any]) -> StorageCondition:
        """Create new storage condition"""
        obj = StorageCondition(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_storage_condition(self, id: int, data: dict[str, Any]) -> StorageCondition | None:
        """Update storage condition"""
        obj = await self.get_storage_condition(id)
        if not obj:
            return None
        for key, value in data.items():
            if value is not None or key in [
                "status",
                "remark",
                "temp_min",
                "temp_max",
                "humidity",
            ]:
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_storage_condition(self, id: int) -> bool:
        """Soft delete storage condition"""
        obj = await self.get_storage_condition(id)
        if not obj:
            raise ValueError(f"Storage condition {id} not found")
        obj.del_flag = 1
        await self.db.flush()
        return True
