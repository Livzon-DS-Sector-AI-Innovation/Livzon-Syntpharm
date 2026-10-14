export interface AuditLogItem {
  id: string
  user_id: string | null
  user_name: string | null
  username: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  old_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  extra: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogItem[]
  total: number
  page: number
  page_size: number
}
