'use server'

import { revalidatePath } from 'next/cache'

import {
  createEquipmentFacilityHazard as apiCreateEquipmentFacilityHazard,
  createWorkActivityHazard as apiCreateWorkActivityHazard,
  deleteEquipmentFacilityHazard as apiDeleteEquipmentFacilityHazard,
  deleteWorkActivityHazard as apiDeleteWorkActivityHazard,
  exportEquipmentFacilityHazards as apiExportEquipmentFacilityHazards,
  exportWorkActivityHazards as apiExportWorkActivityHazards,
  updateEquipmentFacilityHazard as apiUpdateEquipmentFacilityHazard,
  updateWorkActivityHazard as apiUpdateWorkActivityHazard,
} from '@/lib/api/server/risk-grading'
import type {
  EquipmentFacilityHazardCreate,
  EquipmentFacilityHazardExportParams,
  WorkActivityHazardCreate,
  WorkActivityHazardExportParams,
} from '@/types/safety/risk-grading'

const LEDGER_PATH = '/safety/risk-grading/work-activity-ledger'
const EQUIPMENT_LEDGER_PATH = '/safety/risk-grading/equipment-ledger'

export async function createWorkActivityHazardAction(data: WorkActivityHazardCreate) {
  const result = await apiCreateWorkActivityHazard(data)
  revalidatePath(LEDGER_PATH)
  return result
}

export async function updateWorkActivityHazardAction(id: string, data: WorkActivityHazardCreate) {
  const result = await apiUpdateWorkActivityHazard(id, data)
  revalidatePath(LEDGER_PATH)
  return result
}

export async function deleteWorkActivityHazardAction(id: string) {
  const result = await apiDeleteWorkActivityHazard(id)
  revalidatePath(LEDGER_PATH)
  return result
}

export async function exportWorkActivityHazardsAction(params?: WorkActivityHazardExportParams) {
  return apiExportWorkActivityHazards(params)
}

export async function createEquipmentFacilityHazardAction(data: EquipmentFacilityHazardCreate) {
  const result = await apiCreateEquipmentFacilityHazard(data)
  revalidatePath(EQUIPMENT_LEDGER_PATH)
  return result
}

export async function updateEquipmentFacilityHazardAction(id: string, data: EquipmentFacilityHazardCreate) {
  const result = await apiUpdateEquipmentFacilityHazard(id, data)
  revalidatePath(EQUIPMENT_LEDGER_PATH)
  return result
}

export async function deleteEquipmentFacilityHazardAction(id: string) {
  const result = await apiDeleteEquipmentFacilityHazard(id)
  revalidatePath(EQUIPMENT_LEDGER_PATH)
  return result
}

export async function exportEquipmentFacilityHazardsAction(params?: EquipmentFacilityHazardExportParams) {
  return apiExportEquipmentFacilityHazards(params)
}
