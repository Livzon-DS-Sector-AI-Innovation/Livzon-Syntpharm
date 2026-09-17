'use server'

import { revalidatePath } from 'next/cache'
import type { ColumnConfig, CreateTableRequest, UpdateTableRequest } from '@/types/inspection-table'
import {
  getInspectionTables as fetchInspectionTables,
  getInspectionTable as fetchInspectionTable,
  createInspectionTable as apiCreateInspectionTable,
  updateInspectionTable as apiUpdateInspectionTable,
  deleteInspectionTable as apiDeleteInspectionTable,
  addTableRow as apiAddTableRow,
  updateTableRow as apiUpdateTableRow,
  deleteTableRow as apiDeleteTableRow,
  batchSaveTableRows as apiBatchSaveTableRows,
  recognizeImage as apiRecognizeImage,
  recognizeMultipleImagesV3 as apiRecognizeMultipleImagesV3,
  uploadInspectionTemplate as apiUploadInspectionTemplate,
  deleteInspectionTemplate as apiDeleteInspectionTemplate,
} from '@/lib/api/server/inspection-table'

export async function getInspectionTables(params?: {
  is_active?: boolean
  keyword?: string
  page?: number
  page_size?: number
}) {
  return fetchInspectionTables(params)
}

export async function getInspectionTable(id: string) {
  return fetchInspectionTable(id)
}

export async function createInspectionTable(data: CreateTableRequest) {
  const result = await apiCreateInspectionTable(data)
  revalidatePath('/quality/inspection-table')
  return result
}

export async function updateInspectionTable(id: string, data: UpdateTableRequest) {
  const result = await apiUpdateInspectionTable(id, data)
  revalidatePath('/quality/inspection-table')
  return result
}

export async function deleteInspectionTable(id: string) {
  const result = await apiDeleteInspectionTable(id)
  revalidatePath('/quality/inspection-table')
  return result
}

export async function addTableRow(tableId: string, rowData: Record<string, any>) {
  return apiAddTableRow(tableId, rowData)
}

export async function updateTableRow(tableId: string, rowId: number, rowData: Record<string, any>) {
  return apiUpdateTableRow(tableId, rowId, rowData)
}

export async function deleteTableRow(tableId: string, rowId: number) {
  return apiDeleteTableRow(tableId, rowId)
}

export async function batchSaveTableRows(tableId: string, rows: Record<string, any>[]) {
  return apiBatchSaveTableRows(tableId, rows)
}

export async function recognizeImage(tableId: string, file: File) {
  return apiRecognizeImage(tableId, file)
}

export async function recognizeMultipleImagesV3(tableId: string, files: File[]) {
  return apiRecognizeMultipleImagesV3(tableId, files)
}

export async function uploadInspectionTemplate(tableId: string, file: File) {
  return apiUploadInspectionTemplate(tableId, file)
}

export async function deleteInspectionTemplate(tableId: string) {
  return apiDeleteInspectionTemplate(tableId)
}