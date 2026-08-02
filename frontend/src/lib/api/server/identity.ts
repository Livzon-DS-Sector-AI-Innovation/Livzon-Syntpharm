import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function getLoginLogsApi(
  authToken: string,
  params: {
    page?: number
    page_size?: number
    status?: string
    keyword?: string
  }
) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.status) searchParams.set('status', params.status)
  if (params.keyword) searchParams.set('keyword', params.keyword)

  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/login-logs?${searchParams.toString()}`, {
    headers: { Authorization: `Bearer ${authToken}` },
  })
}