import { apiFetch } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

export async function updateSystemSettings(
  data: components['schemas']['HrSystemSettingsUpdate'],
): Promise<components['schemas']['HrSystemSettingsSaveResponse']> {
  return apiFetch('/api/v1/hr/system-settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}
