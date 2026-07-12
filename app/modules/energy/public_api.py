"""Energy module public API — cross-module access points.

Other modules should import from this file instead of directly accessing
internal service/repository/models.
"""

from app.modules.energy.repository import EnergyRepository  # type: ignore[attr-defined]
from app.modules.energy.schemas import (
    EnergyAlertRuleCreate,
    EnergyAlertRuleResponse,
    EnergyDeviceConfigCreate,
    EnergyDeviceConfigResponse,
)
from app.modules.energy.service import EnergyService  # type: ignore[attr-defined]

__all__ = [
    "EnergyService",
    "EnergyRepository",
    "EnergyDeviceConfigCreate",
    "EnergyDeviceConfigResponse",
    "EnergyAlertRuleCreate",
    "EnergyAlertRuleResponse",
]
