"""Dossier Writer database queries."""

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import ChapterAsset, DossierChapter, DossierTemplate, ProductDossier


class DossierRepository:
    """品种资料数据库操作"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ====== Product Dossier ======

    async def check_duplicate(
        self, product_name: str, manufacturer: str, sterile_type: str
    ) -> ProductDossier | None:
        """检查是否存在相同的品种资料"""
        stmt = select(ProductDossier).where(
            and_(
                ProductDossier.product_name == product_name,
                ProductDossier.manufacturer == manufacturer,
                ProductDossier.sterile_type == sterile_type,
                ~ProductDossier.is_deleted,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_product_dossier(self, dossier: ProductDossier) -> ProductDossier:
        """创建品种资料"""
        self.db.add(dossier)
        await self.db.flush()
        return dossier

    async def get_product_dossier(self, dossier_id: UUID) -> ProductDossier | None:
        """获取品种资料详情"""
        stmt = (
            select(ProductDossier)
            .where(and_(ProductDossier.id == dossier_id, ~ProductDossier.is_deleted))
            .options(selectinload(ProductDossier.templates))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_product_dossiers(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[ProductDossier], int]:
        """获取品种资料列表"""
        # 查询总数
        count_stmt = (
            select(func.count())
            .select_from(ProductDossier)
            .where(~ProductDossier.is_deleted)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 查询列表
        stmt = (
            select(ProductDossier)
            .where(~ProductDossier.is_deleted)
            .order_by(ProductDossier.created_at.desc())
            .offset(skip)
            .limit(limit)
            .options(selectinload(ProductDossier.chapters))
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def update_product_dossier(
        self, dossier_id: UUID, **kwargs
    ) -> ProductDossier | None:
        """更新品种资料"""
        dossier = await self.get_product_dossier(dossier_id)
        if not dossier:
            return None
        for key, value in kwargs.items():
            if hasattr(dossier, key):
                setattr(dossier, key, value)
        await self.db.flush()
        return dossier

    async def delete_product_dossier(self, dossier_id: UUID) -> bool:
        """软删除品种资料"""
        dossier = await self.get_product_dossier(dossier_id)
        if not dossier:
            return False
        dossier.is_deleted = True
        await self.db.flush()
        return True

    # ====== Template ======

    async def create_template(self, template: DossierTemplate) -> DossierTemplate:
        """创建模板记录"""
        self.db.add(template)
        await self.db.flush()
        return template

    async def get_template_by_filename(
        self, dossier_id: UUID, filename: str
    ) -> DossierTemplate | None:
        """根据文件名查找模板（用于覆盖更新），返回最新的一条"""
        stmt = (
            select(DossierTemplate)
            .where(
                and_(
                    DossierTemplate.product_dossier_id == dossier_id,
                    DossierTemplate.original_filename == filename,
                    ~DossierTemplate.is_deleted,
                )
            )
            .order_by(DossierTemplate.uploaded_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_templates(self, dossier_id: UUID) -> list[DossierTemplate]:
        """获取模板列表"""
        stmt = (
            select(DossierTemplate)
            .where(
                and_(
                    DossierTemplate.product_dossier_id == dossier_id,
                    ~DossierTemplate.is_deleted,
                )
            )
            .order_by(DossierTemplate.uploaded_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ====== Chapter ======

    async def create_chapter(self, chapter: DossierChapter) -> DossierChapter:
        """创建章节"""
        self.db.add(chapter)
        await self.db.flush()
        return chapter

    async def bulk_create_chapters(self, chapters: list[DossierChapter]) -> None:
        """批量创建章节"""
        self.db.add_all(chapters)
        await self.db.flush()

    async def delete_chapters_by_dossier(self, dossier_id: UUID) -> int:
        """删除品种的所有章节"""
        stmt = select(DossierChapter).where(
            DossierChapter.product_dossier_id == dossier_id
        )
        result = await self.db.execute(stmt)
        chapters = result.scalars().all()
        count = len(chapters)
        for chapter in chapters:
            await self.db.delete(chapter)
        await self.db.flush()
        return count

    async def get_chapter_tree(self, dossier_id: UUID) -> list[DossierChapter]:
        """获取章节树（扁平列表，前端组装树）"""
        stmt = (
            select(DossierChapter)
            .where(DossierChapter.product_dossier_id == dossier_id)
            .order_by(DossierChapter.sort_order)
            .options(selectinload(DossierChapter.assets))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_chapter(self, chapter_id: UUID) -> DossierChapter | None:
        """获取章节详情"""
        stmt = (
            select(DossierChapter)
            .where(DossierChapter.id == chapter_id)
            .options(selectinload(DossierChapter.assets))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_chapter(self, chapter_id: UUID, **kwargs) -> DossierChapter | None:
        """更新章节"""
        chapter = await self.get_chapter(chapter_id)
        if not chapter:
            return None
        for key, value in kwargs.items():
            if hasattr(chapter, key):
                setattr(chapter, key, value)
        await self.db.flush()
        return chapter

    async def count_chapters(self, dossier_id: UUID) -> int:
        """统计章节数量"""
        stmt = (
            select(func.count())
            .select_from(DossierChapter)
            .where(DossierChapter.product_dossier_id == dossier_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    # ====== Asset ======

    async def create_asset(self, asset: ChapterAsset) -> ChapterAsset:
        """创建素材记录"""
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def list_assets(self, chapter_id: UUID) -> list[ChapterAsset]:
        """获取章节素材列表"""
        stmt = (
            select(ChapterAsset)
            .where(ChapterAsset.chapter_id == chapter_id)
            .order_by(ChapterAsset.uploaded_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_asset(self, asset_id: UUID) -> ChapterAsset | None:
        """获取素材详情"""
        stmt = select(ChapterAsset).where(ChapterAsset.id == asset_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_asset(self, asset_id: UUID) -> bool:
        """软删除素材"""
        asset = await self.get_asset(asset_id)
        if not asset:
            return False
        asset.is_deleted = True
        await self.db.flush()
        return True

    async def count_assets(self, chapter_id: UUID) -> int:
        """统计章节素材数量"""
        stmt = (
            select(func.count())
            .select_from(ChapterAsset)
            .where(ChapterAsset.chapter_id == chapter_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    # ====== Asset Usage ======

    async def create_asset_usage(
        self,
        product_dossier_id: UUID,
        chapter_id: UUID,
        asset_id: UUID,
        usage_type: str,
        is_selected: bool = True,
    ) -> "ChapterAssetUsage":
        """创建素材使用记录"""
        from .field_models import ChapterAssetUsage

        usage = ChapterAssetUsage(
            product_dossier_id=product_dossier_id,
            chapter_id=chapter_id,
            asset_id=asset_id,
            usage_type=usage_type,
            is_selected=is_selected,
        )
        self.db.add(usage)
        await self.db.flush()
        return usage

    async def get_asset_usage(
        self, chapter_id: UUID, asset_id: UUID
    ) -> "ChapterAssetUsage | None":
        """获取单个素材使用记录"""
        from .field_models import ChapterAssetUsage

        stmt = select(ChapterAssetUsage).where(
            and_(
                ChapterAssetUsage.chapter_id == chapter_id,
                ChapterAssetUsage.asset_id == asset_id,
                ~ChapterAssetUsage.is_deleted,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_asset_usage(
        self, usage_id: UUID, is_selected: bool
    ) -> "ChapterAssetUsage | None":
        """更新素材使用状态"""
        from .field_models import ChapterAssetUsage

        stmt = select(ChapterAssetUsage).where(
            and_(
                ChapterAssetUsage.id == usage_id,
                ~ChapterAssetUsage.is_deleted,
            )
        )
        result = await self.db.execute(stmt)
        usage = result.scalar_one_or_none()
        if not usage:
            return None
        usage.is_selected = is_selected
        await self.db.flush()
        return usage

    async def get_selected_assets_for_chapter(
        self, chapter_id: UUID
    ) -> list["ChapterAsset"]:
        """获取章节已选择使用的素材（is_selected=true）"""
        from .field_models import ChapterAssetUsage

        stmt = (
            select(ChapterAsset)
            .join(
                ChapterAssetUsage,
                and_(
                    ChapterAssetUsage.asset_id == ChapterAsset.id,
                    ChapterAssetUsage.chapter_id == chapter_id,
                    ChapterAssetUsage.is_selected == True,
                    ~ChapterAssetUsage.is_deleted,
                ),
            )
            .where(~ChapterAsset.is_deleted)
            .order_by(ChapterAsset.uploaded_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_available_assets_with_usage(
        self, chapter_id: UUID
    ) -> list[dict]:
        """获取章节的可用素材（自有 + 继承）及使用状态
        
        返回格式：
        [
            {
                "asset": ChapterAsset,
                "usage": ChapterAssetUsage | None,
                "is_inherited": bool,
                "is_selected": bool,
                "parent_chapter_code": str | None,
            }
        ]
        """
        from .field_models import ChapterAssetUsage

        # 1. 获取当前章节信息
        chapter = await self.get_chapter(chapter_id)
        if not chapter:
            return []

        # 2. 获取所有祖先章节 ID
        ancestor_ids = await self.get_ancestor_chapter_ids(chapter_id)
        all_chapter_ids = [chapter_id] + ancestor_ids

        # 3. 查询这些章节的所有素材
        stmt = (
            select(ChapterAsset)
            .where(
                and_(
                    ChapterAsset.chapter_id.in_(all_chapter_ids),
                    ~ChapterAsset.is_deleted,
                )
            )
            .order_by(ChapterAsset.uploaded_at)
        )
        result = await self.db.execute(stmt)
        assets = list(result.scalars().all())

        # 4. 查询当前章节的所有 usage 记录
        usage_stmt = select(ChapterAssetUsage).where(
            and_(
                ChapterAssetUsage.chapter_id == chapter_id,
                ~ChapterAssetUsage.is_deleted,
            )
        )
        usage_result = await self.db.execute(usage_stmt)
        usages = {u.asset_id: u for u in usage_result.scalars().all()}

        # 5. 组装结果
        available = []
        for asset in assets:
            usage = usages.get(asset.id)
            is_inherited = asset.chapter_id != chapter_id
            
            # 获取父章节的 chapter_code
            parent_chapter_code = None
            if is_inherited:
                parent_chapter = await self.get_chapter(asset.chapter_id)
                if parent_chapter:
                    parent_chapter_code = parent_chapter.chapter_code

            available.append({
                "asset": asset,
                "usage": usage,
                "is_inherited": is_inherited,
                "is_selected": usage.is_selected if usage else False,
                "parent_chapter_code": parent_chapter_code,
            })

        return available

    async def get_ancestor_chapter_ids(self, chapter_id: UUID) -> list[UUID]:
        """获取所有祖先章节的 ID 列表（向上查找）"""
        ancestor_ids = []
        current_id = chapter_id

        while True:
            stmt = select(DossierChapter.parent_id).where(
                DossierChapter.id == current_id
            )
            result = await self.db.execute(stmt)
            parent_id = result.scalar_one_or_none()
            
            if not parent_id:
                break
            
            ancestor_ids.append(parent_id)
            current_id = parent_id

        return ancestor_ids

    async def delete_usages_for_asset(self, asset_id: UUID) -> int:
        """删除素材的所有 usage 记录（软删除）"""
        from .field_models import ChapterAssetUsage

        stmt = select(ChapterAssetUsage).where(
            and_(
                ChapterAssetUsage.asset_id == asset_id,
                ~ChapterAssetUsage.is_deleted,
            )
        )
        result = await self.db.execute(stmt)
        usages = result.scalars().all()
        count = len(usages)
        for usage in usages:
            usage.is_deleted = True
        await self.db.flush()
        return count
