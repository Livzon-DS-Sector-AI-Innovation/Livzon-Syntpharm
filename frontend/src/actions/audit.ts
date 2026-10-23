'use server'

import { cookies } from 'next/headers'
import { unwrapResponse } from '@/lib/api/server/base'
import { getAuditLogsApi } from '@/lib/api/server/audit'
import type { AuditLogListResponse, AuditLogQuery } from '@/types/audit'

export async function getAuditLogs(params: AuditLogQuery): Promise<AuditLogListResponse> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')

  const data = unwrapResponse(await getAuditLogsApi(token?.value || '', params))

  return (
    data ?? {
      items: [],
      total: 0,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
    }
  )
}
