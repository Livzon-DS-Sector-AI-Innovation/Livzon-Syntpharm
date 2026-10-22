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
  /** 是否超级管理员：批量选择时该行复选框置灰 */
  is_superuser?: boolean
  created_at: string
  updated_at: string
}

/** 批量启用/禁用请求。 */
export interface UserBatchStatusRequest {
  user_ids: string[]
  status: 'active' | 'disabled'
}

/** 批量启用/禁用结果：逐条汇总，失败项带原因。 */
export interface UserBatchStatusResult {
  succeeded: string[]
  failed: { id: string; username?: string | null; reason: string }[]
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
  /** 留空 = 后端自动生成一次性初始密码（只在创建响应里返回一次） */
  password?: string
  name: string
  email?: string | null
  mobile?: string | null
  employee_no?: string | null
  department?: string | null
  position?: string | null
  status?: string
}

/** 新建账号的响应：比列表项多一个一次性初始密码。 */
export interface UserCreateResult extends UserManagementItem {
  /** 自动生成时才有值；不落库，关闭弹窗后无法再次查看 */
  initial_password?: string | null
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

/** 删除账号结果：软删除，同时清空授权并吊销会话。 */
export interface UserDeleteResult {
  id: string
  username?: string | null
  /** 被清空的角色授权条数 */
  revoked_grants: number
  /** 被吊销的在线会话数 */
  revoked_sessions: number
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
