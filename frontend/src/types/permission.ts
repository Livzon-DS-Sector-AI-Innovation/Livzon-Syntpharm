/**
 * 权限管理类型。
 *
 * API 请求/响应契约类型全部从 `@/types/generated/schema` 派生；
 * 仅保留纯前端 UI 类型（字面量联合、下拉选项投影）。
 */
import type { components } from '@/types/generated/schema'

export type RoleDetail = components['schemas']['RoleDetailResponse']
export type GrantItem = components['schemas']['GrantResponse']
export type PermissionItem = components['schemas']['PermissionResponse']
export type ApiBindingItem = components['schemas']['ApiBindingResponse']
export type PermissionTreeNode = components['schemas']['PermissionTreeNode']
export type PermissionTreeData = components['schemas']['PermissionTreeData']

// ── 请求契约类型 ──

export type RoleCreateInput = components['schemas']['app__platform__permission__schemas__RoleCreate']
export type RoleUpdateInput = components['schemas']['app__platform__permission__schemas__RoleUpdate']
export type GrantCreateInput = components['schemas']['GrantCreate']
export type GrantUpdateInput = components['schemas']['GrantUpdate']
export type DepartmentOption = components['schemas']['DepartmentOption']

export type BatchFailureItem = components['schemas']['BatchFailure']

/** 批量操作结果：后端 schema 给 succeeded/failed 设了默认值，OpenAPI 标成可选；
 *  实际响应总会返回这两个数组，这里恢复成必填，避免消费端冗余判空。 */
export type BatchResult = {
  succeeded: NonNullable<components['schemas']['BatchResultData']['succeeded']>
  failed: NonNullable<components['schemas']['BatchResultData']['failed']>
}

// ── 纯前端 UI 类型（字面量联合 / 下拉选项投影，非 API 响应契约） ──

export type RoleCategory = 'platform' | 'module'
export type ScopeType = 'self' | 'department' | 'department_and_children' | 'all'

export interface UserOption {
  id: string
  name: string
  username: string | null
}
