"""质量检验台账 API 汇总路由。"""

from fastapi import APIRouter

from app.modules.quality.qc_report.api import batches, products, stats

router = APIRouter()
router.include_router(products.router)
router.include_router(batches.router)
router.include_router(stats.router)

__all__ = ["router"]
