import type { components } from '@/types/generated/schema'
export type CreateRoleInput = components['schemas']['RoleCreate']
export type UpdateRoleInput = components['schemas']['RoleUpdate']
export type AddPersonnelInput = components['schemas']['SpecialOperationPersonnelCreate']

// 角色
export interface EquipmentRole {
  id: string
  name: string
  code: string
  description: string | null
  scope: string
  is_active: boolean
  created_at: string
  updated_at: string
}



// 人员
export interface PersonnelRoleInfo {
  id: string
  name: string
  code: string
  scope: string
}

export interface PersonnelCategoryInfo {
  role_id: string
  role_name: string
  category_id: string
  category_name: string
}

export interface Personnel {
  id: string
  user_id: string | null
  name: string
  employee_no: string | null
  department: string | null
  position: string | null
  avatar_url: string | null
  feishu_user_id: string | null
  feishu_open_id: string | null
  mobile: string | null
  extended_attrs: Record<string, unknown> | null
  is_active: boolean
  roles: PersonnelRoleInfo[]
  categories: PersonnelCategoryInfo[]
  created_at: string
  updated_at: string
}

export interface PersonnelListResponse {
  items: Personnel[]
  total: number
  page: number
  page_size: number
}


export interface AssignRolesInput {
  role_ids: string[]
}

export interface CategoryAssignItem {
  role_id: string
  category_id: string
}

export interface AssignCategoriesInput {
  categories: CategoryAssignItem[]
}

export interface Candidate {
  personnel_id: string
  name: string
  department: string | null
  feishu_user_id: string | null
  feishu_open_id: string | null
  roles: PersonnelRoleInfo[]
}
