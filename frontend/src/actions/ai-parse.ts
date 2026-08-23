'use server'

import { revalidatePath } from 'next/cache'
import {
  parseExperimentRecord as parseExperimentRecordApi,
  parseProcessParameters as parseProcessParametersApi,
} from '@/lib/api/server/ai'

export async function parseExperimentRecord(file: File, type: 'lab_confirmation' | 'scale_up'): Promise<unknown> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('parse_type', type)

  const result = await parseExperimentRecordApi(formData)
  revalidatePath('/research/process-optimization')
  return result as any
}

export async function parseProcessParameters(content: string, type: 'lab_confirmation' | 'scale_up'): Promise<unknown> {
  const result = await parseProcessParametersApi(content, type)
  return result as any
}
