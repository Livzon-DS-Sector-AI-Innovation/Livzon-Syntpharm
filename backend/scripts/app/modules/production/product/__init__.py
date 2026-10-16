"""Product management - product definitions and production output tracking."""

from .api import router as product_router
from .output_api import router as output_router

__all__ = ["product_router", "output_router"]
