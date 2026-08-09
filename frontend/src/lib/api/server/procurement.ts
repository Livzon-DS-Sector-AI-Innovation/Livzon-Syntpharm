import type { operations } from '@/types/generated/schema'
import type {
  InvoiceRecognitionRecordListResponse,
  InvoiceRecognitionResponse,
  InvoiceRecognitionRecordDeleteResponse,
  PurchaseOrderListResponse,
  PurchaseRequestApiResponse,
  PurchaseRequestListResponse,
  PurchaseRequestCreate,
  PurchaseRequestUpdate,
  PurchaseApprovalRequest,
  ContractGenerateRequest,
  ContractRecordListResponse,
  ContractRecordResponse,
  SupplierListResponse,
} from '@/types/procurement'
import type { ContractGenerateActionResult } from '@/types/procurement'

type InvoiceRecognitionRecordQuery =
  operations['list_invoice_records_api_v1_procurement_invoices_recognition_records_get']['parameters']['query']
type PurchaseRequestQuery =
  operations['list_purchase_request_records_api_v1_procurement_purchase_requests_get']['parameters']['query']
type PurchaseOrderQuery =
  operations['list_purchase_order_records_api_v1_procurement_purchase_orders_get']['parameters']['query']

export function getApiBaseUrl(): string {
  return process.env.API_BASE_URL || 'http://dazah-backend-app-1:8000'
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${getApiBaseUrl().replace(/\/$/, '')}${path}`
  const response = await fetch(url, {
    ...options,
    cache: options?.cache ?? 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status} ${response.statusText}`)
  }
  const data = await response.json()
  return data.data ?? data
}

