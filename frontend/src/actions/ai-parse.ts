'use server'

import { parseExperimentRecord as parseExperimentRecordApi, parseProcessParameters as parseProcessParametersApi } from '@/lib/api/server/ai'
import { revalidatePath } from 'next/cache'

export async function parseExperimentRecord(content: string, type: 'lab_confirmation' | 'scale_up'): Promise<unknown> {
  const result = await parseExperimentRecordApi(content, type)
  revalidatePath('/research/process-optimization')
  return result
}

export async function parseProcessParameters(content: string, type: 'lab_confirmation' | 'scale_up'): Promise<unknown> {
  const result = await parseProcessParametersApi(content, type)
  revalidatePath('/research/process-optimization')
  return result
}
