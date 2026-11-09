'use server'

import { revalidatePath } from 'next/cache'

import {
  createWorkActivityHazard as apiCreateWorkActivityHazard,
  deleteWorkActivityHazard as apiDeleteWorkActivityHazard,
  exportWorkActivityHazards as apiExportWorkActivityHazards,
  updateWorkActivityHazard as apiUpdateWorkActivityHazard,
} from '@/lib/api/server/risk-grading'
import type {
  WorkActivityHazardCreate,
  WorkActivityHazardExportParams,
} from '@/types/safety/risk-grading'

const LEDGER_PATH = '/safety/risk-grading/work-activity-ledger'

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
