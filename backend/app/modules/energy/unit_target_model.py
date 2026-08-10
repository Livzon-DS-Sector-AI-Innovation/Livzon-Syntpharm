from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.base_model import BaseModel
import uuid
from datetime import date

class EnergyUnitConsumptionTarget(BaseModel):
    """车间单耗目标表"""
    __tablename__ = "energy_unit_consumption_targets"
    __table_args__ = (
        UniqueConstraint("workshop_id", "target_month", name="uq_workshop_month"),
        {"schema": "energy"},
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("energy.energy_workshops.id", ondelete="CASCADE"), 
        nullable=False,
        comment="关联车间ID"
    )
    target_month: Mapped[date] = mapped_column(Date, nullable=False, comment="目标月份")
    target_unit_consumption: Mapped[float] = mapped_column(
        Numeric(precision=10, scale=4), 
        nullable=False,
        comment="目标单耗(kWh/件)"
    )
