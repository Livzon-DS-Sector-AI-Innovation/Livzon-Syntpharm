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
