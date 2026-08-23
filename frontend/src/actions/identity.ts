'use server'

import { cookies } from 'next/headers'
import { getLoginLogsApi } from '@/lib/api/server/identity'
import type { LoginLogListResponse } from '@/types/identity'

export async function getLoginLogs(params: {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
}): Promise<LoginLogListResponse> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')

  const result = await getLoginLogsApi(token?.value || '', params)
  return result as any
}