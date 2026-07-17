import type { ModuleInfo } from '@/types'
import type {
  PackagingMaterial,
  PackagingMaterialListResponse,
  ProductInventory,
  ProductInventoryListResponse,
  RawMaterial,
  RawMaterialListResponse,
  WarehouseFeishuBusinessDomain,
  WarehouseFeishuConfig,
  WarehouseFeishuRawRecordData,
  WarehouseFeishuTable,
  WarehouseFeishuWsStatus,
} from '@/types/warehouse'

const API_BASE = '/api/v1'

function buildWarehouseUrl(path: string): string {
  const normalizedPath = `/warehouse${path.startsWith('/') ? path : `/${path}`}`
  return `${API_BASE}${normalizedPath}`
}

async function apiFetch<T>(path: string, fallbackMessage: string): Promise<T> {
  const response = await fetch(buildWarehouseUrl(path), {
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

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  const body = await apiFetch<{
    data: ModuleInfo
  }>('/', '获取仓储模块信息失败')
  return body.data
}

export async function fetchRawMaterials(): Promise<RawMaterial[]> {
  const body = await apiFetch<RawMaterialListResponse>(
    '/raw-materials',
    '获取原辅料库存失败',
  )
  return body.data || []
}

export async function fetchPackagingMaterials(): Promise<PackagingMaterial[]> {
  const body = await apiFetch<PackagingMaterialListResponse>(
    '/packaging-materials',
    '获取包材库存失败',
  )
  return body.data || []
}

export async function fetchProducts(): Promise<ProductInventory[]> {
  const body = await apiFetch<ProductInventoryListResponse>(
    '/products',
    '获取成品库存失败',
  )
  return body.data || []
}

export async function fetchWarehouseFeishuConfig(): Promise<WarehouseFeishuConfig> {
  const body = await apiFetch<{ data: WarehouseFeishuConfig }>(
    '/feishu-config',
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
  try {
    const body = await apiFetch<{ data: WarehouseFeishuTable[] }>(
      `/feishu/tables${suffix}`,
      '获取仓储飞书表目录失败',
    )
    return body.data || []
  } catch {
    // Feishu not configured — return empty, not an error
    return []
  }
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
    `/feishu/domains/${businessDomain}/records${suffix}`,
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
    `/feishu/tables/${tableId}/records${suffix}`,
    '获取仓储飞书原始记录失败',
  )
  return body.data
}

export async function fetchWarehouseFeishuWsStatus(): Promise<WarehouseFeishuWsStatus> {
  const body = await apiFetch<{ data: WarehouseFeishuWsStatus }>(
    '/feishu/ws/status',
    '获取仓储飞书长连接状态失败',
  )
  return body.data
}