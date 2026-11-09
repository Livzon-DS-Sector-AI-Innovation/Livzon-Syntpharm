'use server'

import { revalidatePath } from 'next/cache'

import { createWorkActivityHazard as apiCreateWorkActivityHazard } from '@/lib/api/server/risk-grading'
import type { WorkActivityHazardCreate } from '@/types/safety/risk-grading'

const LEDGER_PATH = '/safety/risk-grading/work-activity-ledger'

export async function createWorkActivityHazardAction(data: WorkActivityHazardCreate) {
  const result = await apiCreateWorkActivityHazard(data)
  revalidatePath(LEDGER_PATH)
  return result
}
