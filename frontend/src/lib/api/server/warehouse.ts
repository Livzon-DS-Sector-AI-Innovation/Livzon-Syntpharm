import type {
  PackagingMaterial,
  PackagingMaterialListResponse,
  ProductInventory,
  ProductInventoryListResponse,
  RawMaterial,
  RawMaterialListResponse,
  WarehouseFeishuBusinessDomain,
  WarehouseFeishuConfig,
  WarehouseFeishuConfigUpsert,
  WarehouseFeishuConnectivityResult,
  WarehouseFeishuRawRecordData,
  WarehouseFeishuTable,
  WarehouseFeishuTableBatchEnablePayload,
  WarehouseFeishuTableSyncResult,
  WarehouseFeishuWsStatus,
} from '@/types/warehouse'
import { apiFetch, unwrapResponse } from './base'

const BASE = '/api/v1/warehouse'

export async function fetchModuleInfo(): Promise<{
  code: string
  name: string
  description: string
}> {
  return unwrapResponse(await apiFetch<{
    code: number
    data: { code: string; name: string; description: string }
    message?: string
    meta?: unknown
  }>(BASE))
}

export async function fetchRawMaterials(): Promise<RawMaterial[]> {
  return unwrapResponse(await apiFetch<RawMaterialListResponse>(`${BASE}/raw-materials`)) || []
}

export async function fetchPackagingMaterials(): Promise<PackagingMaterial[]> {
  return unwrapResponse(await apiFetch<PackagingMaterialListResponse>(`${BASE}/packaging-materials`)) || []
}

export async function fetchProducts(): Promise<ProductInventory[]> {
  return unwrapResponse(await apiFetch<ProductInventoryListResponse>(`${BASE}/products`)) || []
}

export async function fetchWarehouseFeishuConfig(): Promise<WarehouseFeishuConfig> {
  return unwrapResponse(await apiFetch<{ code: number; data: WarehouseFeishuConfig; message?: string; meta?: unknown }>(`${BASE}/feishu-config`))
}

export async function fetchWarehouseFeishuTables(): Promise<WarehouseFeishuTable[]> {
  return fetchWarehouseFeishuTablesByParams()
}

export async function fetchWarehouseFeishuTablesByParams(params?: {
  business_domain?: WarehouseFeishuBusinessDomain
  keyword?: string
  enabled?: boolean
}): Promise<WarehouseFeishuTable[]> {
  const search = new URLSearchParams()
  if (params?.business_domain) search.set('business_domain', params.business_domain)
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.enabled !== undefined) search.set('enabled', String(params.enabled))
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return unwrapResponse(await apiFetch<{ code: number; data: WarehouseFeishuTable[]; message?: string; meta?: unknown }>(`${BASE}/feishu/tables${suffix}`)) || []
}

export async function fetchWarehouseFeishuDomainRecords(
  businessDomain: WarehouseFeishuBusinessDomain,
  params?: {
    table_id?: string
    keyword?: string
    field?: string
    field_operator?: string
    field_value?: string
    page?: number
    page_size?: number
  },
): Promise<WarehouseFeishuRawRecordData> {
  const search = new URLSearchParams()
  if (params?.table_id) search.set('table_id', params.table_id)
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.field) search.set('field', params.field)
  if (params?.field_operator) search.set('field_operator', params.field_operator)
  if (params?.field_value) search.set('field_value', params.field_value)
  if (params?.page) search.set('page', String(params.page))
  if (params?.page_size) search.set('page_size', String(params.page_size))
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return unwrapResponse(await apiFetch<{ code: number; data: WarehouseFeishuRawRecordData; message?: string; meta?: unknown }>(`${BASE}/feishu/domains/${businessDomain}/records${suffix}`))
}

export async function fetchWarehouseFeishuTableRecords(
  tableId: string,
  params?: {
    keyword?: string
    field?: string
    field_operator?: string
    field_value?: string
    page?: number
    page_size?: number
  },
): Promise<WarehouseFeishuRawRecordData> {
  const search = new URLSearchParams()
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.field) search.set('field', params.field)
  if (params?.field_operator) search.set('field_operator', params.field_operator)
  if (params?.field_value) search.set('field_value', params.field_value)
  if (params?.page) search.set('page', String(params.page))
  if (params?.page_size) search.set('page_size', String(params.page_size))
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return unwrapResponse(await apiFetch<{ code: number; data: WarehouseFeishuRawRecordData; message?: string; meta?: unknown }>(`${BASE}/feishu/tables/${tableId}/records${suffix}`))
}

export async function fetchWarehouseFeishuWsStatus(): Promise<WarehouseFeishuWsStatus> {
  return unwrapResponse(await apiFetch<{ code: number; data: WarehouseFeishuWsStatus; message?: string; meta?: unknown }>(`${BASE}/feishu/ws/status`))
}

interface ApiResponse<T> {
  code: number
  data: T
  message?: string
}

export async function saveWarehouseFeishuConfig(
  authToken: string | undefined,
  data: WarehouseFeishuConfigUpsert,
): Promise<ApiResponse<WarehouseFeishuConfig>> {
  return apiFetch<ApiResponse<WarehouseFeishuConfig>>(`${BASE}/feishu-config`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function testWarehouseFeishuConfig(
  authToken: string | undefined,
  data: WarehouseFeishuConfigUpsert,
): Promise<ApiResponse<WarehouseFeishuConnectivityResult>> {
  return apiFetch<ApiResponse<WarehouseFeishuConnectivityResult>>(`${BASE}/feishu-config/test`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function refreshWarehouseFeishuTables(
  authToken: string | undefined,
): Promise<ApiResponse<WarehouseFeishuTable[]>> {
  return apiFetch<ApiResponse<WarehouseFeishuTable[]>>(`${BASE}/feishu/tables/refresh`, {
    method: 'POST',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function setWarehouseFeishuTableEnabled(
  authToken: string | undefined,
  tableId: string,
  isEnabled: boolean,
): Promise<ApiResponse<WarehouseFeishuTable>> {
  return apiFetch<ApiResponse<WarehouseFeishuTable>>(`${BASE}/feishu/tables/${tableId}/enabled`, {
    method: 'PATCH',
    body: JSON.stringify({ is_enabled: isEnabled }),
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function setWarehouseFeishuTablesEnabled(
  authToken: string | undefined,
  tableIds: string[],
  isEnabled: boolean,
): Promise<ApiResponse<WarehouseFeishuTable[]>> {
  const body: WarehouseFeishuTableBatchEnablePayload = {
    table_ids: tableIds,
    is_enabled: isEnabled,
  }
  return apiFetch<ApiResponse<WarehouseFeishuTable[]>>(`${BASE}/feishu/tables/enabled/batch`, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function syncWarehouseFeishuTable(
  authToken: string | undefined,
  tableId: string,
): Promise<ApiResponse<WarehouseFeishuTableSyncResult>> {
  return apiFetch<ApiResponse<WarehouseFeishuTableSyncResult>>(`${BASE}/feishu/tables/${tableId}/sync`, {
    method: 'POST',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function restartWarehouseFeishuWs(
  authToken: string | undefined,
): Promise<ApiResponse<WarehouseFeishuWsStatus>> {
  return apiFetch<ApiResponse<WarehouseFeishuWsStatus>>(`${BASE}/feishu/ws/restart`, {
    method: 'POST',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}