export async function fetchModuleInfo(): Promise<{ code: string; name: string; description: string }> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/procurement`)
}

export async function fetchInvoiceRecognitionRecords(
  query: InvoiceRecognitionRecordQuery = {}
): Promise<InvoiceRecognitionRecordListResponse> {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })

  const path = `${getApiBaseUrl()}/api/v1/procurement/invoices/recognition-records${
    params.size ? `?${params.toString()}` : ''
  }`
  
  return apiFetch(path)
}

export async function fetchPurchaseRequests(
  query: PurchaseRequestQuery = {}
): Promise<PurchaseRequestListResponse> {
  const path = `${getApiBaseUrl()}/api/v1/procurement/purchase-requests${buildQueryString(query)}`
  return apiFetch(path)
}

export async function fetchPurchaseOrders(
  query: PurchaseOrderQuery
): Promise<PurchaseOrderListResponse> {
  const path = `${getApiBaseUrl()}/api/v1/procurement/purchase-orders${buildQueryString(query)}`
  return apiFetch(path)
}

export async function exportPurchaseOrdersExcel(
  query: Omit<PurchaseOrderQuery, 'page' | 'page_size'>
): Promise<{ blob: Blob; filename: string }> {
  const url = `${getApiBaseUrl().replace(/\/$/, '')}/api/v1/procurement/purchase-orders/export${buildQueryString(query)}`
  const response = await fetch(url, { cache: 'no-store' })
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
  return apiFetch(`${getApiBaseUrl()}/api/v1/procurement/purchase-requests/${requestId}`)
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

// Contract and Supplier functions
export async function fetchContractRecords(
  params: { keyword?: string; supplier_name?: string; material_name?: string; purchase_category?: string; page?: number; page_size?: number } = {}
): Promise<ContractRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params.keyword) searchParams.set('keyword', params.keyword)
  if (params.supplier_name) searchParams.set('supplier_name', params.supplier_name)
  if (params.material_name) searchParams.set('material_name', params.material_name)
  if (params.purchase_category) searchParams.set('purchase_category', params.purchase_category)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiFetch<ContractRecordListResponse>(
    `${getApiBaseUrl()}/api/v1/procurement/contracts${qs ? `?${qs}` : ''}`
  )
}

export async function fetchContractRecord(id: string): Promise<{ data: ContractRecordResponse }> {
  const response = await apiFetch<ContractRecordResponse>(`${getApiBaseUrl()}/api/v1/procurement/contracts/${id}`)
  return { data: response }
}

export async function fetchContractFile(id: string, filename: string): Promise<{ blob: Blob; filename: string }> {
  const url = `${getApiBaseUrl().replace(/\/$/, '')}/api/v1/procurement/contracts/${id}/files/${filename}`
  const response = await fetch(url, { cache: 'no-store' })
  if (!response.ok) {
    throw new Error('Failed to fetch contract file')
  }
  const blob = await response.blob()
  return { blob, filename }
}

export async function fetchSuppliers(
  params: { keyword?: string; supplier_name?: string; material_name?: string; purchase_category?: string; page?: number; page_size?: number } = {}
): Promise<SupplierListResponse> {
  const searchParams = new URLSearchParams()
  if (params.keyword) searchParams.set('keyword', params.keyword)
  if (params.supplier_name) searchParams.set('supplier_name', params.supplier_name)
  if (params.material_name) searchParams.set('material_name', params.material_name)
  if (params.purchase_category) searchParams.set('purchase_category', params.purchase_category)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiFetch<SupplierListResponse>(
    `${getApiBaseUrl()}/api/v1/procurement/suppliers${qs ? `?${qs}` : ''}`
  )
}

// ── 写操作 ──

export async function recognizeInvoicePdf(
  headers: HeadersInit,
  formData: FormData
): Promise<InvoiceRecognitionResponse> {
  const url = `${getApiBaseUrl().replace(/\/$/, '')}/api/v1/procurement/invoices/recognize`
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
    cache: 'no-store',
  })
  return parseJsonResponse<InvoiceRecognitionResponse>(response, '发票识别失败')
}

export async function deleteInvoiceRecognitionRecord(
  headers: HeadersInit,
  recordId: string
): Promise<InvoiceRecognitionRecordDeleteResponse> {
  const url = `${getApiBaseUrl().replace(/\/$/, '')}/api/v1/procurement/invoices/recognition-records/${recordId}`
  const response = await fetch(url, {
    method: 'DELETE',
    headers,
    cache: 'no-store',
  })
  return parseJsonResponse<InvoiceRecognitionRecordDeleteResponse>(response, '识别记录删除失败')
}

export async function deleteInvoiceRecognitionRecords(
  headers: HeadersInit,
  recordIds: string[]
): Promise<InvoiceRecognitionRecordDeleteResponse> {
  const url = `${getApiBaseUrl().replace(/\/$/, '')}/api/v1/procurement/invoices/recognition-records/batch-delete`
  const response = await fetch(url, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids: recordIds }),
    cache: 'no-store',
  })
  return parseJsonResponse<InvoiceRecognitionRecordDeleteResponse>(response, '识别记录删除失败')
}

export async function createPurchaseRequest(
  headers: HeadersInit,
  payload: PurchaseRequestCreate
): Promise<PurchaseRequestApiResponse> {
  return procurementJsonFetch<PurchaseRequestApiResponse>(
    `${getApiBaseUrl()}/api/v1/procurement/purchase-requests`,
    headers,
    { method: 'POST', body: JSON.stringify(payload) },
    '采购申请保存失败'
  )
}

export async function updatePurchaseRequest(
  headers: HeadersInit,
  requestId: string,
  payload: PurchaseRequestUpdate
): Promise<PurchaseRequestApiResponse> {
  return procurementJsonFetch<PurchaseRequestApiResponse>(
    `${getApiBaseUrl()}/api/v1/procurement/purchase-requests/${requestId}`,
    headers,
    { method: 'PUT', body: JSON.stringify(payload) },
    '采购申请更新失败'
  )
}

export async function submitPurchaseRequest(
  headers: HeadersInit,
  requestId: string
): Promise<PurchaseRequestApiResponse> {
  return procurementJsonFetch<PurchaseRequestApiResponse>(
    `${getApiBaseUrl()}/api/v1/procurement/purchase-requests/${requestId}/submit`,
    headers,
    { method: 'POST', body: JSON.stringify({}) },
    '采购申请提交失败'
  )
}

export async function approvePurchaseRequest(
  headers: HeadersInit,
  requestId: string,
  payload: PurchaseApprovalRequest
): Promise<PurchaseRequestApiResponse> {
  return procurementJsonFetch<PurchaseRequestApiResponse>(
    `${getApiBaseUrl()}/api/v1/procurement/purchase-requests/${requestId}/approve`,
    headers,
    { method: 'POST', body: JSON.stringify(payload) },
    '审批失败'
  )
}

export async function rejectPurchaseRequest(
  headers: HeadersInit,
  requestId: string,
  payload: PurchaseApprovalRequest
): Promise<PurchaseRequestApiResponse> {
  return procurementJsonFetch<PurchaseRequestApiResponse>(
    `${getApiBaseUrl()}/api/v1/procurement/purchase-requests/${requestId}/reject`,
    headers,
    { method: 'POST', body: JSON.stringify(payload) },
    '驳回失败'
  )
}

export async function generateProcurementContract(
  headers: HeadersInit,
  payload: ContractGenerateRequest
): Promise<ContractGenerateActionResult> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/procurement/contracts/generate`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    cache: 'no-store',
  })

  if (!response.ok) {
    let message = '合同生成失败'
    try {
      const errorBody = await response.json()
      message = errorBody.detail || errorBody.message || message
    } catch {
      message = `${message}: ${response.status} ${response.statusText}`
    }
    return { ok: false, message }
  }

  const contentType =
    response.headers.get('content-type') ||
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  const filename =
    parseDownloadFilename(response.headers.get('content-disposition')) || '采购合同.docx'
  const arrayBuffer = await response.arrayBuffer()

  return {
    ok: true,
    filename,
    contentType,
    base64: Buffer.from(arrayBuffer).toString('base64'),
  }
}

export async function importSupplierTable(
  headers: HeadersInit,
  formData: FormData
): Promise<any> {
  const url = `${getApiBaseUrl().replace(/\/$/, '')}/api/v1/procurement/suppliers/import`
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
    cache: 'no-store',
  })
  const body = await response.json().catch(() => null)
  if (!response.ok || !body) {
    throw new Error(body?.message || '供应商清单导入失败')
  }
  return body
}

// ── 内部辅助函数 ──

async function parseJsonResponse<T extends { code: number; message: string }>(
  response: Response,
  fallbackMessage: string
): Promise<T> {
  try {
    const body = await response.json()
    if (response.ok && typeof body?.code === 'number') {
      return body
    }
    return {
      code: typeof body?.code === 'number' ? body.code : response.status,
      message: body?.message || body?.detail || fallbackMessage,
      data: body?.data ?? null,
      meta: body?.meta ?? null,
    } as unknown as T
  } catch {
    return {
      code: response.status,
      message: `${fallbackMessage}: ${response.status} ${response.statusText}`,
      data: null,
      meta: null,
    } as unknown as T
  }
}

async function procurementJsonFetch<T extends { code: number; message: string }>(
  path: string,
  headers: HeadersInit,
  options: RequestInit,
  fallbackMessage: string
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { ...headers, 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  return parseJsonResponse<T>(response, fallbackMessage)
}
