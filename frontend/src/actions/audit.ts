'use server'

import { cookies } from 'next/headers'
import { getAuditLogsApi } from '@/lib/api/server/audit'
import type { AuditLogListResponse } from '@/types/audit'

export async function getAuditLogs(params: {
  page?: number
  page_size?: number
  user_id?: string
  action?: string
  resource_type?: string
  keyword?: string
}): Promise<AuditLogListResponse> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')

  const res = (await getAuditLogsApi(token?.value || '', params)) as {
    data?: AuditLogListResponse
  }

  return (
    res?.data ?? {
      items: [],
      total: 0,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
    }
  )
}
