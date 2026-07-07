"""Static Data Module - Service

Business logic layer for static data operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.static_data import schemas as s
from app.modules.quality.qms.static_data.repository import StaticDataRepository


class StaticDataService:
    """Service for static data operations"""

    def __init__(self, db: AsyncSession):
        self.repo = StaticDataRepository(db)

    # ========== HPLC Reference Substance ==========

    async def list_hplc_reference(self, skip: int = 0, limit: int = 20, **kw):
        """List HPLC reference substances"""
        return await self.repo.list_hplc_reference(skip, limit, **kw)

    async def get_hplc_reference(self, id: int):
        """Get single HPLC reference substance"""
        return await self.repo.get_hplc_reference(id)

    async def create_hplc_reference(self, data: s.HplcReferenceCreate, user_id: int):
        """Create HPLC reference substance"""
        existing = await self.repo.get_hplc_reference_by_code(data.ref_code)
        if existing:
            raise ValueError(f"Reference code {data.ref_code} already exists")

        obj = await self.repo.create_hplc_reference(
            {**data.model_dump(), "create_by": user_id}
        )
        return obj

    async def update_hplc_reference(
        self, id: int, data: s.HplcReferenceUpdate, user_id: int
    ):
        """Update HPLC reference substance"""
        existing = await self.repo.get_hplc_reference(id)
        if not existing:
            raise ValueError(f"HPLC reference substance {id} not found")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id

        obj = await self.repo.update_hplc_reference(id, update_data)
        return obj

    async def delete_hplc_reference(self, id: int):
        """Delete HPLC reference substance"""
        return await self.repo.delete_hplc_reference(id)

    async def adjust_hplc_reference_quantity(
        self, id: int, quantity_change: int, user_id: int
    ):
        """Adjust HPLC reference quantity"""
        try:
            obj = await self.repo.adjust_hplc_reference_quantity(id, quantity_change)
            if not obj:
                raise ValueError(f"HPLC reference {id} not found")
            obj.update_by = user_id
            return obj
        except ValueError as e:
            raise e

    async def use_hplc_reference(
        self,
        id: int,
        usage_amount: float,
        usage_unit: str,
        usage_person: str | None,
        usage_purpose: str | None,
        remark: str | None,
        user_id: int,
    ):
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

    async def list_hplc_reference_usage(
        self, ref_id: int | None = None, skip: int = 0, limit: int = 20
    ):
        """查询领用记录"""
        return await self.repo.list_hplc_reference_usage(ref_id, skip, limit)

    async def get_hplc_references_need_recal(self):
        """查询需要复标的对照品"""
        return await self.repo.get_hplc_references_need_recal()

    # ========== Chromatography Column ==========

    async def list_chrom_column(self, skip: int = 0, limit: int = 20, **kw):
        """List chromatography columns"""
        return await self.repo.list_chrom_column(skip, limit, **kw)

    async def get_chrom_column(self, id: int):
        """Get single chromatography column"""
        return await self.repo.get_chrom_column(id)

    async def create_chrom_column(self, data: s.ChromColumnCreate, user_id: int):
        """Create chromatography column"""
        existing = await self.repo.get_chrom_column_by_code(data.col_code)
        if existing:
            raise ValueError(f"Column code {data.col_code} already exists")

        obj = await self.repo.create_chrom_column(
            {**data.model_dump(), "create_by": user_id}
        )
        return obj

    async def update_chrom_column(
        self, id: int, data: s.ChromColumnUpdate, user_id: int
    ):
        """Update chromatography column"""
        existing = await self.repo.get_chrom_column(id)
        if not existing:
            raise ValueError(f"Chromatography column {id} not found")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id

        obj = await self.repo.update_chrom_column(id, update_data)
        return obj

    async def delete_chrom_column(self, id: int):
        """Delete chromatography column"""
        return await self.repo.delete_chrom_column(id)

    async def increment_chrom_column_usage(self, id: int, user_id: int):
        """Increment usage count of a chromatography column"""
        obj = await self.repo.increment_chrom_column_usage(id)
        if not obj:
            raise ValueError(f"Chromatography column {id} not found")
        return obj

    # ========== Medium (培养基) ==========

    async def list_medium(self, skip: int = 0, limit: int = 20, **kw):
        """List medium"""
        return await self.repo.list_medium(skip, limit, **kw)

    async def get_medium(self, id: int):
        """Get single medium"""
        return await self.repo.get_medium(id)

    async def create_medium(self, data: s.MediumCreate, user_id: int):
        """Create medium"""
        existing = await self.repo.get_medium_by_code(data.medium_code)
        if existing:
            raise ValueError(f"Medium code {data.medium_code} already exists")

        obj = await self.repo.create_medium({**data.model_dump(), "create_by": user_id})
        return obj

    async def update_medium(self, id: int, data: s.MediumUpdate, user_id: int):
        """Update medium"""
        existing = await self.repo.get_medium(id)
        if not existing:
            raise ValueError(f"Medium {id} not found")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id

        obj = await self.repo.update_medium(id, update_data)
        return obj

    async def delete_medium(self, id: int):
        """Delete medium"""
        return await self.repo.delete_medium(id)

    async def adjust_medium_stock(self, id: int, quantity: int, user_id: int):
        """Adjust medium stock quantity"""
        obj = await self.repo.adjust_medium_stock(id, quantity)
        if not obj:
            raise ValueError(f"Medium {id} not found")
        obj.update_by = user_id
        return obj

    # ========== Standard (标准品) ==========

    async def list_standard(self, skip: int = 0, limit: int = 20, **kw):
        """List standards"""
        return await self.repo.list_standard(skip, limit, **kw)

    async def get_standard(self, id: int):
        """Get single standard"""
        return await self.repo.get_standard(id)

    async def create_standard(self, data: s.StandardCreate, user_id: int):
        """Create standard"""
        existing = await self.repo.get_standard_by_code(data.std_code)
        if existing:
            raise ValueError(f"Standard code {data.std_code} already exists")
        obj = await self.repo.create_standard(
            {**data.model_dump(), "create_by": user_id}
        )
        return obj

    async def update_standard(self, id: int, data: s.StandardUpdate, user_id: int):
        """Update standard"""
        existing = await self.repo.get_standard(id)
        if not existing:
            raise ValueError(f"Standard {id} not found")
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id
        obj = await self.repo.update_standard(id, update_data)
        return obj

    async def delete_standard(self, id: int):
        """Delete standard"""
        return await self.repo.delete_standard(id)

    async def adjust_standard_quantity(self, id: int, quantity: int, user_id: int):
        """Adjust standard quantity"""
        obj = await self.repo.adjust_standard_quantity(id, quantity)
        if not obj:
            raise ValueError(f"Standard {id} not found")
        obj.update_by = user_id
        return obj

    # ========== Storage Condition (贮存条件) ==========

    async def list_storage_condition(self, skip: int = 0, limit: int = 20, **kw):
        """List storage conditions"""
        return await self.repo.list_storage_condition(skip, limit, **kw)

    async def get_storage_condition(self, id: int):
        """Get single storage condition"""
        return await self.repo.get_storage_condition(id)

    async def create_storage_condition(
        self, data: s.StorageConditionCreate, user_id: int
    ):
        """Create storage condition"""
        existing = await self.repo.get_storage_condition_by_code(data.cond_code)
        if existing:
            raise ValueError(f"Storage condition code {data.cond_code} already exists")
        obj = await self.repo.create_storage_condition(
            {**data.model_dump(), "create_by": user_id}
        )
        return obj

    async def update_storage_condition(
        self, id: int, data: s.StorageConditionUpdate, user_id: int
    ):
        """Update storage condition"""
        existing = await self.repo.get_storage_condition(id)
        if not existing:
            raise ValueError(f"Storage condition {id} not found")
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_data:
            update_data["update_by"] = user_id
        obj = await self.repo.update_storage_condition(id, update_data)
        return obj

    async def delete_storage_condition(self, id: int):
        """Delete storage condition"""
        return await self.repo.delete_storage_condition(id)
