import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { WorkshopProductCreate } from '@/types/workshop-product'
import type { ProductCreateInput, ProductUpdateInput } from '@/types/product'

export async function createProduct(data: ProductCreateInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProduct(id: string, data: ProductUpdateInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteProduct(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products/${id}`, {
    method: 'DELETE',
  })
}

export async function getProducts(): Promise<any> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products`, { cache: 'no-store' })
}

export async function getProductsByWorkshop(workshop: string): Promise<any> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products/workshop/${encodeURIComponent(workshop)}`, { cache: 'no-store' })
}

export async function getProduct(productId: string): Promise<any> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products/${productId}`, { cache: 'no-store' })
}

export async function createWorkshopProduct(data: WorkshopProductCreate): Promise<any> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function syncProductsFromFeishu(): Promise<{
  code: number
  message: string
  data: { created: number; updated: number; failed: number; total: number }
}> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products/sync-from-feishu`, {
    method: 'POST',
    cache: 'no-store',
  })
}

export async function syncProductToFeishu(id: string): Promise<{
  code: number
  message: string
  data: { feishu_record_id: string }
}> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/products/${id}/sync-to-feishu`, {
    method: 'POST',
    cache: 'no-store',
  })
}