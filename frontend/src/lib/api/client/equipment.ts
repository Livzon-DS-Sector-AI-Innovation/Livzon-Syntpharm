import type { DepartmentOption } from '@/types/equipment/generated-bridge'
export type { DepartmentOption } from '@/types/equipment/generated-bridge'
import type { Personnel } from '@/types/equipment-personnel'
import {
  EquipmentCategory, Location, EquipmentFilters, EquipmentListResponse, EquipmentStatistics,
  FailureCode, WorkOrderFilters, WorkOrderListResponse, WorkOrderStatistics, WorkOrder,
  CalibrationPlanFilters, CalibrationPlanListResponse, CalibrationPlan,
  CalibrationRecordFilters, CalibrationRecordListResponse,
  SparePartFilters, SparePartListResponse, SparePart, StockWarning, SparePartStockResponse,
  MaintenancePlanFilters, MaintenancePlanListResponse, MaintenancePlan,
  InspectionTemplateFilters, InspectionTemplateListResponse, InspectionTemplate, InspectionTemplateItem,
  MaterialRecord, ClaimTimeoutConfig, Maintainer, WorkOrderImage,
} from '@/types/equipment/generated-bridge'
import { apiGet, apiFetchPaginated, fetchApi } from '@/lib/api/client'

const API_BASE = '/api/v1'

// Query parameter types (manually defined to avoid type resolution issues)
export interface GetEquipmentsQuery {
  category_id?: string | null
  location_id?: string | null
  department_id?: string | null
  status?: string | null
  keyword?: string | null
  page?: number
  page_size?: number
}

export interface GetStatisticsQuery {
  category_id?: string | null
  location_id?: string | null
  department_id?: string | null
  status?: string | null
}



// ═══════════════════════════════════════════════════════════
//  设备分类
// ═══════════════════════════════════════════════════════════
export async function fetchCategories(): Promise<EquipmentCategory[]> {
  return apiGet(`${API_BASE}/equipment/categories`)
}

export async function fetchCategoryTree(): Promise<EquipmentCategory[]> {
  return apiGet(`${API_BASE}/equipment/categories?tree=true`)
}

// ═══════════════════════════════════════════════════════════
//  位置管理
// ═══════════════════════════════════════════════════════════
export async function fetchLocations(): Promise<Location[]> {
  return apiGet(`${API_BASE}/equipment/locations`)
}

export async function fetchLocationTree(): Promise<Location[]> {
  return apiGet(`${API_BASE}/equipment/locations?tree=true`)
}

// ═══════════════════════════════════════════════════════════
//  设备管理
// ═══════════════════════════════════════════════════════════
export async function fetchEquipments(filters: EquipmentFilters = {}): Promise<EquipmentListResponse> {
  const params = new URLSearchParams()
  if (filters.category_id) params.append('category_id', filters.category_id)
  if (filters.location_id) params.append('location_id', filters.location_id)
  if (filters.department_id) params.append('department_id', filters.department_id)
  if (filters.status) params.append('status', filters.status)
  if (filters.keyword) params.append('keyword', filters.keyword)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())

  const queryString = params.toString()
  const url = queryString
    ? `${API_BASE}/equipment/equipments?${queryString}`
    : `${API_BASE}/equipment/equipments`

  return apiFetchPaginated(url)
}

// Use GetStatisticsQuery from generated types

export async function fetchEquipmentStatistics(filters: GetStatisticsQuery = {}): Promise<EquipmentStatistics> {
  const params = new URLSearchParams()
  if (filters.category_id) params.append('category_id', filters.category_id)
  if (filters.location_id) params.append('location_id', filters.location_id)
  if (filters.department_id) params.append('department_id', filters.department_id)
  if (filters.status) params.append('status', filters.status)

  const queryString = params.toString()
  const url = queryString
    ? `${API_BASE}/equipment/equipments/statistics?${queryString}`
    : `${API_BASE}/equipment/equipments/statistics`

  return apiGet(url)
}

// ═══════════════════════════════════════════════════════════
//  故障代码
// ═══════════════════════════════════════════════════════════
export async function fetchFailureCodes(type: 'symptoms' | 'causes' | 'actions'): Promise<FailureCode[]> {
  return apiGet(`${API_BASE}/equipment/maintenance/failure-codes/${type}`)
}

// ═══════════════════════════════════════════════════════════
//  维修工单
// ═══════════════════════════════════════════════════════════
export async function fetchWorkOrders(filters: WorkOrderFilters = {}): Promise<WorkOrderListResponse> {
  const params = new URLSearchParams()
  if (filters.status) params.append('status', filters.status)
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.priority) params.append('priority', filters.priority)
  if (filters.order_type) params.append('order_type', filters.order_type)
  if (filters.exclude_status) params.append('exclude_status', filters.exclude_status)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())

  const queryString = params.toString()
  const url = queryString
    ? `${API_BASE}/equipment/maintenance/work-orders?${queryString}`
    : `${API_BASE}/equipment/maintenance/work-orders`

  return apiFetchPaginated(url)
}

