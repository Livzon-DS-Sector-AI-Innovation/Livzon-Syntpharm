import { apiFetch, apiFetchRaw, API_BASE_URL, buildQueryString } from '@/lib/api/server/base'
import type {
  ProductOutput,
  ProductOutputFormData,
  ProductOutputQueryParams,
  SummaryData,
} from '@/types/product-output'

export async function getProductOutputs(
  params: ProductOutputQueryParams,
  headers: Record<string, string>,
) {
  const qs = buildQueryString(params as Record<string, unknown>)
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output${qs}`, { headers })
}

export async function getProductOutput(id: string, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/${id}`, { headers })
}

export async function createProductOutput(data: ProductOutputFormData, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateProductOutput(id: string, data: Partial<ProductOutputFormData>, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteProductOutput(id: string, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function getWorkshops(headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/workshops`, { headers })
}

export async function getSummary(
  params: {
    target_date?: string
    month?: string
    year?: number
    product_id?: string
    start_date?: string
    end_date?: string
  },
  headers: Record<string, string>,
) {
  const qs = buildQueryString(params as Record<string, unknown>)
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/summary${qs}`, { headers })
}

export async function importProductOutputs(formData: FormData, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/import`, {
    method: 'POST',
    body: formData,
    headers,
  })
}

export async function getBatchCount(
  params: {
    target_date?: string
    month?: string
    year?: number
    product_id?: string
    start_date?: string
    end_date?: string
  },
  headers: Record<string, string>,
) {
  const qs = buildQueryString(params as Record<string, unknown>)
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/batch-count${qs}`, { headers })
}
// ─── Sync Config ───

export async function getSyncConfig(productId: string, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${productId}`, { headers })
}

export async function createSyncConfig(data: Record<string, unknown>, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-sync-config`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { ...headers, 'Content-Type': 'application/json' },
  })
}

export async function updateSyncConfig(configId: string, data: Record<string, unknown>, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${configId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers: { ...headers, 'Content-Type': 'application/json' },
  })
}

export async function deleteSyncConfig(configId: string, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${configId}`, {
    method: 'DELETE',
    headers,
  })
}

export async function pushToFeishu(productId: string, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${productId}/push`, {
    method: 'POST',
    headers,
  })
}

export async function pullFromFeishu(productId: string, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${productId}/pull`, {
    method: 'POST',
    headers,
  })
}

export async function bidirectionalSync(productId: string, headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${productId}/sync`, {
    method: 'POST',
    headers,
  })
}

export async function importFromBitable(appToken: string, tableId: string, headers: Record<string, string>) {
  const params = new URLSearchParams({ app_token: appToken })
  if (tableId) params.set('table_id', tableId)
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/import-from-bitable?${params.toString()}`, {
    method: 'POST',
    headers,
  })
}

export async function batchDeleteProductOutputs(ids: string[], headers: Record<string, string>) {
  return apiFetch(`${API_BASE_URL}/api/v1/production/product-output/batch?ids=${ids.join(',')}`, {
    method: 'DELETE',
    headers,
  })
}
