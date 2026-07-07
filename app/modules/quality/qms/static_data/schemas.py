"""Static Data Module - Schemas

Pydantic validation schemas for API request/response.
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ========== Common Fields ==========

class AuditFields(BaseModel):
    """Common audit fields for response"""
    create_by: int = Field(..., description='Creator')
    create_time: datetime = Field(..., description='Create time')
    update_by: Optional[int] = Field(None, description='Updater')
    update_time: Optional[datetime] = Field(None, description='Update time')


# ========== 1. Storage Condition ==========

class StorageConditionBase(BaseModel):
    """Storage Condition Base Schema"""
    cond_code: str = Field(..., max_length=50, description='Condition code')
    cond_name: str = Field(..., max_length=100, description='Condition name')
    temp_min: Optional[float] = Field(None, description='Min temperature')
    temp_max: Optional[float] = Field(None, description='Max temperature')
    humidity: Optional[str] = Field(None, max_length=50, description='Humidity')
    remark: Optional[str] = Field(None, max_length=500, description='Remark')
    status: int = Field(0, description='0-enabled 1-disabled')


class StorageConditionCreate(StorageConditionBase):
    """Create Storage Condition"""
    create_by: int = Field(..., description='Creator')


class StorageConditionUpdate(BaseModel):
    """Update Storage Condition"""
    cond_name: Optional[str] = Field(None, max_length=100)
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    humidity: Optional[str] = Field(None, max_length=50)
    remark: Optional[str] = Field(None, max_length=500)
    status: Optional[int] = None


class StorageConditionResponse(StorageConditionBase, AuditFields):
    """Storage Condition Response"""
    id: int

    class Config:
        from_attributes = True


# ========== 2. Unit ==========

class UnitBase(BaseModel):
    """Unit Base Schema"""
    unit_code: str = Field(..., max_length=50, description='Unit code')
    unit_name: str = Field(..., max_length=50, description='Unit name')
    unit_type: str = Field(..., max_length=30, description='Unit type')
    base_value: Optional[float] = Field(None, description='Conversion base')
    remark: Optional[str] = Field(None, max_length=500, description='Remark')
    status: int = Field(0, description='0-enabled 1-disabled')


class UnitCreate(UnitBase):
    """Create Unit"""
    create_by: int = Field(..., description='Creator')


class UnitUpdate(BaseModel):
    """Update Unit"""
    unit_name: Optional[str] = Field(None, max_length=50)
    unit_type: Optional[str] = Field(None, max_length=30)
    base_value: Optional[float] = None
    remark: Optional[str] = Field(None, max_length=500)
    status: Optional[int] = None


class UnitResponse(UnitBase, AuditFields):
    """Unit Response"""
    id: int

    class Config:
        from_attributes = True


# ========== 11. HPLC Reference Substance ==========

class HplcReferenceBase(BaseModel):
    """HPLC Reference Substance Base"""
    ref_code: str = Field(..., max_length=50, description='Reference code')
    ref_name: str = Field(..., max_length=200, description='Reference name')
    project_name: Optional[str] = Field(None, max_length=100, description='Project')
    internal_batch: Optional[str] = Field(None, max_length=50, description='Internal batch')
    cas_no: Optional[str] = Field(None, max_length=50, description='CAS number')
    cat_no: Optional[str] = Field(None, max_length=50, description='Catalog number')
    manufacturer_batch: Optional[str] = Field(None, max_length=50, description='Manufacturer batch')
    manufacturer: Optional[str] = Field(None, max_length=200, description='Manufacturer')
    spec: Optional[str] = Field(None, max_length=50, description='Specification per bottle (e.g., 100mg)')
    spec_unit: Optional[str] = Field(None, max_length=10, description='Specification unit (mg/g)')
    quantity: Optional[int] = Field(None, description='Quantity (bottle count)')
    total_amount: Optional[float] = Field(None, description='Total amount (mg/g)')
    remaining_amount: Optional[float] = Field(None, description='Remaining amount (mg/g)')
    remaining_unit: Optional[str] = Field('mg', max_length=10, description='Remaining amount unit')
    recal_threshold: Optional[float] = Field(None, description='Recalibration threshold (mg/g)')
    need_recal: bool = Field(False, description='Need recalibration flag')
    purity: Optional[float] = Field(None, description='Purity %')
    content: Optional[float] = Field(None, description='Content %')
    stock_status: Optional[str] = Field(None, max_length=100, description='Stock status')
    arrival_date: Optional[date] = Field(None, description='Arrival date')
    produce_date: Optional[date] = Field(None, description='Production date')
    expire_date: Optional[date] = Field(None, description='Expiry date')
    recal_cycle_days: Optional[int] = Field(None, description='Recalibration cycle')
    open_date: Optional[date] = Field(None, description='Opening date')
    open_expire_days: Optional[int] = Field(None, description='Opening validity days')
    storage_cond_code: Optional[str] = Field(None, max_length=50, description='Storage condition')
    location: Optional[str] = Field(None, max_length=100, description='Location')
    has_coa: bool = Field(False, description='Has COA')
    handover_no: Optional[str] = Field(None, max_length=100, description='Handover number')
    ref_status: int = Field(0, description='Status: 0-active 1-used 2-expired 3-scrapped')
    remark: Optional[str] = Field(None, description='Remark')
    attach_file: Optional[str] = Field(None, description='Attachments')


class HplcReferenceCreate(HplcReferenceBase):
    """Create HPLC Reference Substance"""
    create_by: int = Field(0, description='Creator')


class HplcReferenceUpdate(BaseModel):
    """Update HPLC Reference Substance"""
    ref_name: Optional[str] = Field(None, max_length=200)
    project_name: Optional[str] = Field(None, max_length=100)
    internal_batch: Optional[str] = Field(None, max_length=50)
    cas_no: Optional[str] = Field(None, max_length=50)
    cat_no: Optional[str] = Field(None, max_length=50)
    manufacturer_batch: Optional[str] = Field(None, max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=200)
    spec: Optional[str] = Field(None, max_length=50)
    spec_unit: Optional[str] = Field(None, max_length=10)
    quantity: Optional[int] = None
    total_amount: Optional[float] = None
    remaining_amount: Optional[float] = None
    remaining_unit: Optional[str] = Field(None, max_length=10)
    recal_threshold: Optional[float] = None
    need_recal: Optional[bool] = None
    purity: Optional[float] = None
    content: Optional[float] = None
    stock_status: Optional[str] = Field(None, max_length=100)
    arrival_date: Optional[date] = None
    produce_date: Optional[date] = None
    expire_date: Optional[date] = None
    recal_cycle_days: Optional[int] = None
    open_date: Optional[date] = None
    open_expire_days: Optional[int] = None
    storage_cond_code: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    has_coa: Optional[bool] = None
    handover_no: Optional[str] = Field(None, max_length=100)
    ref_status: Optional[int] = None
    remark: Optional[str] = Field(None)
    attach_file: Optional[str] = Field(None)


class HplcReferenceResponse(HplcReferenceBase, AuditFields):
    """HPLC Reference Substance Response"""
    id: int

    class Config:
        from_attributes = True


class HplcReferenceUsageBase(BaseModel):
    """HPLC Reference Usage Base"""
    ref_id: int = Field(..., description='Reference substance ID')
    usage_amount: float = Field(..., description='Usage amount (mg/g)')
    usage_unit: str = Field('mg', max_length=10, description='Usage unit')
    usage_person: Optional[str] = Field(None, max_length=100, description='Person who used')
    usage_purpose: Optional[str] = Field(None, max_length=200, description='Usage purpose')
    usage_date: Optional[date] = Field(None, description='Usage date')
    remark: Optional[str] = Field(None, description='Remark')


class HplcReferenceUsageCreate(HplcReferenceUsageBase):
    """Create HPLC Reference Usage"""
    create_by: int = Field(0, description='Creator')


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
    col_code: str = Field(..., max_length=50, description='Column code (unique)')
    col_type: str = Field(..., max_length=50, description='Stationary phase type')
    spec: str = Field(..., max_length=100, description='Specification')
    manufacturer: str = Field(..., max_length=100, description='Manufacturer')
    serial_no: str = Field(..., max_length=100, description='Original serial number')
    purchase_date: date = Field(..., description='Purchase date')
    use_start_date: Optional[date] = Field(None, description='Start using date')
    max_use_times: int = Field(..., description='Max allowed usage times')
    used_times: int = Field(0, description='Used times')
    storage_cond_code: str = Field(..., max_length=50, description='Storage condition code')
    location: str = Field(..., max_length=100, description='Storage location')
    col_status: int = Field(0, description='0-active 1-waiting_clean 2-sealed 3-scrapped')
    column_category: int = Field(0, description='0-HPLC 1-GC')
    apply_method: Optional[str] = Field(None, max_length=500, description='Applicable test method')
    attach_file: Optional[str] = Field(None, description='Attachments')
    remark: Optional[str] = Field(None, max_length=500, description='Remark')


class ChromColumnCreate(ChromColumnBase):
    """Create Chromatography Column"""
    pass


class ChromColumnUpdate(BaseModel):
    """Update Chromatography Column"""
    col_type: Optional[str] = Field(None, max_length=50)
    spec: Optional[str] = Field(None, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)
    serial_no: Optional[str] = Field(None, max_length=100)
    purchase_date: Optional[date] = None
    use_start_date: Optional[date] = None
    max_use_times: Optional[int] = None
    used_times: Optional[int] = None
    storage_cond_code: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    col_status: Optional[int] = None
    column_category: Optional[int] = None
    apply_method: Optional[str] = Field(None, max_length=500)
    attach_file: Optional[str] = None
    remark: Optional[str] = Field(None, max_length=500)


class ChromColumnResponse(ChromColumnBase, AuditFields):
    """Chromatography Column Response"""
    id: int

    class Config:
        from_attributes = True


# ========== 6. Medium (培养基) ==========

class MediumBase(BaseModel):
    """Medium Base Schema"""
    medium_code: str = Field(..., max_length=50, description='Medium code (unique)')
    medium_name: str = Field(..., max_length=100, description='Medium name')
    medium_type: str = Field(..., max_length=50, description='Medium type')
    manufacturer: str = Field(..., max_length=100, description='Manufacturer')
    batch_no: str = Field(..., max_length=50, description='Batch number')
    spec: str = Field(..., max_length=100, description='Specification')
    storage_cond_code: str = Field(..., max_length=50, description='Storage condition code')
    expire_date: date = Field(..., description='Expiration date')
    verify_status: str = Field(..., max_length=20, description='Verification status')
    config_method: Optional[str] = Field(None, max_length=500, description='Configuration method')
    stock_num: int = Field(0, description='Stock quantity')
    unit_code: str = Field(..., max_length=20, description='Unit code')
    min_stock: int = Field(0, description='Minimum stock')
    status: int = Field(0, description='0-active 1-inactive')
    attach_file: Optional[str] = Field(None, description='Attachments')
    remark: Optional[str] = Field(None, max_length=500, description='Remark')


class MediumCreate(MediumBase):
    """Create Medium"""
    pass


class MediumUpdate(BaseModel):
    """Update Medium"""
    medium_name: Optional[str] = Field(None, max_length=100)
    medium_type: Optional[str] = Field(None, max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=100)
    batch_no: Optional[str] = Field(None, max_length=50)
    spec: Optional[str] = Field(None, max_length=100)
    storage_cond_code: Optional[str] = Field(None, max_length=50)
    expire_date: Optional[date] = None
    verify_status: Optional[str] = Field(None, max_length=20)
    config_method: Optional[str] = Field(None, max_length=500)
    stock_num: Optional[int] = None
    unit_code: Optional[str] = Field(None, max_length=20)
    min_stock: Optional[int] = None
    status: Optional[int] = None
    attach_file: Optional[str] = None
    remark: Optional[str] = Field(None, max_length=500)


class MediumResponse(MediumBase, AuditFields):
    """Medium Response"""
    id: int

    class Config:
        from_attributes = True


# ========== 7. Standard (标准品) ==========

class StandardBase(BaseModel):
    """Standard Base Schema"""
    std_code: str = Field(..., max_length=50, description='Standard code (unique)')
    std_name: str = Field(..., max_length=200, description='Standard name')
    std_type: str = Field(..., max_length=30, description='Type: national/working/international')
    cas_no: Optional[str] = Field(None, max_length=50, description='CAS number')
    manufacturer: Optional[str] = Field(None, max_length=200, description='Source/Manufacturer')
    batch_no: str = Field(..., max_length=50, description='Batch number')
    spec: Optional[str] = Field(None, max_length=100, description='Specification')
    purity: Optional[float] = Field(None, description='Purity %')
    content: Optional[float] = Field(None, description='Content %')
    quantity: int = Field(0, description='Quantity')
    unit_code: str = Field(..., max_length=20, description='Unit code')
    min_stock: int = Field(0, description='Minimum stock alert')
    produce_date: Optional[date] = Field(None, description='Production date')
    expire_date: Optional[date] = Field(None, description='Expiration date')
    storage_cond_code: str = Field(..., max_length=50, description='Storage condition code')
    location: Optional[str] = Field(None, max_length=100, description='Storage location')
    test_item: Optional[str] = Field(None, max_length=200, description='Associated test item')
    std_status: int = Field(0, description='0-active 1-used_up 2-expired 3-scrapped')
    attach_file: Optional[str] = Field(None, description='Attachments')
    remark: Optional[str] = Field(None, max_length=500, description='Remark')


class StandardCreate(StandardBase):
    """Create Standard"""
    pass


class StandardUpdate(BaseModel):
    """Update Standard"""
    std_name: Optional[str] = Field(None, max_length=200)
    std_type: Optional[str] = Field(None, max_length=30)
    cas_no: Optional[str] = Field(None, max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=200)
    batch_no: Optional[str] = Field(None, max_length=50)
    spec: Optional[str] = Field(None, max_length=100)
    purity: Optional[float] = None
    content: Optional[float] = None
    quantity: Optional[int] = None
    unit_code: Optional[str] = Field(None, max_length=20)
    min_stock: Optional[int] = None
    produce_date: Optional[date] = None
    expire_date: Optional[date] = None
    storage_cond_code: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    test_item: Optional[str] = Field(None, max_length=200)
    std_status: Optional[int] = None
    attach_file: Optional[str] = None
    remark: Optional[str] = Field(None, max_length=500)


class StandardResponse(StandardBase, AuditFields):
    """Standard Response"""
    id: int

    class Config:
        from_attributes = True