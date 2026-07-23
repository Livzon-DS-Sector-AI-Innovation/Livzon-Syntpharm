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
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserManagementListResponse {
  items: UserManagementItem[]
  total: number
}

export interface LocalUserCreate {
  username: string
  password: string
  role?: string
}

export interface UserManagementUpdate {
  username?: string
  name?: string
  email?: string | null
  mobile?: string | null
  employee_no?: string | null
  department?: string | null
  position?: string | null
  role?: string
  status?: string
  is_active?: boolean
}

export interface PasswordResetRequest {
  password: string
}