export async function fetchWorkOrderStatistics(exclude_status?: string): Promise<WorkOrderStatistics> {
  const params = new URLSearchParams()
  if (exclude_status) params.append('exclude_status', exclude_status)
  const qs = params.toString()
  return apiGet(`${API_BASE}/equipment/maintenance/work-ordersstatistics${qs ? `?${qs}` : ''}`)
}

export async function fetchWorkOrderById(id: string): Promise<WorkOrder> {
  return apiGet(`${API_BASE}/equipment/maintenance/work-orders${id}`)
}

// ═══════════════════════════════════════════════════════════
//  校准计划
// ═══════════════════════════════════════════════════════════
export async function fetchCalibrationPlans(filters: CalibrationPlanFilters = {}): Promise<CalibrationPlanListResponse> {
  const params = new URLSearchParams()
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.status) params.append('status', filters.status)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())

  const queryString = params.toString()
  const url = queryString
    ? `${API_BASE}/equipment/maintenance/calibration/plans?${queryString}`
    : `${API_BASE}/equipment/maintenance/calibration/plans`

  return apiFetchPaginated(url)
}

export async function fetchCalibrationPlanById(id: string): Promise<CalibrationPlan> {
  return apiGet(`${API_BASE}/equipment/maintenance/calibration/plans/${id}`)
}

// ═══════════════════════════════════════════════════════════
//  校准记录
// ═══════════════════════════════════════════════════════════
export async function fetchCalibrationRecords(filters: CalibrationRecordFilters = {}): Promise<CalibrationRecordListResponse> {
  const params = new URLSearchParams()
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.plan_id) params.append('plan_id', filters.plan_id)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())

  const queryString = params.toString()
  const url = queryString
    ? `${API_BASE}/equipment/maintenance/calibration/records?${queryString}`
    : `${API_BASE}/equipment/maintenance/calibration/records`

  return apiFetchPaginated(url)
}

// ═══════════════════════════════════════════════════════════
//  备件管理
// ═══════════════════════════════════════════════════════════
export async function fetchSpareParts(filters: SparePartFilters = {}): Promise<SparePartListResponse> {
  const params = new URLSearchParams()
  if (filters.category) params.append('category', filters.category)
  if (filters.keyword) params.append('keyword', filters.keyword)
  if (filters.is_active !== undefined) params.append('is_active', filters.is_active.toString())
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())

  const queryString = params.toString()
  const url = queryString
    ? `${API_BASE}/equipment/spare-parts/?${queryString}`
    : `${API_BASE}/equipment/spare-parts/`

  return apiFetchPaginated(url)
}

export async function fetchSparePartById(id: string): Promise<SparePart> {
  return apiGet(`${API_BASE}/equipment/spare-parts/${id}`)
}

export async function fetchStockWarnings(): Promise<StockWarning[]> {
  return apiGet(`${API_BASE}/equipment/spare-parts/stock/warnings`)
}

export async function fetchSparePartStock(id: string): Promise<SparePartStockResponse> {
  return apiGet(`${API_BASE}/equipment/spare-parts/${id}/stock`)
}

// ═══════════════════════════════════════════════════════════
//  维护计划
// ═══════════════════════════════════════════════════════════
export async function fetchMaintenancePlans(filters: MaintenancePlanFilters = {}): Promise<MaintenancePlanListResponse> {
  const params = new URLSearchParams()
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.category_id) params.append('category_id', filters.category_id)
  if (filters.status) params.append('status', filters.status)
  if (filters.keyword) params.append('keyword', filters.keyword)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())

  const queryString = params.toString()
  const url = queryString
    ? `${API_BASE}/equipment/maintenance/plans?${queryString}`
    : `${API_BASE}/equipment/maintenance/plans`

  return apiFetchPaginated(url)
}

export async function fetchMaintenancePlanById(id: string): Promise<MaintenancePlan> {
  return apiGet(`${API_BASE}/equipment/maintenance/plans${id}`)
}

export async function fetchOverdueMaintenancePlans(days?: number): Promise<MaintenancePlan[]> {
  const params = days ? `?days=${days}` : ''
  return apiGet(`${API_BASE}/equipment/maintenance/plansoverdue${params}`)
}

