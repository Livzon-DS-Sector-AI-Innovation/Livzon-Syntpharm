import type { operations } from '@/types/generated/schema'
import type {
  InvoiceRecognitionRecordListResponse,
  PurchaseOrderListResponse,
  PurchaseRequestApiResponse,
  PurchaseRequestListResponse,
} from '@/types/procurement'
import { apiGet } from '@/lib/api/client'

type InvoiceRecognitionRecordQuery =
  operations['list_invoice_records_api_v1_procurement_invoices_recognition_records_get']['parameters']['query']
type PurchaseRequestQuery =
  operations['list_purchase_request_records_api_v1_procurement_purchase_requests_get']['parameters']['query']
type PurchaseOrderQuery =
  operations['list_purchase_order_records_api_v1_procurement_purchase_orders_get']['parameters']['query']

export async function fetchModuleInfo(): Promise<{ code: string; name: string; description: string }> {
  return apiGet(`/api/v1/procurement`)
}

export async function fetchInvoiceRecognitionRecords(
  query: InvoiceRecognitionRecordQuery = {}
): Promise<InvoiceRecognitionRecordListResponse> {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })

  const path = `/api/v1/procurement/invoices/recognition-records${
    params.size ? `?${params.toString()}` : ''
  }`
  
  return apiGet(path)
}

export async function fetchPurchaseRequests(
  query: PurchaseRequestQuery = {}
): Promise<PurchaseRequestListResponse> {
  const path = `/api/v1/procurement/purchase-requests${buildQueryString(query)}`
  return apiGet(path)
}

export async function fetchPurchaseOrders(
  query: PurchaseOrderQuery
): Promise<PurchaseOrderListResponse> {
  const path = `/api/v1/procurement/purchase-orders${buildQueryString(query)}`
  return apiGet(path)
}

export async function exportPurchaseOrdersExcel(
  query: Omit<PurchaseOrderQuery, 'page' | 'page_size'>
): Promise<{ blob: Blob; filename: string }> {
  const path = `/api/v1/procurement/purchase-orders/export${buildQueryString(query)}`
  const response = await fetch(path, { cache: 'no-store' })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status} ${response.statusText}`)
  }
  const blob = await response.blob()
  const excelBlob = blob.type
    ? blob
    : new Blob([blob], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
  return {
    blob: excelBlob,
    filename: parseDownloadFilename(response.headers.get('content-disposition')),
  }
}

export async function fetchPurchaseRequest(
  requestId: string
): Promise<PurchaseRequestApiResponse> {
  return apiGet(`/api/v1/procurement/purchase-requests/${requestId}`)
}

function buildQueryString(query: Record<string, unknown>) {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params.size ? `?${params.toString()}` : ''
}

function parseDownloadFilename(contentDisposition: string | null) {
  if (!contentDisposition) return '采购订单.xlsx'

  const utf8Match = contentDisposition.match(/filename\*=utf-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1])
  }

  const asciiMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return asciiMatch?.[1] ?? '采购订单.xlsx'
}

export async function fetchSuppliers(
  params: { keyword?: string; supplier_name?: string; material_name?: string; purchase_category?: string; page?: number; page_size?: number } = {}
): Promise<import('@/types/procurement').SupplierListResponse> {
  const searchParams = new URLSearchParams()
  if (params.keyword) searchParams.set('keyword', params.keyword)
  if (params.supplier_name) searchParams.set('supplier_name', params.supplier_name)
  if (params.material_name) searchParams.set('material_name', params.material_name)
  if (params.purchase_category) searchParams.set('purchase_category', params.purchase_category)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiGet(`/api/v1/procurement/suppliers${qs ? `?${qs}` : ''}`)
}

export async function fetchContractRecords(
  params: { keyword?: string; supplier_name?: string; material_name?: string; purchase_category?: string; page?: number; page_size?: number } = {}
): Promise<import('@/types/procurement').ContractRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params.keyword) searchParams.set('keyword', params.keyword)
  if (params.supplier_name) searchParams.set('supplier_name', params.supplier_name)
  if (params.material_name) searchParams.set('material_name', params.material_name)
  if (params.purchase_category) searchParams.set('purchase_category', params.purchase_category)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiGet(`/api/v1/procurement/contracts${qs ? `?${qs}` : ''}`)
}

export async function fetchContractRecord(id: string): Promise<{ data: import('@/types/procurement').ContractRecordResponse }> {
  const data = await apiGet<import('../../../types/procurement').ContractRecordResponse>(`/api/v1/procurement/contracts/${id}`)
  return { data }
}

export async function fetchContractFile(id: string, filename: string): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`/api/v1/procurement/contracts/${id}/files/${filename}`)
  const blob = await response.blob()
  return { blob, filename }
}
