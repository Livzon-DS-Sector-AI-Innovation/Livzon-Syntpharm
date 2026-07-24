import type { WorkOrder, Equipment, CalibrationPlan, CalibrationRecord, MaintenancePlan, FailureCode, SparePart, InspectionTemplate, InspectionTemplateItem } from '@/types/equipment'

export interface Maintainer {
  user_id: string
  name: string
  employee_no: string | null
  department_id?: string
}

export interface DepartmentOption {
  id: string
  name: string
}

export async function fetchEquipmentsClient(params?: Record<string, unknown>): Promise<{ items: Equipment[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) searchParams.set(k, String(v)) })
  }
  const res = await fetch(`/api/v1/equipment/equipments?${searchParams.toString()}`)
  const json = await res.json()
  return { items: json.data || [], total: json.meta?.total || 0 }
}

export async function fetchEquipmentStatisticsClient(): Promise<any> {
  const res = await fetch('/api/v1/equipment/equipments/statistics')
  const json = await res.json()
  return json.data
}

export async function fetchCategoriesClient(): Promise<any[]> {
  const res = await fetch('/api/v1/equipment/categories')
  const json = await res.json()
  return json.data || []
}

export async function fetchLocationsClient(): Promise<any[]> {
  const res = await fetch('/api/v1/equipment/locations')
  const json = await res.json()
  return json.data || []
}

export async function fetchDepartmentsClient(): Promise<DepartmentOption[]> {
  const res = await fetch('/api/v1/equipment/departments')
  const json = await res.json()
  return json.data || []
}

export async function fetchAllUsersClient(): Promise<Maintainer[]> {
  const res = await fetch('/api/v1/equipment/maintenance/personnel')
  if (!res.ok) return []
  const json = await res.json()
  return json.data || []
}

export async function fetchMaintainersClient(): Promise<Maintainer[]> {
  const res = await fetch('/api/v1/equipment/maintenance/personnel')
  if (!res.ok) return []
  const json = await res.json()
  return json.data || []
}

export async function fetchWorkOrdersClient(params?: Record<string, unknown>): Promise<{ items: WorkOrder[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) searchParams.set(k, String(v)) })
  }
  const res = await fetch(`/api/v1/equipment/maintenance/work-orders?${searchParams.toString()}`)
  const json = await res.json()
  return { items: json.data || [], total: json.meta?.total || 0 }
}

export async function fetchWorkOrderByIdClient(id: string): Promise<WorkOrder> {
  const res = await fetch(`/api/v1/equipment/maintenance/work-orders/${id}`)
  const json = await res.json()
  return json.data
}

export async function fetchWorkOrderStatisticsClient(): Promise<any> {
  const res = await fetch('/api/v1/equipment/maintenance/work-orders/statistics')
  const json = await res.json()
  return json.data
}

export async function fetchFailureCodesClient(type: string): Promise<FailureCode[]> {
  const res = await fetch(`/api/v1/equipment/maintenance/failure-codes/${type}`)
  const json = await res.json()
  return json.data || []
}

export async function fetchCalibrationPlansClient(params?: Record<string, unknown>): Promise<{ items: CalibrationPlan[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) searchParams.set(k, String(v)) })
  }
  const res = await fetch(`/api/v1/equipment/maintenance/calibration/plans?${searchParams.toString()}`)
  const json = await res.json()
  return { items: json.data || [], total: json.meta?.total || 0 }
}

export async function fetchCalibrationRecordsClient(params?: Record<string, unknown>): Promise<{ items: CalibrationRecord[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) searchParams.set(k, String(v)) })
  }
  const res = await fetch(`/api/v1/equipment/maintenance/calibration/records?${searchParams.toString()}`)
  const json = await res.json()
  return { items: json.data || [], total: json.meta?.total || 0 }
}

export async function fetchMaintenancePlansClient(params?: Record<string, unknown>): Promise<{ items: MaintenancePlan[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) searchParams.set(k, String(v)) })
  }
  const res = await fetch(`/api/v1/equipment/maintenance/plans?${searchParams.toString()}`)
  const json = await res.json()
  return { items: json.data || [], total: json.meta?.total || 0 }
}

export async function fetchSparePartsClient(params?: Record<string, unknown>): Promise<{ items: SparePart[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) searchParams.set(k, String(v)) })
  }
  const res = await fetch(`/api/v1/equipment/spare-parts?${searchParams.toString()}`)
  const json = await res.json()
  return { items: json.data || [], total: json.meta?.total || 0 }
}

export async function fetchInspectionTemplatesClient(params?: Record<string, unknown>): Promise<{ items: InspectionTemplate[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) searchParams.set(k, String(v)) })
  }
  const res = await fetch(`/api/v1/equipment/maintenance/inspection-templates?${searchParams.toString()}`)
  const json = await res.json()
  return { items: json.data || [], total: json.meta?.total || 0 }
}

export async function fetchInspectionTemplateItemsClient(templateId: string): Promise<InspectionTemplateItem[]> {
  const res = await fetch(`/api/v1/equipment/maintenance/inspection-templates/${templateId}/items`)
  const json = await res.json()
  return json.data || []
}

export async function fetchInspectionTemplateByIdClient(templateId: string): Promise<InspectionTemplate> {
  const res = await fetch(`/api/v1/equipment/maintenance/inspection-templates/${templateId}`)
  const json = await res.json()
  return json.data
}

export async function fetchWorkOrderMaterialsClient(workOrderId: string): Promise<any[]> {
  const res = await fetch(`/api/v1/equipment/maintenance/work-orders/${workOrderId}/materials`)
  const json = await res.json()
  return json.data || []
}

export async function fetchClaimTimeoutConfigClient(): Promise<any> {
  const res = await fetch('/api/v1/equipment/maintenance/config/claim-timeout')
  const json = await res.json()
  return json.data || {}
}

export async function fetchStockWarningsClient(): Promise<any[]> {
  const res = await fetch('/api/v1/equipment/spare-parts/stock-warnings')
  const json = await res.json()
  return json.data || []
}

export async function fetchOverdueMaintenancePlansClient(): Promise<MaintenancePlan[]> {
  const res = await fetch('/api/v1/equipment/maintenance/plans/overdue')
  const json = await res.json()
  return json.data || []
}
