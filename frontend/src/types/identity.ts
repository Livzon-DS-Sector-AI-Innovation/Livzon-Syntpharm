/**
 * 登录日志类型。
 *
 * 注：后端 `GET /api/v1/identity/login-logs` 目前没有声明 response_model，
 * OpenAPI 里是 inline schema，因此这里仍保留手写契约（补上后端模型后应改为
 * 从 `@/types/generated/schema` 派生）。
 */

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

/** 登录日志查询参数（actions 与 lib/api/server 共用一份，避免两层各写一遍）。 */
export interface LoginLogQuery {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
}
