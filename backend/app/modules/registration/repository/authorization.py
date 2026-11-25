"""Registration database queries live here."""

from uuid import UUID

from sqlalchemy import Integer, asc, desc, extract, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models import (
    AuthorizationLetter,
    AuthorizationLetterTrail,
    ProductRegistrationNumber,
    ReferenceStandard,
)


class AuthorizationLetterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, letter_id: UUID) -> AuthorizationLetter | None:
        result = await self.session.execute(
            select(AuthorizationLetter).where(
                AuthorizationLetter.id == letter_id,
                AuthorizationLetter.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_letters(
        self,
        *,
        keyword: str | None = None,
        product_name: str | None = None,
        year: int | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[AuthorizationLetter], int]:
        stmt = select(AuthorizationLetter).where(AuthorizationLetter.is_deleted.is_(False))

        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    AuthorizationLetter.product_name.ilike(like),
                    AuthorizationLetter.registration_number.ilike(like),
                    AuthorizationLetter.preparation_unit.ilike(like),
                    AuthorizationLetter.preparation_name.ilike(like),
                )
            )
        if product_name:
            stmt = stmt.where(AuthorizationLetter.product_name == product_name)
        if year:
            stmt = stmt.where(extract("year", AuthorizationLetter.created_at) == year)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        default_sort = AuthorizationLetter.created_at
        sort_column = getattr(AuthorizationLetter, sort_by, default_sort)
        order_func = desc if sort_order == "desc" else asc
        stmt = stmt.order_by(order_func(sort_column))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_distinct_products(self) -> list[str]:
        """已有授权书记录中的品种去重列表（供筛选下拉与主数据合并）"""
        result = await self.session.execute(
            select(AuthorizationLetter.product_name).where(AuthorizationLetter.is_deleted.is_(False)).distinct()
        )
        return list(result.scalars().all())

    async def list_years(self) -> list[int]:
        """按生成时间提取年份选项，降序"""
        year_col = extract("year", AuthorizationLetter.created_at).cast(Integer)
        result = await self.session.execute(
            select(year_col).where(AuthorizationLetter.is_deleted.is_(False)).distinct()
        )
        return sorted((y for y in result.scalars().all() if y is not None), reverse=True)

    async def create(self, letter: AuthorizationLetter) -> AuthorizationLetter:
        self.session.add(letter)
        await self.session.flush()
        await self.session.refresh(letter)
        return letter

    async def soft_delete(self, letter: AuthorizationLetter) -> None:
        letter.is_deleted = True
        await self.session.flush()

    # ── 留痕（只增不删） ──

    async def add_trail(
        self,
        *,
        letter_id: UUID,
        action: str,
        detail: str,
        created_by: UUID | None = None,
    ) -> AuthorizationLetterTrail:
        trail = AuthorizationLetterTrail(
            letter_id=letter_id,
            action=action,
            detail=detail,
            created_by=created_by,
        )
        self.session.add(trail)
        await self.session.flush()
        await self.session.refresh(trail)
        return trail

    async def list_trails(self, letter_id: UUID) -> list[AuthorizationLetterTrail]:
        result = await self.session.execute(
            select(AuthorizationLetterTrail)
            .where(
                AuthorizationLetterTrail.letter_id == letter_id,
                AuthorizationLetterTrail.is_deleted.is_(False),
            )
            .order_by(AuthorizationLetterTrail.created_at.desc())
        )
        return list(result.scalars().all())

    # ── 品种登记号对照表（仅新增、不覆盖） ──

    async def list_products(self) -> list[ProductRegistrationNumber]:
        """品种登记号对照表（按品种名升序）"""
        result = await self.session.execute(
            select(ProductRegistrationNumber)
            .where(ProductRegistrationNumber.is_deleted.is_(False))
            .order_by(ProductRegistrationNumber.product_name)
        )
        return list(result.scalars().all())

    async def get_registration_number(self, product_name: str) -> str | None:
        """按品种名查登记号；不存在返回 None"""
        result = await self.session.execute(
            select(ProductRegistrationNumber.registration_number).where(
                ProductRegistrationNumber.product_name == product_name,
                ProductRegistrationNumber.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def insert_product_registration_number_if_missing(self, product_name: str, registration_number: str) -> None:
        """已存在则跳过（不覆盖），不存在才插入。依赖 (product_name, is_deleted) 唯一约束。"""
        stmt = (
            pg_insert(ProductRegistrationNumber)
            .values(product_name=product_name, registration_number=registration_number)
            .on_conflict_do_nothing(index_elements=["product_name", "is_deleted"])
        )
        await self.session.execute(stmt)
        await self.session.flush()


class ReferenceStandardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: UUID) -> "ReferenceStandard | None":
        result = await self.session.execute(
            select(ReferenceStandard).where(
                ReferenceStandard.id == record_id,
                ReferenceStandard.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_records(
        self,
        *,
        drug_name: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list["ReferenceStandard"], int]:
        stmt = select(ReferenceStandard).where(ReferenceStandard.is_deleted.is_(False))

        if drug_name:
            stmt = stmt.where(ReferenceStandard.drug_name.ilike(f"%{drug_name}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        default_sort = ReferenceStandard.created_at
        sort_column = getattr(ReferenceStandard, sort_by, default_sort)
        order_func = desc if sort_order == "desc" else asc
        stmt = stmt.order_by(order_func(sort_column))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, record: "ReferenceStandard") -> "ReferenceStandard":
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def soft_delete(self, record: "ReferenceStandard") -> None:
        record.is_deleted = True
        await self.session.flush()
