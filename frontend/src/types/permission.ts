/**
 * 权限管理类型。
 *
 * API 响应契约类型（角色/授权/权限/接口绑定/权限树）从 `@/types/generated/schema` 派生；
 * 表单输入与纯前端 UI 类型（下拉选项、批量结果等）按规范保留手写。
 */
import type { components } from '@/types/generated/schema'

export type RoleCategory = 'platform' | 'module'
export type ScopeType = 'self' | 'department' | 'department_and_children' | 'all'

export type RoleDetail = components['schemas']['RoleDetailResponse']
export type GrantItem = components['schemas']['GrantResponse']
export type PermissionItem = components['schemas']['PermissionResponse']
export type ApiBindingItem = components['schemas']['ApiBindingResponse']
export type PermissionTreeNode = components['schemas']['PermissionTreeNode']
export type PermissionTreeData = components['schemas']['PermissionTreeData']

// ── 表单 / 纯前端 UI 类型（非 API 响应契约，保留手写） ──

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

export interface UserOption {
  id: string
  name: string
  username: string | null
}

export interface DepartmentOption {
  code: string
  name: string
}
