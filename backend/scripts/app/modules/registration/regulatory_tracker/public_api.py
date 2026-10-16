"""Regulatory tracker module public API — cross-module access points.

Other modules should import from this file instead of directly accessing
internal service/repository/models.
"""

from app.modules.registration.regulatory_tracker import repository

__all__ = [
    "repository",
]
