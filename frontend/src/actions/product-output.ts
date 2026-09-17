'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import type {
  ProductOutput,
  ProductOutputFormData,
  ProductOutputQueryParams,
  SummaryData,
} from '@/types/product-output'
import {
  getProductOutputs as getProductOutputsApi,
  getProductOutput as getProductOutputApi,
  createProductOutput as createProductOutputApi,
  updateProductOutput as updateProductOutputApi,
  deleteProductOutput as deleteProductOutputApi,
  getWorkshops as getWorkshopsApi,
  getSummary as getSummaryApi,
  importProductOutputs as importProductOutputsApi,
  fetchPreviewImport as fetchPreviewImportApi,
  fetchUndoImport as fetchUndoImportApi,
  getBatchCount as getBatchCountApi,
} from '@/lib/api/server/product-output'

export async function getProductOutputs(params: ProductOutputQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return getProductOutputsApi(params, authHeaders)
}

export async function getProductOutput(id: string) {
  const authHeaders = await getAuthHeaders()
  return getProductOutputApi(id, authHeaders)
}

export async function createProductOutput(data: ProductOutputFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await createProductOutputApi(data, authHeaders)
  revalidatePath('/production/product-output')
  return response
}

export async function updateProductOutput(id: string, data: Partial<ProductOutputFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await updateProductOutputApi(id, data, authHeaders)
  revalidatePath('/production/product-output')
  return response
}

export async function deleteProductOutput(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await deleteProductOutputApi(id, authHeaders)
  revalidatePath('/production/product-output')
  return response
}

export async function getWorkshops() {
  const authHeaders = await getAuthHeaders()
  return getWorkshopsApi(authHeaders)
}

export async function getSummary(params: {
  target_date?: string
  month?: string
  year?: number
  product_id?: string
  start_date?: string
  end_date?: string
} = {}) {
  const authHeaders = await getAuthHeaders()
  return getSummaryApi(params, authHeaders)
}

export async function importProductOutputs(formData: FormData) {
  const authHeaders = await getAuthHeaders()
  const response = await importProductOutputsApi(formData, authHeaders)
  revalidatePath('/production/product-output')
  return response
}

export async function getBatchCount(params: {
  target_date?: string
  month?: string
  year?: number
  product_id?: string
  start_date?: string
  end_date?: string
} = {}) {
  const authHeaders = await getAuthHeaders()
  return getBatchCountApi(params, authHeaders)
}
// ─── Sync Config Actions ───

import type { components } from '@/types/generated/schema'
import {
  getSyncConfig as getSyncConfigApi,
  createSyncConfig as createSyncConfigApi,
  updateSyncConfig as updateSyncConfigApi,
  deleteSyncConfig as deleteSyncConfigApi,
  pushToFeishu as pushToFeishuApi,
  pullFromFeishu as pullFromFeishuApi,
  bidirectionalSync as bidirectionalSyncApi,
  importFromBitable as importFromBitableApi,
  batchDeleteProductOutputs as batchDeleteApi,
} from '@/lib/api/server/product-output'

export async function getSyncConfig(productId: string) {
  const authHeaders = await getAuthHeaders()
  return getSyncConfigApi(productId, authHeaders)
}

export async function createSyncConfig(data: components["schemas"]["ProductSyncConfigCreate"]) {
  const authHeaders = await getAuthHeaders()
  return createSyncConfigApi(data as unknown as Record<string, unknown>, authHeaders)
}

export async function updateSyncConfig(configId: string, data: components["schemas"]["ProductSyncConfigUpdate"]) {
  const authHeaders = await getAuthHeaders()
  return updateSyncConfigApi(configId, data as unknown as Record<string, unknown>, authHeaders)
}

export async function deleteSyncConfig(configId: string) {
  const authHeaders = await getAuthHeaders()
  return deleteSyncConfigApi(configId, authHeaders)
}

export async function pushToFeishu(productId: string) {
  const authHeaders = await getAuthHeaders()
  return pushToFeishuApi(productId, authHeaders)
}

export async function pullFromFeishu(productId: string) {
  const authHeaders = await getAuthHeaders()
  return pullFromFeishuApi(productId, authHeaders)
}

export async function bidirectionalSync(productId: string) {
  const authHeaders = await getAuthHeaders()
  return bidirectionalSyncApi(productId, authHeaders)
}

export async function importFromBitable(appToken: string, tableId: string = '') {
  const authHeaders = await getAuthHeaders()
  return importFromBitableApi(appToken, tableId, authHeaders)
}

export async function batchDeleteProductOutputs(ids: string[]) {
  const authHeaders = await getAuthHeaders()
  return batchDeleteApi(ids, authHeaders)
}

// ─── Annual Review Actions ───

import {
  fetchAnnualReview as fetchAnnualReviewApi,
  fetchExportAnnualReview as fetchExportAnnualReviewApi,
} from '@/lib/api/server/product-output'
import type { AnnualReviewData } from '@/types/product-output'

export async function fetchAnnualReview(year: number) {
  const authHeaders = await getAuthHeaders()
  return fetchAnnualReviewApi(year, authHeaders)
}

export async function fetchExportAnnualReview(year: number) {
  const authHeaders = await getAuthHeaders()
  return fetchExportAnnualReviewApi(year, authHeaders)
}

export async function fetchPreviewImport(formData: FormData) {
  const authHeaders = await getAuthHeaders()
  return fetchPreviewImportApi(formData, authHeaders)
}

export async function fetchUndoImport(batchId: string) {
  const authHeaders = await getAuthHeaders()
  const response = await fetchUndoImportApi(batchId, authHeaders)
  revalidatePath('/production/product-output')
  return response
}
