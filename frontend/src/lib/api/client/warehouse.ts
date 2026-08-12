import type { ModuleInfo } from '@/types'
import type {
  PackagingMaterial,
  ProductInventory,
  RawMaterial,
  WarehouseFeishuBusinessDomain,
  WarehouseFeishuConfig,
  WarehouseFeishuRawRecordData,
  WarehouseFeishuTable,
  WarehouseFeishuWsStatus,
} from '@/types/warehouse'
import { apiGet } from '@/lib/api/client'

const API_BASE = '/api/v1'

function buildWarehouseUrl(path: string): string {
  const normalizedPath = `/warehouse${path.startsWith('/') ? path : `/${path}`}`
  return `${API_BASE}${normalizedPath}`
}

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiGet<ModuleInfo>(buildWarehouseUrl('/'))
}

export async function fetchRawMaterials(): Promise<RawMaterial[]> {
  const result = await apiGet<RawMaterial[]>(buildWarehouseUrl('/raw-materials'))
  return result || []
}

export async function fetchPackagingMaterials(): Promise<PackagingMaterial[]> {
  const result = await apiGet<PackagingMaterial[]>(buildWarehouseUrl('/packaging-materials'))
  return result || []
}

export async function fetchProducts(): Promise<ProductInventory[]> {
  const result = await apiGet<ProductInventory[]>(buildWarehouseUrl('/products'))
  return result || []
}

export async function fetchWarehouseFeishuConfig(): Promise<WarehouseFeishuConfig> {
  return apiGet<WarehouseFeishuConfig>(buildWarehouseUrl('/feishu-config'))
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
    const result = await apiGet<WarehouseFeishuTable[]>(
      buildWarehouseUrl(`/feishu/tables${suffix}`),
    )
    return result || []
  } catch {
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
  return apiGet<WarehouseFeishuRawRecordData>(
    buildWarehouseUrl(`/feishu/domains/${businessDomain}/records${suffix}`),
  )
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
  return apiGet<WarehouseFeishuRawRecordData>(
    buildWarehouseUrl(`/feishu/tables/${tableId}/records${suffix}`),
  )
}

export async function fetchWarehouseFeishuWsStatus(): Promise<WarehouseFeishuWsStatus> {
  return apiGet<WarehouseFeishuWsStatus>(buildWarehouseUrl('/feishu/ws/status'))
}
