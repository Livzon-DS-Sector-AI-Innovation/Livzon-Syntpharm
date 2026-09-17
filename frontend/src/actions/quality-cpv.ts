'use server'

import { revalidatePath } from 'next/cache'
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
import {
  createCpvProduct as createCpvProductApi,
  updateCpvProduct as updateCpvProductApi,
  deleteCpvProduct as deleteCpvProductApi,
  createCpvParameter as createCpvParameterApi,
  updateCpvParameter as updateCpvParameterApi,
  deleteCpvParameter as deleteCpvParameterApi,
  previewCpvImport as previewCpvImportApi,
  confirmCpvImport as confirmCpvImportApi,
  fetchCpvProducts as fetchCpvProductsApi,
  fetchCpvProduct as fetchCpvProductApi,
  fetchCpvParameters as fetchCpvParametersApi,
} from '@/lib/api/server/quality-cpv'

export async function createCpvProduct(data: CreateCpvProductInput): Promise<CpvProduct> {
  const result = await createCpvProductApi(data)
  revalidatePath('/quality/cpv')
  return result
}

export async function updateCpvProduct(productId: string, data: UpdateCpvProductInput): Promise<CpvProduct> {
  const result = await updateCpvProductApi(productId, data)
  revalidatePath('/quality/cpv')
  return result
}

export async function deleteCpvProduct(productId: string): Promise<void> {
  await deleteCpvProductApi(productId)
  revalidatePath('/quality/cpv')
}

export async function createCpvParameter(productId: string, data: CreateCpvParameterInput): Promise<CpvParameter> {
  const result = await createCpvParameterApi(productId, data)
  revalidatePath('/quality/cpv')
  return result
}

export async function updateCpvParameter(parameterId: string, data: Partial<CreateCpvParameterInput>): Promise<CpvParameter> {
  const result = await updateCpvParameterApi(parameterId, data)
  revalidatePath('/quality/cpv')
  return result
}

export async function deleteCpvParameter(parameterId: string): Promise<void> {
  await deleteCpvParameterApi(parameterId)
  revalidatePath('/quality/cpv')
}

export async function previewCpvImport(
  file: File,
  productId: string,
  dataType: 'CPP' | 'CQA',
  importMode: string
): Promise<CpvImportPreview> {
  const formData = new FormData()
  formData.append('file', file)
  return previewCpvImportApi(formData, productId, dataType, importMode)
}

export async function confirmCpvImport(
  file: File,
  productId: string,
  dataType: 'CPP' | 'CQA',
  importMode: string,
  fileName: string,
  skipErrors: boolean
): Promise<CpvImportTask> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await confirmCpvImportApi(formData, productId, dataType, importMode, fileName, skipErrors)
  revalidatePath('/quality/cpv')
  return result
}

export async function fetchCpvProductsServer(params?: { page?: number; page_size?: number }) {
  return fetchCpvProductsApi(params)
}

export async function fetchCpvProductServer(productId: string) {
  return fetchCpvProductApi(productId)
}

export async function fetchCpvParametersServer(productId: string, type: 'CPP' | 'CQA') {
  return fetchCpvParametersApi(productId, type)
}