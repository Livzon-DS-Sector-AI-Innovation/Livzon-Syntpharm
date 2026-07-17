import { API_BASE_URL } from '@/lib/api/server/base'

export async function updateSystemSettings(data: Record<string, unknown>) {
  const url = `${API_BASE_URL}/api/v1/hr/system-settings`
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    cache: 'no-store',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.message || '保存设置失败')
  }
  return res.json()
}
