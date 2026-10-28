/**
 * 权限管理类型。
 *
 * API 请求/响应契约类型全部从 `@/types/generated/schema` 派生；
 * 仅保留纯前端 UI 类型（字面量联合、下拉选项投影）与 Server Action 结果类型。
 */
import type { components } from '@/types/generated/schema'

export type RoleDetail = components['schemas']['RoleDetailResponse']
export type GrantItem = components['schemas']['GrantResponse']
export type PermissionItem = components['schemas']['PermissionResponse']
export type ApiBindingItem = components['schemas']['ApiBindingResponse']
export type PermissionTreeNode = components['schemas']['PermissionTreeNode']
export type PermissionTreeData = components['schemas']['PermissionTreeData']
export type MyPermissions = components['schemas']['MyPermissionsData']

// ── 请求契约类型 ──

export type RoleCreateInput = components['schemas']['app__platform__permission__schemas__RoleCreate']
export type RoleUpdateInput = components['schemas']['app__platform__permission__schemas__RoleUpdate']
export type GrantCreateInput = components['schemas']['GrantCreate']
export type GrantUpdateInput = components['schemas']['GrantUpdate']
export type DepartmentOption = components['schemas']['DepartmentOption']

export type { BatchFailureItem, BatchResult } from '@/types/batch'

/**
 * 权限写操作统一返回结果对象，业务错误（如「角色编码已存在」）不抛异常。
 * 定义在类型文件而不是 `actions/permission.ts`：`'use server'` 文件只允许导出
 * 异步函数，导出类型会破坏「服务端动作模块」的边界约定。
 */
export type PermissionActionResult<T> = { ok: true; data: T } | { ok: false; message: string }

// ── 纯前端 UI 类型（字面量联合 / 下拉选项投影，非 API 响应契约） ──

export type RoleCategory = 'platform' | 'module'
export type ScopeType = 'self' | 'department' | 'department_and_children' | 'all'

export interface UserOption {
  id: string
  name: string
  username: string | null
}
