import { apiFetch } from '@/lib/api/server/base'

export async function updateSystemSettings(data: Record<string, unknown>) {
  return apiFetch('/api/v1/hr/system-settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}
