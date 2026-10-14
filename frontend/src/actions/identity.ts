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

  // apiFetch 返回的是完整信封 { code, data, message }，必须解包出 data。
  // 不解包的话组件里的 items / total 全是 undefined → 表格永远空白
  // （与用户列表曾经的坑同源）。
  const res = (await getLoginLogsApi(token?.value || '', params)) as {
    data?: LoginLogListResponse
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
