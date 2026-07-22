"""Static Data Module - Models

SQLAlchemy ORM models for static data tables.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    """Base class for all models"""

    pass


# ========== 1. Storage Condition ==========


class StorageCondition(BaseModel):
    """Storage Condition Dictionary"""

    __tablename__ = "t_qs_storage_condition"
    __table_args__ = {"schema": "qms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cond_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Condition code (unique)")
    cond_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Condition name")
    temp_min: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="Min temperature")
    temp_max: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="Max temperature")
    humidity: Mapped[str | None] = mapped_column(String(50), comment="Humidity requirement")
    remark: Mapped[str | None] = mapped_column(String(500), comment="Remark")
    status: Mapped[int] = mapped_column(SmallInteger, default=0, comment="Status: 0-enabled 1-disabled")
    create_by: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Creator")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="Create time")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="Updater")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.now, comment="Update time")
    del_flag: Mapped[int] = mapped_column(SmallInteger, default=0, comment="Delete flag")


# ========== 2. Unit ==========


class Unit(BaseModel):
    """Unit Dictionary"""

    __tablename__ = "t_qs_unit"
    __table_args__ = {"schema": "qms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    unit_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Unit code (unique)")
    unit_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="Unit name")
    unit_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="Unit type")
    base_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), comment="Conversion base value")
    remark: Mapped[str | None] = mapped_column(String(500), comment="Remark")
    status: Mapped[int] = mapped_column(SmallInteger, default=0, comment="Status: 0-enabled 1-disabled")
    create_by: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Creator")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="Create time")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="Updater")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.now, comment="Update time")
    del_flag: Mapped[int] = mapped_column(SmallInteger, default=0, comment="Delete flag")


# ========== 11. HPLC Reference Substance Ledger ==========


class HplcReference(BaseModel):
    """HPLC Reference Substance Ledger"""

    __tablename__ = "t_qs_hplc_reference"
    __table_args__ = {"schema": "qms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ref_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Reference code (unique)")
    ref_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Reference name")
    project_name: Mapped[str | None] = mapped_column(String(100), comment="Associated test project")
    internal_batch: Mapped[str | None] = mapped_column(String(50), comment="Internal batch number")
    cas_no: Mapped[str | None] = mapped_column(String(50), comment="CAS number")
    cat_no: Mapped[str | None] = mapped_column(String(50), comment="Supplier catalog number")
    manufacturer_batch: Mapped[str | None] = mapped_column(String(50), comment="Manufacturer batch")
    manufacturer: Mapped[str | None] = mapped_column(String(200), comment="Supplier/source")
    spec: Mapped[str | None] = mapped_column(String(50), comment="Specification per bottle (e.g., 100mg)")
    spec_unit: Mapped[str | None] = mapped_column(String(10), comment="Specification unit (mg/g)")
    quantity: Mapped[int | None] = mapped_column(Integer, comment="Quantity (bottle count)")
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), comment="Total amount (mg/g)")
    remaining_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), comment="Remaining amount (mg/g)")
    remaining_unit: Mapped[str | None] = mapped_column(String(10), default="mg", comment="Remaining amount unit")
    recal_threshold: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), comment="Recalibration threshold (mg/g)")
    need_recal: Mapped[bool] = mapped_column(Boolean, default=False, comment="Need recalibration flag")
    purity: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), comment="Purity %")
    content: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), comment="Content %")
    stock_status: Mapped[str | None] = mapped_column(String(100), comment="Current stock status")
    arrival_date: Mapped[date | None] = mapped_column(Date, comment="Arrival date")
    produce_date: Mapped[date | None] = mapped_column(Date, comment="Production/calibration date")
    expire_date: Mapped[date | None] = mapped_column(Date, comment="Expiry date")
    recal_cycle_days: Mapped[int | None] = mapped_column(Integer, comment="Recalibration cycle (days)")
    open_date: Mapped[date | None] = mapped_column(Date, comment="Opening date")
    open_expire_days: Mapped[int | None] = mapped_column(Integer, comment="Opening validity (days)")
    storage_cond_code: Mapped[str | None] = mapped_column(String(50), comment="Storage condition code")
    location: Mapped[str | None] = mapped_column(String(100), comment="Storage location")
    has_coa: Mapped[bool] = mapped_column(Boolean, default=False, comment="Has COA")
    handover_no: Mapped[str | None] = mapped_column(String(100), comment="Handover number")
    ref_status: Mapped[int] = mapped_column(Integer, default=0, comment="Status: 0-active 1-used 2-expired 3-scrapped")
    remark: Mapped[str | None] = mapped_column(Text, comment="Remark")
    attach_file: Mapped[str | None] = mapped_column(Text, comment="Attachments JSON")
    create_by: Mapped[int] = mapped_column(Integer, default=0, comment="Creator")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="Create time")
    update_by: Mapped[int | None] = mapped_column(Integer, comment="Updater")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.now, comment="Update time")
    del_flag: Mapped[int] = mapped_column(Integer, default=0, comment="Delete flag")


class HplcReferenceUsage(BaseModel):
    """HPLC Reference Substance Usage Log"""

    __tablename__ = "t_qs_hplc_reference_usage"
    __table_args__ = {"schema": "qms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ref_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Reference substance ID")
    ref_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Reference code")
    ref_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Reference name")
    usage_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="Usage amount (mg/g)")
    usage_unit: Mapped[str] = mapped_column(String(10), default="mg", comment="Usage unit")
    remaining_after: Mapped[Decimal] = mapped_column(Numeric(10, 2), comment="Remaining amount after usage")
    usage_person: Mapped[str | None] = mapped_column(String(100), comment="Person who used")
    usage_purpose: Mapped[str | None] = mapped_column(String(200), comment="Usage purpose/project")
    usage_date: Mapped[date] = mapped_column(Date, default=date.today, comment="Usage date")
    remark: Mapped[str | None] = mapped_column(Text, comment="Remark")
    create_by: Mapped[int] = mapped_column(Integer, default=0, comment="Creator")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="Create time")
    del_flag: Mapped[int] = mapped_column(Integer, default=0, comment="Delete flag")


# ========== 5. Chromatography Column ==========


class ChromColumn(BaseModel):
    """Chromatography Column Management"""

    __tablename__ = "t_qs_chrom_column"
    __table_args__ = {"schema": "qms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    col_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Column code (unique)")
    col_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="Stationary phase type (C18/C8 etc.)")
    spec: Mapped[str] = mapped_column(String(100), nullable=False, comment="Specification")
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False, comment="Manufacturer")
    serial_no: Mapped[str] = mapped_column(String(100), nullable=False, comment="Original serial number")
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False, comment="Purchase date")
    use_start_date: Mapped[date | None] = mapped_column(Date, comment="Start using date")
    max_use_times: Mapped[int] = mapped_column(Integer, nullable=False, comment="Max allowed usage times")
    used_times: Mapped[int] = mapped_column(Integer, default=0, comment="Used times")
    storage_cond_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Storage condition code")
    location: Mapped[str] = mapped_column(String(100), nullable=False, comment="Storage location")
    col_status: Mapped[int] = mapped_column(
        SmallInteger, default=0, comment="0-active 1-waiting_clean 2-sealed 3-scrapped"
    )
    column_category: Mapped[int] = mapped_column(SmallInteger, default=0, comment="0-HPLC 1-GC")
    apply_method: Mapped[str | None] = mapped_column(String(500), comment="Applicable test method")
    attach_file: Mapped[str | None] = mapped_column(Text, comment="Attachments")
    remark: Mapped[str | None] = mapped_column(String(500), comment="Remark")
    create_by: Mapped[int] = mapped_column(Integer, default=0, comment="Creator")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="Create time")
    update_by: Mapped[int | None] = mapped_column(Integer, comment="Updater")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.now, comment="Update time")
    del_flag: Mapped[int] = mapped_column(Integer, default=0, comment="Delete flag")


# ========== 7. Standard (标准品) ==========


class Standard(BaseModel):
    """Standard Reference Substance Management (标准品管理)"""

    __tablename__ = "t_qs_standard"
    __table_args__ = {"schema": "qms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    std_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Standard code (unique)")
    std_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Standard name")
    std_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="Type: national/working/international")
    cas_no: Mapped[str | None] = mapped_column(String(50), comment="CAS number")
    manufacturer: Mapped[str | None] = mapped_column(String(200), comment="Source/Manufacturer")
    batch_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="Batch number")
    spec: Mapped[str | None] = mapped_column(String(100), comment="Specification")
    purity: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), comment="Purity %")
    content: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), comment="Content %")
    quantity: Mapped[int] = mapped_column(Integer, default=0, comment="Quantity")
    unit_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="Unit code")
    min_stock: Mapped[int] = mapped_column(Integer, default=0, comment="Minimum stock alert")
    produce_date: Mapped[date | None] = mapped_column(Date, comment="Production date")
    expire_date: Mapped[date | None] = mapped_column(Date, comment="Expiration date")
    storage_cond_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Storage condition code")
    location: Mapped[str | None] = mapped_column(String(100), comment="Storage location")
    test_item: Mapped[str | None] = mapped_column(String(200), comment="Associated test item")
    std_status: Mapped[int] = mapped_column(SmallInteger, default=0, comment="0-active 1-used_up 2-expired 3-scrapped")
    attach_file: Mapped[str | None] = mapped_column(Text, comment="Attachments")
    remark: Mapped[str | None] = mapped_column(String(500), comment="Remark")
    create_by: Mapped[int] = mapped_column(Integer, default=0, comment="Creator")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="Create time")
    update_by: Mapped[int | None] = mapped_column(Integer, comment="Updater")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.now, comment="Update time")
    del_flag: Mapped[int] = mapped_column(Integer, default=0, comment="Delete flag")


class Medium(BaseModel):
    """Medium Management (培养基管理)"""

    __tablename__ = "t_qs_medium"
    __table_args__ = {"schema": "qms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    medium_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Medium code (unique)")
    medium_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Medium name")
    medium_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="Medium type")
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False, comment="Manufacturer")
    batch_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="Batch number")
    spec: Mapped[str] = mapped_column(String(100), nullable=False, comment="Specification")
    storage_cond_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Storage condition code")
    expire_date: Mapped[date] = mapped_column(Date, nullable=False, comment="Expiration date")
    verify_status: Mapped[str] = mapped_column(String(20), nullable=False, comment="Verification status")
    config_method: Mapped[str | None] = mapped_column(String(500), comment="Configuration method")
    stock_num: Mapped[int] = mapped_column(Integer, default=0, comment="Stock quantity")
    unit_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="Unit code")
    min_stock: Mapped[int] = mapped_column(Integer, default=0, comment="Minimum stock")
    status: Mapped[int] = mapped_column(SmallInteger, default=0, comment="0-active 1-inactive")
    attach_file: Mapped[str | None] = mapped_column(Text, comment="Attachments")
    remark: Mapped[str | None] = mapped_column(String(500), comment="Remark")
    create_by: Mapped[int] = mapped_column(Integer, default=0, comment="Creator")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="Create time")
    update_by: Mapped[int | None] = mapped_column(Integer, comment="Updater")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.now, comment="Update time")
    del_flag: Mapped[int] = mapped_column(Integer, default=0, comment="Delete flag")
