export interface UserManagementItem {
  id: string
  username: string
  role: string
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type UserManagementListResponse = UserManagementItem[]

export interface LocalUserCreate {
  username: string
  password: string
  role?: string
}

export interface UserManagementUpdate {
  username?: string
  role?: string
  status?: string
  is_active?: boolean
}

export interface PasswordResetRequest {
  new_password: string
}
