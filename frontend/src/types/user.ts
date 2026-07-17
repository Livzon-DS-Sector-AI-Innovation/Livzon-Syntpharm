/**
 * User TypeScript types
 *
 * This is a UI/display type representing the current authenticated user profile.
 * Per AGENTS.md: "允许手写前端 UI 类型，例如表单状态、筛选条件、表格状态、下拉选项、ViewModel/display 类型"
 *
 * The backend doesn't export this via OpenAPI because it's part of the auth system,
 * not a business API resource.
 */

export interface User {
  id: string
  name: string
  username: string | null
  status: 'active' | 'disabled'
  auth_source: 'local' | 'feishu'
  email: string | null
  mobile: string | null
  avatar_url: string | null
  employee_no: string | null
  department: string | null
  position: string | null
}

// Impersonation types
export interface ImpersonateUserInfo {
  id: string
  name: string
  employee_no?: string
  department?: string
}

// Extend ImpersonateUserInfo with position
export interface ImpersonateUserInfoExtended extends ImpersonateUserInfo {
  position?: string
}

// Impersonation status type
export interface ImpersonationStatus {
  is_impersonating: boolean
  original_user?: ImpersonateUserInfo
  impersonated_user?: ImpersonateUserInfo
}

// Extend ImpersonationStatus with real_user
export interface ImpersonationStatusExtended extends ImpersonationStatus {
  target_user?: ImpersonateUserInfo
  expires_at?: string
  real_user?: ImpersonateUserInfo
}