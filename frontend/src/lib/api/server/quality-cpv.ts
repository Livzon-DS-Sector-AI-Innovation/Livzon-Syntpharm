import { apiFetch, apiFetchRaw, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'
import type {
  CreateCpvProductInput,
  UpdateCpvProductInput,
  CreateCpvParameterInput,
  CpvProduct,
  CpvParameter,
  CpvImportPreview,
  CpvImportTask,
} from '@/types/quality-cpv'
import type { components } from '@/types/generated/schema'

type CpvProductListApiResponse = components['schemas']['CpvProductListApiResponse']

export async function createCpvProduct(data: CreateCpvProductInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/cpv/products`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCpvProduct(productId: string, data: UpdateCpvProductInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/cpv/products/${productId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCpvProduct(productId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/cpv/products/${productId}`, {
    method: 'DELETE',
  })
}

export async function createCpvParameter(productId: string, data: CreateCpvParameterInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/cpv/products/${productId}/parameters`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCpvParameter(parameterId: string, data: Partial<CreateCpvParameterInput>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/cpv/parameters/${parameterId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCpvParameter(parameterId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/cpv/parameters/${parameterId}`, {
    method: 'DELETE',
  })
}

export async function previewCpvImport(
  formData: FormData,
  productId: string,
  dataType: 'CPP' | 'CQA',
  importMode: string,
) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/cpv/import/preview?product_id=${productId}&data_type=${dataType}&import_mode=${importMode}`, {
    method: 'POST',
    body: formData,
  })
}

export async function confirmCpvImport(
  formData: FormData,
  productId: string,
  dataType: 'CPP' | 'CQA',
  importMode: string,
  fileName: string,
  skipErrors: boolean,
) {
  const params = new URLSearchParams()
  params.set('product_id', productId)
  params.set('data_type', dataType)
  params.set('import_mode', importMode)
  params.set('file_name', fileName)
  params.set('skip_errors', String(skipErrors))
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/cpv/import/confirm?${params}`, {
    method: 'POST',
    body: formData,
  })
}

export async function fetchCpvProducts(params?: { page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
  const query = searchParams.toString()
  const url = `${getApiBaseUrl()}/api/v1/quality/cpv/products${query ? `?${query}` : ''}`
  const raw = await apiFetch<CpvProductListApiResponse>(url)
  const data = unwrapResponse(raw)
  return { items: Array.isArray(data) ? data : [], total: Array.isArray(data) ? data.length : 0 }
}

export async function fetchCpvProduct(productId: string) {
  return apiFetch<CpvProduct>(`${getApiBaseUrl()}/api/v1/quality/cpv/products/${productId}`)
}

export async function fetchCpvParameters(productId: string, type: 'CPP' | 'CQA') {
  return apiFetch<CpvParameter[]>(`${getApiBaseUrl()}/api/v1/quality/cpv/products/${productId}/parameters?type=${type}`)
}