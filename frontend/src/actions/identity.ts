'use server'

import { cookies } from 'next/headers'
import { getLoginLogsApi } from '@/lib/api/server/identity'

export interface LoginLog {
  id: string
  user_id: string | null
  user_name: string | null
  login_type: string
  status: string
  ip_address: string | null
  user_agent: string | null
  error_message: string | null
  created_at: string
}

export interface LoginLogListResponse {
  items: LoginLog[]
  total: number
  page: number
  page_size: number
}

export async function getLoginLogs(params: {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
}): Promise<LoginLogListResponse> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')

  const result = await getLoginLogsApi(token?.value || '', params)
  return result
}