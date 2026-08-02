'use server'

import {
  createGiftRequisitionApi, updateGiftRequisitionApi, deleteGiftRequisitionApi,
  createRegulationApi, updateRegulationApi, deleteRegulationApi,
  extractRegulationTextApi,
  createGiftInventoryApi, updateGiftInventoryApi, deleteGiftInventoryApi,
  createVehicleApi, updateVehicleApi, deleteVehicleApi,
  batchImportVehiclesApi,
} from '@/lib/api/server/administration'

export async function createGiftRequisition(data: any) {
  return createGiftRequisitionApi(data)
}

export async function updateGiftRequisition(id: string, data: any) {
  return updateGiftRequisitionApi(id, data)
}

export async function deleteGiftRequisition(id: string) {
  return deleteGiftRequisitionApi(id)
}

export async function createRegulation(data: Record<string, unknown>): Promise<unknown> {
  return createRegulationApi(data as Record<string, unknown>)
}

export async function updateRegulation(id: string, data: Record<string, unknown>): Promise<unknown> {
  return updateRegulationApi(id, data as Record<string, unknown>)
}

export async function deleteRegulation(id: string) {
  return deleteRegulationApi(id)
}

export async function extractRegulationText(data: { file_name?: string; file_type?: string; file_data?: string }) {
  return extractRegulationTextApi(data) as Promise<{ code: number; message: string; data: { text: string; source: string } }>
}

export async function createGiftInventory(data: any) {
  return createGiftInventoryApi(data)
}

export async function updateGiftInventory(id: string, data: any) {
  return updateGiftInventoryApi(id, data)
}

export async function deleteGiftInventory(id: string) {
  return deleteGiftInventoryApi(id)
}

export async function createVehicle(data: any) {
  return createVehicleApi(data)
}

export async function updateVehicle(id: string, data: any) {
  return updateVehicleApi(id, data)
}

export async function deleteVehicle(id: string) {
  return deleteVehicleApi(id)
}

export async function batchImportVehicles(file: any): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  return batchImportVehiclesApi(formData)
}
