'use server'

import { revalidatePath } from 'next/cache'
import { updateSystemSettings as updateSystemSettingsApi } from '@/lib/api/server/admin'

export async function updateSystemSettings(data: Record<string, unknown>) {
  const res = await updateSystemSettingsApi(data)
  revalidatePath('/hr/system-settings')
  return res as any
}
