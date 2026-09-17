'use server'

import {
  createGiftRequisitionApi, updateGiftRequisitionApi, deleteGiftRequisitionApi,
  createRegulationApi, updateRegulationApi, deleteRegulationApi,
  extractRegulationTextApi,
  createGiftInventoryApi, updateGiftInventoryApi, deleteGiftInventoryApi,
  createVehicleApi, updateVehicleApi, deleteVehicleApi,
  batchImportVehiclesApi,
} from '@/lib/api/server/administration'

export async function createGiftRequisition(data: Record<string, unknown>): Promise<unknown> {
  return createGiftRequisitionApi(data)
}

export async function updateGiftRequisition(id: string, data: Record<string, unknown>): Promise<unknown> {
  return updateGiftRequisitionApi(id, data)
}

export async function deleteGiftRequisition(id: string): Promise<unknown> {
  return deleteGiftRequisitionApi(id)
}

export async function createRegulation(data: Record<string, unknown>): Promise<unknown> {
  return createRegulationApi(data)
}

export async function updateRegulation(id: string, data: Record<string, unknown>): Promise<unknown> {
  return updateRegulationApi(id, data)
}

export async function deleteRegulation(id: string): Promise<unknown> {
  return deleteRegulationApi(id)
}

export async function extractRegulationText(data: { file_name?: string; file_type?: string; file_data?: string }): Promise<{ code: number; message: string; data: { text: string; source: string } }> {
  return extractRegulationTextApi(data) as Promise<{ code: number; message: string; data: { text: string; source: string } }>
}

export async function createGiftInventory(data: Record<string, unknown>): Promise<unknown> {
  return createGiftInventoryApi(data)
}

export async function updateGiftInventory(id: string, data: Record<string, unknown>): Promise<unknown> {
  return updateGiftInventoryApi(id, data)
}

export async function deleteGiftInventory(id: string): Promise<unknown> {
  return deleteGiftInventoryApi(id)
}

export async function createVehicle(data: Record<string, unknown>): Promise<unknown> {
  return createVehicleApi(data)
}

export async function updateVehicle(id: string, data: Record<string, unknown>): Promise<unknown> {
  return updateVehicleApi(id, data)
}

export async function deleteVehicle(id: string): Promise<unknown> {
  return deleteVehicleApi(id)
}

export async function batchImportVehicles(file: File): Promise<unknown> {
  const formData = new FormData()
  formData.append('file', file)
  return batchImportVehiclesApi(formData)
}
