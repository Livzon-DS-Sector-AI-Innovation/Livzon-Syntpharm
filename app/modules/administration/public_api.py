"""Administration module public API — cross-module access points.

Other modules should import from this file instead of directly accessing
internal service/repository/models.
"""

from app.modules.administration.models import VehicleRequest

__all__ = ["VehicleRequest"]
