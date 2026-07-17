import { apiFetch, apiFetchRaw, API_BASE_URL } from '@/lib/api/server/base'
import type {
  CreateCpvProductInput,
  UpdateCpvProductInput,
  CreateCpvParameterInput,
  CpvProduct,
  CpvProductWithStats,
  CpvParameter,
  CpvImportPreview,
  CpvImportTask,
} from '@/types/quality-cpv'

export async function createCpvProduct(data: CreateCpvProductInput) {
  return apiFetch(`${API_BASE_URL}/api/v1/quality/cpv/products`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCpvProduct(productId: string, data: UpdateCpvProductInput) {
  return apiFetch(`${API_BASE_URL}/api/v1/quality/cpv/products/${productId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCpvProduct(productId: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/quality/cpv/products/${productId}`, {
    method: 'DELETE',
  })
}

export async function createCpvParameter(productId: string, data: CreateCpvParameterInput) {
  return apiFetch(`${API_BASE_URL}/api/v1/quality/cpv/products/${productId}/parameters`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCpvParameter(parameterId: string, data: Partial<CreateCpvParameterInput>) {
  return apiFetch(`${API_BASE_URL}/api/v1/quality/cpv/parameters/${parameterId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCpvParameter(parameterId: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/quality/cpv/parameters/${parameterId}`, {
    method: 'DELETE',
  })
}

export async function previewCpvImport(
  formData: FormData,
  productId: string,
  dataType: 'CPP' | 'CQA',
  importMode: string,
) {
  return apiFetch(`${API_BASE_URL}/api/v1/quality/cpv/import/preview?product_id=${productId}&data_type=${dataType}&import_mode=${importMode}`, {
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
  return apiFetch(`${API_BASE_URL}/api/v1/quality/cpv/import/confirm?${params}`, {
    method: 'POST',
    body: formData,
  })
}

export async function fetchCpvProducts(params?: { page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
  const query = searchParams.toString()
  const url = `${API_BASE_URL}/api/v1/quality/cpv/products${query ? `?${query}` : ''}`
  return apiFetch<{ items: CpvProductWithStats[]; total: number }>(url)
}

export async function fetchCpvProduct(productId: string) {
  return apiFetch<CpvProduct>(`${API_BASE_URL}/api/v1/quality/cpv/products/${productId}`)
}

export async function fetchCpvParameters(productId: string, type: 'CPP' | 'CQA') {
  return apiFetch<CpvParameter[]>(`${API_BASE_URL}/api/v1/quality/cpv/products/${productId}/parameters?type=${type}`)
}