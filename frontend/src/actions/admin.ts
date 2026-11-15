'use server'

import { revalidatePath } from 'next/cache'
import type { components } from '@/types/generated/schema'
import { updateSystemSettings as updateSystemSettingsApi } from '@/lib/api/server/admin'

export async function updateSystemSettings(data: components['schemas']['HrSystemSettingsUpdate']) {
  const res = await updateSystemSettingsApi(data)
  revalidatePath('/hr/system-settings')
  return res
}
