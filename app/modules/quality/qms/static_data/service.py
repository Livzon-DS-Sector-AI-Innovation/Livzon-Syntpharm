"""Static Data Module - Service

Business logic layer for static data operations.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.static_data import schemas as s
from app.modules.quality.qms.static_data.repository import StaticDataRepository


class StaticDataService:
    """Service for static data operations"""

    def __init__(self, db: AsyncSession):
        self.repo = StaticDataRepository(db)

    # ========== HPLC Reference Substance ==========

    async def list_hplc_reference(self, skip: int = 0, limit: int = 20, **kw) -> Any:  # type: ignore[no-untyped-def]
        """List HPLC reference substances"""
        return await self.repo.list_hplc_reference(skip, limit, **kw)

    async def get_hplc_reference(self, id: int) -> Any:
        """Get single HPLC reference substance"""
        return await self.repo.get_hplc_reference(id)

    async def create_hplc_reference(self, data: s.HplcReferenceCreate, user_id: int) -> Any:
        """Create HPLC reference substance"""
        existing = await self.repo.get_hplc_reference_by_code(data.ref_code)
        if existing:
            raise ValueError(f"Reference code {data.ref_code} already exists")

        obj = await self.repo.create_hplc_reference({**data.model_dump(), "create_by": user_id})
        return obj

    async def _func_l41(self, id: int, data: s.HplcReferenceUpdate, user_id: int) -> Any:
        """Update HPLC reference substance"""
        existing = await self.repo.get_hplc_reference(id)
        if not existing:
            raise ValueError(f"HPLC reference substance {id} not found")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id

        obj = await self.repo.update_hplc_reference(id, update_data)
        return obj

    async def delete_hplc_reference(self, id: int) -> Any:
        """Delete HPLC reference substance"""
        return await self.repo.delete_hplc_reference(id)

    async def _func_l59(self, id: int, quantity_change: int, user_id: int) -> Any:
        """Adjust HPLC reference quantity"""
        try:
            obj = await self.repo.adjust_hplc_reference_quantity(id, quantity_change)
            if not obj:
                raise ValueError(f"HPLC reference {id} not found")
            obj.update_by = user_id
            return obj
        except ValueError as e:
            raise e

    async def _func_l71(
        self,
        id: int,
        usage_amount: float,
        usage_unit: str,
        usage_person: str | None,
        usage_purpose: str | None,
        remark: str | None,
        user_id: int,
    ) -> Any:
        """Use HPLC reference substance"""
        try:
            obj, usage_log = await self.repo.use_hplc_reference(
                id,
                usage_amount,
                usage_unit,
                usage_person,
                usage_purpose,
                remark,
                user_id,
            )
            return obj, usage_log
        except ValueError as e:
            raise e

    async def _func_l95(self, ref_id: int | None = None, skip: int = 0, limit: int = 20) -> Any:
        """查询领用记录"""
        return await self.repo.list_hplc_reference_usage(ref_id, skip, limit)

    async def get_hplc_references_need_recal(self) -> Any:
        """查询需要复标的对照品"""
        return await self.repo.get_hplc_references_need_recal()

    # ========== Chromatography Column ==========

    async def list_chrom_column(self, skip: int = 0, limit: int = 20, **kw) -> Any:  # type: ignore[no-untyped-def]
        """List chromatography columns"""
        return await self.repo.list_chrom_column(skip, limit, **kw)

    async def get_chrom_column(self, id: int) -> Any:
        """Get single chromatography column"""
        return await self.repo.get_chrom_column(id)

    async def create_chrom_column(self, data: s.ChromColumnCreate, user_id: int) -> Any:
        """Create chromatography column"""
        existing = await self.repo.get_chrom_column_by_code(data.col_code)
        if existing:
            raise ValueError(f"Column code {data.col_code} already exists")

        obj = await self.repo.create_chrom_column({**data.model_dump(), "create_by": user_id})
        return obj

    async def _func_l125(self, id: int, data: s.ChromColumnUpdate, user_id: int) -> Any:
        """Update chromatography column"""
        existing = await self.repo.get_chrom_column(id)
        if not existing:
            raise ValueError(f"Chromatography column {id} not found")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id

        obj = await self.repo.update_chrom_column(id, update_data)
        return obj

    async def delete_chrom_column(self, id: int) -> Any:
        """Delete chromatography column"""
        return await self.repo.delete_chrom_column(id)

    async def increment_chrom_column_usage(self, id: int, user_id: int) -> Any:
        """Increment usage count of a chromatography column"""
        obj = await self.repo.increment_chrom_column_usage(id)
        if not obj:
            raise ValueError(f"Chromatography column {id} not found")
        return obj

    # ========== Medium (培养基) ==========

    async def list_medium(self, skip: int = 0, limit: int = 20, **kw) -> Any:  # type: ignore[no-untyped-def]
        """List medium"""
        return await self.repo.list_medium(skip, limit, **kw)

    async def get_medium(self, id: int) -> Any:
        """Get single medium"""
        return await self.repo.get_medium(id)

    async def create_medium(self, data: s.MediumCreate, user_id: int) -> Any:
        """Create medium"""
        existing = await self.repo.get_medium_by_code(data.medium_code)
        if existing:
            raise ValueError(f"Medium code {data.medium_code} already exists")

        obj = await self.repo.create_medium({**data.model_dump(), "create_by": user_id})
        return obj

    async def update_medium(self, id: int, data: s.MediumUpdate, user_id: int) -> Any:
        """Update medium"""
        existing = await self.repo.get_medium(id)
        if not existing:
            raise ValueError(f"Medium {id} not found")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id

        obj = await self.repo.update_medium(id, update_data)
        return obj

    async def delete_medium(self, id: int) -> Any:
        """Delete medium"""
        return await self.repo.delete_medium(id)

    async def adjust_medium_stock(self, id: int, quantity: int, user_id: int) -> Any:
        """Adjust medium stock quantity"""
        obj = await self.repo.adjust_medium_stock(id, quantity)
        if not obj:
            raise ValueError(f"Medium {id} not found")
        obj.update_by = user_id
        return obj

    # ========== Standard (标准品) ==========

    async def list_standard(self, skip: int = 0, limit: int = 20, **kw) -> Any:  # type: ignore[no-untyped-def]
        """List standards"""
        return await self.repo.list_standard(skip, limit, **kw)

    async def get_standard(self, id: int) -> Any:
        """Get single standard"""
        return await self.repo.get_standard(id)

    async def create_standard(self, data: s.StandardCreate, user_id: int) -> Any:
        """Create standard"""
        existing = await self.repo.get_standard_by_code(data.std_code)
        if existing:
            raise ValueError(f"Standard code {data.std_code} already exists")
        obj = await self.repo.create_standard({**data.model_dump(), "create_by": user_id})
        return obj

    async def update_standard(self, id: int, data: s.StandardUpdate, user_id: int) -> Any:
        """Update standard"""
        existing = await self.repo.get_standard(id)
        if not existing:
            raise ValueError(f"Standard {id} not found")
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id
        obj = await self.repo.update_standard(id, update_data)
        return obj

    async def delete_standard(self, id: int) -> Any:
        """Delete standard"""
        return await self.repo.delete_standard(id)

    async def adjust_standard_quantity(self, id: int, quantity: int, user_id: int) -> Any:
        """Adjust standard quantity"""
        obj = await self.repo.adjust_standard_quantity(id, quantity)
        if not obj:
            raise ValueError(f"Standard {id} not found")
        obj.update_by = user_id
        return obj

    # ========== Storage Condition (贮存条件) ==========

    async def list_storage_condition(self, skip: int = 0, limit: int = 20, **kw) -> Any:  # type: ignore[no-untyped-def]
        """List storage conditions"""
        return await self.repo.list_storage_condition(skip, limit, **kw)

    async def get_storage_condition(self, id: int) -> Any:
        """Get single storage condition"""
        return await self.repo.get_storage_condition(id)

    async def _func_l247(self, data: s.StorageConditionCreate, user_id: int) -> Any:
        """Create storage condition"""
        existing = await self.repo.get_storage_condition_by_code(data.cond_code)
        if existing:
            raise ValueError(f"Storage condition code {data.cond_code} already exists")
        obj = await self.repo.create_storage_condition({**data.model_dump(), "create_by": user_id})
        return obj

    async def _func_l258(self, id: int, data: s.StorageConditionUpdate, user_id: int) -> Any:
        """Update storage condition"""
        existing = await self.repo.get_storage_condition(id)
        if not existing:
            raise ValueError(f"Storage condition {id} not found")
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id
        obj = await self.repo.update_storage_condition(id, update_data)
        return obj

    async def delete_storage_condition(self, id: int) -> Any:
        """Delete storage condition"""
        return await self.repo.delete_storage_condition(id)
