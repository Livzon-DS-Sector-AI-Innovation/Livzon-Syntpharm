/**
 * 权限管理 UI 类型（手写，对应后端 permission 模块 schema）。
 */

export type RoleCategory = 'platform' | 'module'
export type ScopeType = 'self' | 'department' | 'department_and_children' | 'all'

export interface RoleDetail {
  id: string
  code: string
  name: string
  category: RoleCategory
  module_code: string | null
  description: string | null
  is_builtin: boolean
  is_superuser: boolean
  status: string
  permission_codes: string[]
}

export interface RoleCreateInput {
  code: string
  name: string
  category: RoleCategory
  module_code?: string | null
  description?: string | null
  permission_codes?: string[]
}

export interface RoleUpdateInput {
  name?: string
  description?: string | null
  permission_codes?: string[]
  status?: string
}

/** 批量操作失败项（后端统一结构）。 */
export interface BatchFailureItem {
  key: string
  label?: string | null
  reason: string
}

/** 批量操作结果：成功 id 列表 + 失败明细。 */
export interface BatchResult {
  succeeded: string[]
  failed: BatchFailureItem[]
}

export interface PermissionItem {
  id: string
  code: string
  name: string
  module: string
  resource: string
  action: string
  description: string | null
  status: string
  is_builtin: boolean
}

export interface GrantItem {
  id: string
  user_id: string
  role_id: string
  scope_type: ScopeType
  scope_dept_codes: string[] | null
  status: string
  granted_by: string | null
  version: number
  role_code: string | null
  role_name: string | null
  user_name: string | null
}

export interface GrantCreateInput {
  user_id: string
  role_id: string
  scope_type: ScopeType
  scope_dept_codes?: string[] | null
}

export interface GrantUpdateInput {
  scope_type?: ScopeType
  scope_dept_codes?: string[] | null
  status?: string
}

export interface ApiBindingItem {
  id: string
  permission_code: string
  method: string
  route_template: string
  scope_required: boolean
  status: string
}

export interface UserOption {
  id: string
  name: string
  username: string | null
}

export interface DepartmentOption {
  code: string
  name: string
}

export interface PermissionTreeNode {
  key: string
  title: string
  type: 'module' | 'resource' | 'permission'
  code: string | null
  kind: string | null
  status: string | null
  description: string | null
  binding_count: number
  disabled: boolean
  children: PermissionTreeNode[]
}

export interface PermissionTreeData {
  tree: PermissionTreeNode[]
  total_permissions: number
  total_modules: number
}
