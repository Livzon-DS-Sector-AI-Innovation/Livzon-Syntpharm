"""Re-export from production public API to avoid duplicate definitions."""

from app.modules.production.public_api import LabelVerification

__all__ = ["LabelVerification"]