// ═══════════════════════════════════════════════════════════
//  巡检模板
// ═══════════════════════════════════════════════════════════
export async function fetchInspectionTemplates(filters: InspectionTemplateFilters = {}): Promise<InspectionTemplateListResponse> {
  const params = new URLSearchParams()
  if (filters.equipment_category_id) params.append('equipment_category_id', filters.equipment_category_id)
  if (filters.is_active !== undefined) params.append('is_active', filters.is_active.toString())
  if (filters.keyword) params.append('keyword', filters.keyword)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())

  const queryString = params.toString()
  const url = queryString
    ? `${API_BASE}/equipment/maintenance/inspection-templates/?${queryString}`
    : `${API_BASE}/equipment/maintenance/inspection-templates/`

  return apiFetchPaginated(url)
}

export async function fetchInspectionTemplateById(id: string): Promise<InspectionTemplate> {
  return apiGet(`${API_BASE}/equipment/maintenance/inspection-templates/${id}`)
}

// ═══════════════════════════════════════════════════════════
//  工单物料
// ═══════════════════════════════════════════════════════════
export async function fetchWorkOrderMaterials(workOrderId: string): Promise<MaterialRecord[]> {
  return apiGet(`${API_BASE}/equipment/maintenance/work-orders${workOrderId}/materials`)
}

// ═══════════════════════════════════════════════════════════
//  部门列表
// ═══════════════════════════════════════════════════════════

export async function fetchDepartments(): Promise<DepartmentOption[]> {
  return apiGet(`${API_BASE}/equipment/departments`)
}

// ═══════════════════════════════════════════════════════════
//  Client-only exports (direct fetch wrappers)
// ═══════════════════════════════════════════════════════════

export async function fetchMaintainersClient(): Promise<Maintainer[]> {
  return await apiGet(`${API_BASE}/equipment/maintenance/staff/maintainers`) || []
}

export async function fetchAllUsersClient(): Promise<Maintainer[]> {
  return await apiGet(`${API_BASE}/equipment/maintenance/staff/all-users`) || []
}

export async function fetchWorkOrderImagesClient(workOrderId: string): Promise<WorkOrderImage[]> {
  return await apiGet(`${API_BASE}/equipment/maintenance/work-orders${workOrderId}/images`) || []
}

export async function fetchClaimTimeoutConfigClient(): Promise<ClaimTimeoutConfig> {
  return await apiGet<ClaimTimeoutConfig>(`${API_BASE}/equipment/maintenance/config/claim-timeout`)
    || { emergency: 15, high: 30, medium: 60, low: 120 }
}

export async function fetchPersonnelList(_params?: Record<string, unknown>): Promise<Personnel[]> {
  return await apiGet<Personnel[]>(`${API_BASE}/identity/personnel?page_size=1000`) || []
}

// ═══════════════════════════════════════════════════════════
//  Client aliases with null-to-undefined coercion
// ═══════════════════════════════════════════════════════════

// Use GetEquipmentsQuery from generated types

export async function fetchEquipmentsClient(params: GetEquipmentsQuery = {}): Promise<EquipmentListResponse> {
  return fetchEquipments({
    category_id: params.category_id ?? undefined,
    location_id: params.location_id ?? undefined,
    department_id: params.department_id ?? undefined,
    status: params.status ?? undefined,
    keyword: params.keyword ?? undefined,
    page: params.page ?? undefined,
    page_size: params.page_size ?? undefined,
  })
}

export const fetchEquipmentStatisticsClient = fetchEquipmentStatistics
export const fetchCategoriesClient = fetchCategories
export const fetchLocationsClient = fetchLocations
export const fetchFailureCodesClient = fetchFailureCodes
export const fetchWorkOrdersClient = fetchWorkOrders
export const fetchWorkOrderStatisticsClient = fetchWorkOrderStatistics
export const fetchWorkOrderByIdClient = fetchWorkOrderById
export const fetchCalibrationPlansClient = fetchCalibrationPlans
export const fetchCalibrationRecordsClient = fetchCalibrationRecords
export const fetchSparePartsClient = fetchSpareParts
export const fetchSparePartByIdClient = fetchSparePartById
export const fetchStockWarningsClient = fetchStockWarnings
export const fetchMaintenancePlansClient = fetchMaintenancePlans
export const fetchOverdueMaintenancePlansClient = fetchOverdueMaintenancePlans
export async function fetchInspectionTemplateItemsClient(templateId: string): Promise<InspectionTemplateItem[]> {
  return await apiGet<InspectionTemplateItem[]>(`${API_BASE}/equipment/maintenance/inspection-templates/${templateId}/items`)
}

export const fetchInspectionTemplatesClient = fetchInspectionTemplates
export const fetchInspectionTemplateByIdClient = fetchInspectionTemplateById
export const fetchWorkOrderMaterialsClient = fetchWorkOrderMaterials
export const fetchDepartmentsClient = fetchDepartments
/**
 * 批量删除设备
 */
export async function batchDeleteEquipments(ids: string[]): Promise<any> {
  return await fetchApi<any>(`${API_BASE}/equipment/equipments/batch-delete`, {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
}
