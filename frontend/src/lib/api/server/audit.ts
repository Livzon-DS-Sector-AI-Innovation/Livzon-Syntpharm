import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function getAuditLogsApi(
  authToken: string,
  params: {
    page?: number
    page_size?: number
    user_id?: string
    action?: string
    resource_type?: string
    keyword?: string
  },
) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.user_id) searchParams.set('user_id', params.user_id)
  if (params.action) searchParams.set('action', params.action)
  if (params.resource_type) searchParams.set('resource_type', params.resource_type)
  if (params.keyword) searchParams.set('keyword', params.keyword)

  return apiFetch(`${getApiBaseUrl()}/api/v1/audit/logs?${searchParams.toString()}`, {
    headers: { Authorization: `Bearer ${authToken}` },
  })
}
