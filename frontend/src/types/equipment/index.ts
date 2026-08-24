// Export from equipment.ts (includes bridge types and equipment-specific types)
export * from './equipment'

// Export enums and utility types from individual files
export type { WorkOrderType, WorkOrderPriority, WorkOrderStatus, VerificationResult } from './work-order'
export type { CalibrationType, CalibrationResult, CalibrationPlanStatus } from './calibration'
export type { MaintenancePlanStatus } from './maintenance'
export type { FailureCodeType } from './failure-code'

// Export legacy interfaces from individual files (for backward compatibility)
export type { WorkOrder, WorkOrderFilters, WorkOrderListResponse, WorkOrderStatistics } from './work-order'
export type { CalibrationPlan, CalibrationPlanFilters, CalibrationPlanListResponse, CalibrationRecord, CalibrationRecordFilters, CalibrationRecordListResponse } from './calibration'
export type { SparePart, SparePartFilters, SparePartListResponse, StockWarning, SparePartStockResponse } from './spare-part'
export type { FailureCode } from './failure-code'
export type { InspectionTemplate, InspectionTemplateFilters, InspectionTemplateListResponse, InspectionTemplateItem, InspectionRecordItem, InspectionCompleteInput } from './inspection-template'
export type { MaintenancePlan, MaintenancePlanFilters, MaintenancePlanListResponse } from './maintenance'

// Export request types from individual files
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

// Export common types
export * from './common'
export * from './personnel'
export * from './material'
