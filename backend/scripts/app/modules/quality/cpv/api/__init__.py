"""CPV API routes."""

from fastapi import APIRouter

from app.modules.quality.cpv.api.cpv_import import router as cpv_import_router
from app.modules.quality.cpv.api.cpv_products import router as cpv_products_router

router = APIRouter()

# Mount CPV sub-routes
router.include_router(cpv_products_router, prefix="/cpv", tags=["CPV-产品"])
router.include_router(cpv_import_router, prefix="/cpv", tags=["CPV-导入"])
