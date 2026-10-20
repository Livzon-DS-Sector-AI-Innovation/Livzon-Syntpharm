export interface UserManagementItem {
  id: string
  username: string
  name: string
  email: string
  mobile: string
  employee_no: string
  department: string
  position: string
  role: string
  /** 有效角色名列表（来自授权管理里的授权） */
  roles?: string[]
  status: string
  is_active: boolean
  auth_source?: string
  feishu_user_id?: string | null
  feishu_open_id?: string | null
  feishu_union_id?: string | null
  avatar_url?: string | null
  last_login_at?: string | null
  /** 是否强制修改密码（管理员重置后为 true，用户自助改密后清除） */
  must_change_password?: boolean
  /** 密码最后修改时间 */
  password_updated_at?: string | null
  /** 解绑飞书时该账号是否被一并软删除（仅解绑响应返回） */
  account_deleted?: boolean
  created_at: string
  updated_at: string
}

export interface FeishuBindRequest {
  source_user_id: string
}

export interface FeishuBindResult {
  moved_grants: number
  deduplicated_grants: number
}

export interface UserManagementListResponse {
  items: UserManagementItem[]
  total: number
}

export interface LocalUserCreate {
  username: string
  password: string
  name: string
  email?: string | null
  mobile?: string | null
  employee_no?: string | null
  department?: string | null
  position?: string | null
  status?: string
}

export interface UserManagementUpdate {
  /** 登录用户名创建后不可修改，更新请求不提交该字段 */
  name?: string
  email?: string | null
  mobile?: string | null
  employee_no?: string | null
  department?: string | null
  position?: string | null
  status?: string
  is_active?: boolean
}

export interface PasswordResetRequest {
  /** 留空 = 随机生成（明文只在响应里返回一次） */
  password?: string
}

export interface PasswordResetResult {
  message: string
  /** 仅「随机生成」时返回，供管理员一次性抄给用户；不落库，关闭弹窗后无法再看 */
  password?: string | null
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/** 在线会话（来自 GET /identity/sessions，Redis 会话索引）。 */
export interface UserSession {
  jti: string
  user_id: string
  name: string
  username: string
  ip_address: string | null
  user_agent: string | null
  created_at: string
}
