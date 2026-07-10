"""Static Data Module - Schemas

Pydantic validation schemas for API request/response.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

# ========== Common Fields ==========


class AuditFields(BaseModel):
    """Common audit fields for response"""

    create_by: int = Field(..., description="Creator")
    create_time: datetime = Field(..., description="Create time")
    update_by: int | None = Field(None, description="Updater")
    update_time: datetime | None = Field(None, description="Update time")


# ========== 1. Storage Condition ==========


class StorageConditionBase(BaseModel):
    """Storage Condition Base Schema"""

    cond_code: str = Field(..., max_length=50, description="Condition code")
    cond_name: str = Field(..., max_length=100, description="Condition name")
    temp_min: float | None = Field(None, description="Min temperature")
    temp_max: float | None = Field(None, description="Max temperature")
    humidity: str | None = Field(None, max_length=50, description="Humidity")
    remark: str | None = Field(None, max_length=500, description="Remark")
    status: int = Field(0, description="0-enabled 1-disabled")


class StorageConditionCreate(StorageConditionBase):
    """Create Storage Condition"""

    create_by: int = Field(..., description="Creator")


class StorageConditionUpdate(BaseModel):
    """Update Storage Condition"""

    cond_name: str | None = Field(None, max_length=100)
    temp_min: float | None = None
    temp_max: float | None = None
    humidity: str | None = Field(None, max_length=50)
    remark: str | None = Field(None, max_length=500)
    status: int | None = None


class StorageConditionResponse(StorageConditionBase, AuditFields):
    """Storage Condition Response"""

    id: int

    class Config:
        from_attributes = True


# ========== 2. Unit ==========


class UnitBase(BaseModel):
    """Unit Base Schema"""

    unit_code: str = Field(..., max_length=50, description="Unit code")
    unit_name: str = Field(..., max_length=50, description="Unit name")
    unit_type: str = Field(..., max_length=30, description="Unit type")
    base_value: float | None = Field(None, description="Conversion base")
    remark: str | None = Field(None, max_length=500, description="Remark")
    status: int = Field(0, description="0-enabled 1-disabled")


class UnitCreate(UnitBase):
    """Create Unit"""

    create_by: int = Field(..., description="Creator")


class UnitUpdate(BaseModel):
    """Update Unit"""

    unit_name: str | None = Field(None, max_length=50)
    unit_type: str | None = Field(None, max_length=30)
    base_value: float | None = None
    remark: str | None = Field(None, max_length=500)
    status: int | None = None


class UnitResponse(UnitBase, AuditFields):
    """Unit Response"""

    id: int

    class Config:
        from_attributes = True


# ========== 11. HPLC Reference Substance ==========


class HplcReferenceBase(BaseModel):
    """HPLC Reference Substance Base"""

    ref_code: str = Field(..., max_length=50, description="Reference code")
    ref_name: str = Field(..., max_length=200, description="Reference name")
    project_name: str | None = Field(None, max_length=100, description="Project")
    internal_batch: str | None = Field(
        None, max_length=50, description="Internal batch"
    )
    cas_no: str | None = Field(None, max_length=50, description="CAS number")
    cat_no: str | None = Field(None, max_length=50, description="Catalog number")
    manufacturer_batch: str | None = Field(
        None, max_length=50, description="Manufacturer batch"
    )
    manufacturer: str | None = Field(None, max_length=200, description="Manufacturer")
    spec: str | None = Field(
        None, max_length=50, description="Specification per bottle (e.g., 100mg)"
    )
    spec_unit: str | None = Field(
        None, max_length=10, description="Specification unit (mg/g)"
    )
    quantity: int | None = Field(None, description="Quantity (bottle count)")
    total_amount: float | None = Field(None, description="Total amount (mg/g)")
    remaining_amount: float | None = Field(None, description="Remaining amount (mg/g)")
    remaining_unit: str | None = Field(
        "mg", max_length=10, description="Remaining amount unit"
    )
    recal_threshold: float | None = Field(
        None, description="Recalibration threshold (mg/g)"
    )
    need_recal: bool = Field(False, description="Need recalibration flag")
    purity: float | None = Field(None, description="Purity %")
    content: float | None = Field(None, description="Content %")
    stock_status: str | None = Field(None, max_length=100, description="Stock status")
    arrival_date: date | None = Field(None, description="Arrival date")
    produce_date: date | None = Field(None, description="Production date")
    expire_date: date | None = Field(None, description="Expiry date")
    recal_cycle_days: int | None = Field(None, description="Recalibration cycle")
    open_date: date | None = Field(None, description="Opening date")
    open_expire_days: int | None = Field(None, description="Opening validity days")
    storage_cond_code: str | None = Field(
        None, max_length=50, description="Storage condition"
    )
    location: str | None = Field(None, max_length=100, description="Location")
    has_coa: bool = Field(False, description="Has COA")
    handover_no: str | None = Field(None, max_length=100, description="Handover number")
    ref_status: int = Field(
        0, description="Status: 0-active 1-used 2-expired 3-scrapped"
    )
    remark: str | None = Field(None, description="Remark")
    attach_file: str | None = Field(None, description="Attachments")


class HplcReferenceCreate(HplcReferenceBase):
    """Create HPLC Reference Substance"""

    create_by: int = Field(0, description="Creator")


class HplcReferenceUpdate(BaseModel):
    """Update HPLC Reference Substance"""

    ref_name: str | None = Field(None, max_length=200)
    project_name: str | None = Field(None, max_length=100)
    internal_batch: str | None = Field(None, max_length=50)
    cas_no: str | None = Field(None, max_length=50)
    cat_no: str | None = Field(None, max_length=50)
    manufacturer_batch: str | None = Field(None, max_length=50)
    manufacturer: str | None = Field(None, max_length=200)
    spec: str | None = Field(None, max_length=50)
    spec_unit: str | None = Field(None, max_length=10)
    quantity: int | None = None
    total_amount: float | None = None
    remaining_amount: float | None = None
    remaining_unit: str | None = Field(None, max_length=10)
    recal_threshold: float | None = None
    need_recal: bool | None = None
    purity: float | None = None
    content: float | None = None
    stock_status: str | None = Field(None, max_length=100)
    arrival_date: date | None = None
    produce_date: date | None = None
    expire_date: date | None = None
    recal_cycle_days: int | None = None
    open_date: date | None = None
    open_expire_days: int | None = None
    storage_cond_code: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=100)
    has_coa: bool | None = None
    handover_no: str | None = Field(None, max_length=100)
    ref_status: int | None = None
    remark: str | None = Field(None)
    attach_file: str | None = Field(None)


class HplcReferenceResponse(HplcReferenceBase, AuditFields):
    """HPLC Reference Substance Response"""

    id: int

    class Config:
        from_attributes = True


class HplcReferenceUsageBase(BaseModel):
    """HPLC Reference Usage Base"""

    ref_id: int = Field(..., description="Reference substance ID")
    usage_amount: float = Field(..., description="Usage amount (mg/g)")
    usage_unit: str = Field("mg", max_length=10, description="Usage unit")
    usage_person: str | None = Field(
        None, max_length=100, description="Person who used"
    )
    usage_purpose: str | None = Field(None, max_length=200, description="Usage purpose")
    usage_date: date | None = Field(None, description="Usage date")
    remark: str | None = Field(None, description="Remark")


class HplcReferenceUsageCreate(HplcReferenceUsageBase):
    """Create HPLC Reference Usage"""

    create_by: int = Field(0, description="Creator")


class HplcReferenceUsageResponse(HplcReferenceUsageBase, AuditFields):
    """HPLC Reference Usage Response"""

    id: int
    ref_code: str
    ref_name: str
    remaining_after: float

    class Config:
        from_attributes = True


# ========== 5. Chromatography Column ==========


class ChromColumnBase(BaseModel):
    """Chromatography Column Base Schema"""

    col_code: str = Field(..., max_length=50, description="Column code (unique)")
    col_type: str = Field(..., max_length=50, description="Stationary phase type")
    spec: str = Field(..., max_length=100, description="Specification")
    manufacturer: str = Field(..., max_length=100, description="Manufacturer")
    serial_no: str = Field(..., max_length=100, description="Original serial number")
    purchase_date: date = Field(..., description="Purchase date")
    use_start_date: date | None = Field(None, description="Start using date")
    max_use_times: int = Field(..., description="Max allowed usage times")
    used_times: int = Field(0, description="Used times")
    storage_cond_code: str = Field(
        ..., max_length=50, description="Storage condition code"
    )
    location: str = Field(..., max_length=100, description="Storage location")
    col_status: int = Field(
        0, description="0-active 1-waiting_clean 2-sealed 3-scrapped"
    )
    column_category: int = Field(0, description="0-HPLC 1-GC")
    apply_method: str | None = Field(
        None, max_length=500, description="Applicable test method"
    )
    attach_file: str | None = Field(None, description="Attachments")
    remark: str | None = Field(None, max_length=500, description="Remark")


class ChromColumnCreate(ChromColumnBase):
    """Create Chromatography Column"""

    pass


class ChromColumnUpdate(BaseModel):
    """Update Chromatography Column"""

    col_type: str | None = Field(None, max_length=50)
    spec: str | None = Field(None, max_length=100)
    manufacturer: str | None = Field(None, max_length=100)
    serial_no: str | None = Field(None, max_length=100)
    purchase_date: date | None = None
    use_start_date: date | None = None
    max_use_times: int | None = None
    used_times: int | None = None
    storage_cond_code: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=100)
    col_status: int | None = None
    column_category: int | None = None
    apply_method: str | None = Field(None, max_length=500)
    attach_file: str | None = None
    remark: str | None = Field(None, max_length=500)


class ChromColumnResponse(ChromColumnBase, AuditFields):
    """Chromatography Column Response"""

    id: int

    class Config:
        from_attributes = True


# ========== 6. Medium (培养基) ==========


class MediumBase(BaseModel):
    """Medium Base Schema"""

    medium_code: str = Field(..., max_length=50, description="Medium code (unique)")
    medium_name: str = Field(..., max_length=100, description="Medium name")
    medium_type: str = Field(..., max_length=50, description="Medium type")
    manufacturer: str = Field(..., max_length=100, description="Manufacturer")
    batch_no: str = Field(..., max_length=50, description="Batch number")
    spec: str = Field(..., max_length=100, description="Specification")
    storage_cond_code: str = Field(
        ..., max_length=50, description="Storage condition code"
    )
    expire_date: date = Field(..., description="Expiration date")
    verify_status: str = Field(..., max_length=20, description="Verification status")
    config_method: str | None = Field(
        None, max_length=500, description="Configuration method"
    )
    stock_num: int = Field(0, description="Stock quantity")
    unit_code: str = Field(..., max_length=20, description="Unit code")
    min_stock: int = Field(0, description="Minimum stock")
    status: int = Field(0, description="0-active 1-inactive")
    attach_file: str | None = Field(None, description="Attachments")
    remark: str | None = Field(None, max_length=500, description="Remark")


class MediumCreate(MediumBase):
    """Create Medium"""

    pass


class MediumUpdate(BaseModel):
    """Update Medium"""

    medium_name: str | None = Field(None, max_length=100)
    medium_type: str | None = Field(None, max_length=50)
    manufacturer: str | None = Field(None, max_length=100)
    batch_no: str | None = Field(None, max_length=50)
    spec: str | None = Field(None, max_length=100)
    storage_cond_code: str | None = Field(None, max_length=50)
    expire_date: date | None = None
    verify_status: str | None = Field(None, max_length=20)
    config_method: str | None = Field(None, max_length=500)
    stock_num: int | None = None
    unit_code: str | None = Field(None, max_length=20)
    min_stock: int | None = None
    status: int | None = None
    attach_file: str | None = None
    remark: str | None = Field(None, max_length=500)


class MediumResponse(MediumBase, AuditFields):
    """Medium Response"""

    id: int

    class Config:
        from_attributes = True


# ========== 7. Standard (标准品) ==========


class StandardBase(BaseModel):
    """Standard Base Schema"""

    std_code: str = Field(..., max_length=50, description="Standard code (unique)")
    std_name: str = Field(..., max_length=200, description="Standard name")
    std_type: str = Field(
        ..., max_length=30, description="Type: national/working/international"
    )
    cas_no: str | None = Field(None, max_length=50, description="CAS number")
    manufacturer: str | None = Field(
        None, max_length=200, description="Source/Manufacturer"
    )
    batch_no: str = Field(..., max_length=50, description="Batch number")
    spec: str | None = Field(None, max_length=100, description="Specification")
    purity: float | None = Field(None, description="Purity %")
    content: float | None = Field(None, description="Content %")
    quantity: int = Field(0, description="Quantity")
    unit_code: str = Field(..., max_length=20, description="Unit code")
    min_stock: int = Field(0, description="Minimum stock alert")
    produce_date: date | None = Field(None, description="Production date")
    expire_date: date | None = Field(None, description="Expiration date")
    storage_cond_code: str = Field(
        ..., max_length=50, description="Storage condition code"
    )
    location: str | None = Field(None, max_length=100, description="Storage location")
    test_item: str | None = Field(
        None, max_length=200, description="Associated test item"
    )
    std_status: int = Field(0, description="0-active 1-used_up 2-expired 3-scrapped")
    attach_file: str | None = Field(None, description="Attachments")
    remark: str | None = Field(None, max_length=500, description="Remark")


class StandardCreate(StandardBase):
    """Create Standard"""

    pass


class StandardUpdate(BaseModel):
    """Update Standard"""

    std_name: str | None = Field(None, max_length=200)
    std_type: str | None = Field(None, max_length=30)
    cas_no: str | None = Field(None, max_length=50)
    manufacturer: str | None = Field(None, max_length=200)
    batch_no: str | None = Field(None, max_length=50)
    spec: str | None = Field(None, max_length=100)
    purity: float | None = None
    content: float | None = None
    quantity: int | None = None
    unit_code: str | None = Field(None, max_length=20)
    min_stock: int | None = None
    produce_date: date | None = None
    expire_date: date | None = None
    storage_cond_code: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=100)
    test_item: str | None = Field(None, max_length=200)
    std_status: int | None = None
    attach_file: str | None = None
    remark: str | None = Field(None, max_length=500)


class StandardResponse(StandardBase, AuditFields):
    """Standard Response"""

    id: int

    class Config:
        from_attributes = True
