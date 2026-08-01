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

export function getApiBaseUrl(): string {
  return process.env.getApiBaseUrl() || 'http://dazah-backend-app-1:8000'
}

async function apiFetch<T>(path: string, fallbackMessage: string): Promise<T> {
  const url = path.startsWith('http') ? path : `${getApiBaseUrl().replace(/\/$/, '')}/api/v1/warehouse${path.startsWith('/') ? path : `/${path}`}`
  
  const response = await fetch(url, {
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  const body = await response.json().catch(() => null)

  if (!response.ok || !body) {
    throw new Error(body?.message || fallbackMessage)
  }

  return body as T
}

export async function fetchModuleInfo(): Promise<{
  code: string
  name: string
  description: string
}> {
  const body = await apiFetch<{
    data: { code: string; name: string; description: string }
  }>(`${getApiBaseUrl()}/api/v1/warehouse`, '获取仓储模块信息失败')
  return body.data
}

export async function fetchRawMaterials(): Promise<RawMaterial[]> {
  const body = await apiFetch<RawMaterialListResponse>(
    `${getApiBaseUrl()}/api/v1/warehouse/raw-materials`,
    '获取原辅料库存失败',
  )
  return body.data || []
}

export async function fetchPackagingMaterials(): Promise<PackagingMaterial[]> {
  const body = await apiFetch<PackagingMaterialListResponse>(
    `${getApiBaseUrl()}/api/v1/warehouse/packaging-materials`,
    '获取包材库存失败',
  )
  return body.data || []
}

export async function fetchProducts(): Promise<ProductInventory[]> {
  const body = await apiFetch<ProductInventoryListResponse>(
    `${getApiBaseUrl()}/api/v1/warehouse/products`,
    '获取成品库存失败',
  )
  return body.data || []
}

export async function fetchWarehouseFeishuConfig(): Promise<WarehouseFeishuConfig> {
  const body = await apiFetch<{ data: WarehouseFeishuConfig }>(
    `${getApiBaseUrl()}/api/v1/warehouse/feishu-config`,
    '获取仓储飞书配置失败',
  )
  return body.data
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
  if (params?.business_domain) {
    search.set('business_domain', params.business_domain)
  }
  if (params?.keyword) {
    search.set('keyword', params.keyword)
  }
  if (params?.enabled !== undefined) {
    search.set('enabled', String(params.enabled))
  }
  const suffix = search.toString() ? `?${search.toString()}` : ''
  const body = await apiFetch<{ data: WarehouseFeishuTable[] }>(
    `${getApiBaseUrl()}/api/v1/warehouse/feishu/tables${suffix}`,
    '获取仓储飞书表目录失败',
  )
  return body.data || []
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
  const body = await apiFetch<{ data: WarehouseFeishuRawRecordData }>(
    `${getApiBaseUrl()}/api/v1/warehouse/feishu/domains/${businessDomain}/records${suffix}`,
    '获取仓储飞书原始记录失败',
  )
  return body.data
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
  const body = await apiFetch<{ data: WarehouseFeishuRawRecordData }>(
    `${getApiBaseUrl()}/api/v1/warehouse/feishu/tables/${tableId}/records${suffix}`,
    '获取仓储飞书原始记录失败',
  )
  return body.data
}

export async function fetchWarehouseFeishuWsStatus(): Promise<WarehouseFeishuWsStatus> {
  const body = await apiFetch<{ data: WarehouseFeishuWsStatus }>(
    `${getApiBaseUrl()}/api/v1/warehouse/feishu/ws/status`,
    '获取仓储飞书长连接状态失败',
  )
  return body.data
}

// ── 写操作 ──

async function apiFetchWithAuth<T>(
  path: string,
  options: RequestInit,
  authToken: string | undefined,
  fallbackMessage: string,
): Promise<T> {
  const url = path.startsWith('http') ? path : `${getApiBaseUrl().replace(/\/$/, '')}/api/v1/warehouse${path.startsWith('/') ? path : `/${path}`}`

  const response = await fetch(url, {
    ...options,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...options.headers,
    },
  })
  const body = await response.json().catch(() => null)

  if (!response.ok || !body) {
    throw new Error(body?.message || fallbackMessage)
  }

  return body as T
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
  return apiFetchWithAuth<ApiResponse<WarehouseFeishuConfig>>(
    '/feishu-config',
    { method: 'PUT', body: JSON.stringify(data) },
    authToken,
    '保存仓储飞书配置失败',
  )
}

export async function testWarehouseFeishuConfig(
  authToken: string | undefined,
  data: WarehouseFeishuConfigUpsert,
): Promise<ApiResponse<WarehouseFeishuConnectivityResult>> {
  return apiFetchWithAuth<ApiResponse<WarehouseFeishuConnectivityResult>>(
    '/feishu-config/test',
    { method: 'POST', body: JSON.stringify(data) },
    authToken,
    '测试仓储飞书配置失败',
  )
}

export async function refreshWarehouseFeishuTables(
  authToken: string | undefined,
): Promise<ApiResponse<WarehouseFeishuTable[]>> {
  return apiFetchWithAuth<ApiResponse<WarehouseFeishuTable[]>>(
    '/feishu/tables/refresh',
    { method: 'POST' },
    authToken,
    '刷新仓储飞书表失败',
  )
}

export async function setWarehouseFeishuTableEnabled(
  authToken: string | undefined,
  tableId: string,
  isEnabled: boolean,
): Promise<ApiResponse<WarehouseFeishuTable>> {
  return apiFetchWithAuth<ApiResponse<WarehouseFeishuTable>>(
    `/feishu/tables/${tableId}/enabled`,
    { method: 'PATCH', body: JSON.stringify({ is_enabled: isEnabled }) },
    authToken,
    '设置仓储飞书表启用状态失败',
  )
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
  return apiFetchWithAuth<ApiResponse<WarehouseFeishuTable[]>>(
    '/feishu/tables/enabled/batch',
    { method: 'POST', body: JSON.stringify(body) },
    authToken,
    '批量设置仓储飞书表启用状态失败',
  )
}

export async function syncWarehouseFeishuTable(
  authToken: string | undefined,
  tableId: string,
): Promise<ApiResponse<WarehouseFeishuTableSyncResult>> {
  return apiFetchWithAuth<ApiResponse<WarehouseFeishuTableSyncResult>>(
    `/feishu/tables/${tableId}/sync`,
    { method: 'POST' },
    authToken,
    '同步仓储飞书表失败',
  )
}

export async function restartWarehouseFeishuWs(
  authToken: string | undefined,
): Promise<ApiResponse<WarehouseFeishuWsStatus>> {
  return apiFetchWithAuth<ApiResponse<WarehouseFeishuWsStatus>>(
    '/feishu/ws/restart',
    { method: 'POST' },
    authToken,
    '重启仓储飞书长连接失败',
  )
}
