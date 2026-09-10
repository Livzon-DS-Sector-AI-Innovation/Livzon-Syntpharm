// Export response types from bridge file (these are the source of truth)
export type {
  EquipmentCategory,
  EquipmentCategoryTree,
  Location,
  LocationTree,
  Equipment,
  FailureCode,
  SparePart,
  WorkOrder,
  CalibrationPlan,
  InspectionTemplate,
  InspectionTemplateItem,
  MaintenancePlan,
} from './generated-bridge'

// Export filter and statistics types from bridge
export type {
  EquipmentFilters,
  WorkOrderFilters,
  SparePartFilters,
  CalibrationPlanFilters,
  InspectionTemplateFilters,
  MaintenancePlanFilters,
  EquipmentStatistics,
  WorkOrderStatistics,
  PaginatedResponse,
} from './generated-bridge'

// Export response types (new naming)
export type {
  EquipmentCategoryResponse,
  LocationResponse,
  EquipmentResponse,
  FailureCodeResponse,
  SparePartResponse,
  WorkOrderResponse,
  CalibrationPlanResponse,
  InspectionTemplateResponse,
  InspectionTemplateItemResponse,
  MaintenancePlanResponse,
} from './generated-bridge'

// Export enums and utility types from individual files
export type { EquipmentStatus, EquipmentImportance, EquipmentClass } from './equipment'
export type { WorkOrderType, WorkOrderPriority, WorkOrderStatus, VerificationResult } from './work-order'
export type { CalibrationType, CalibrationResult, CalibrationPlanStatus } from './calibration'
export type { MaintenancePlanStatus } from './maintenance'
export type { FailureCodeType } from './failure-code'

// Export request types from individual files
export type { 
  CreateCategoryInput,
  UpdateCategoryInput,
  CreateEquipmentInput,
  UpdateEquipmentInput,
  CreateLocationInput,
  UpdateLocationInput,
  EquipmentListResponse,
  ImportResult,
  ImportRowError,
} from './equipment'
export type { 
  CreateWorkOrderInput, 
  UpdateWorkOrderInput, 
  AssignWorkOrderInput, 
  CompleteWorkOrderInput, 
  VerifyWorkOrderInput 
} from './work-order'
export type { 
  CreateCalibrationPlanInput, 
  UpdateCalibrationPlanInput, 
  CreateCalibrationRecordInput
} from './calibration'
export type { 
  CreateMaintenancePlanInput, 
  UpdateMaintenancePlanInput 
} from './maintenance'
export type { 
  CreateInspectionTemplateInput, 
  UpdateInspectionTemplateInput, 
  CreateInspectionTemplateItemInput, 
  UpdateInspectionTemplateItemInput 
} from './inspection-template'
export type { 
  CreateFailureCodeInput, 
  UpdateFailureCodeInput 
} from './failure-code'
export type {
  CreateSparePartInput,
  UpdateSparePartInput,
  StockInboundInput,
  StockAdjustInput
} from './spare-part'

// Export list response types from individual files
export type { WorkOrderListResponse } from './work-order'
export type { CalibrationPlanListResponse, CalibrationRecord, CalibrationRecordFilters, CalibrationRecordListResponse } from './calibration'
export type { SparePartListResponse, StockWarning, SparePartStockResponse } from './spare-part'
export type { InspectionTemplateListResponse, InspectionRecordItem, InspectionCompleteInput } from './inspection-template'
export type { MaintenancePlanListResponse } from './maintenance'

// Export common types
export * from './common'
export * from './personnel'
export * from './material'
