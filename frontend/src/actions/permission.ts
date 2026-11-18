'use server'

import { cookies } from 'next/headers'
import { revalidatePath } from 'next/cache'
import { unwrapResponse } from '@/lib/api/server/base'
import { normalizeBatchResult } from '@/lib/api/batch'
import {
  assignModuleAdmin as assignModuleAdminApi,
  batchCreateGrants as batchCreateGrantsApi,
  batchDeleteGrants as batchDeleteGrantsApi,
  batchDeleteRoles as batchDeleteRolesApi,
  batchUpdateGrantStatus as batchUpdateGrantStatusApi,
  batchUpdateRoleStatus as batchUpdateRoleStatusApi,
  createGrant as createGrantApi,
  createRole as createRoleApi,
  deleteGrant as deleteGrantApi,
  deleteRole as deleteRoleApi,
  disableUserAccess as disableUserAccessApi,
  getApiBindings as getApiBindingsApi,
  getDepartments as getDepartmentsApi,
  getGrants as getGrantsApi,
  getModuleAdmins as getModuleAdminsApi,
  getMyPermissions as getMyPermissionsApi,
  getPermissions as getPermissionsApi,
  getPermissionApiBindings as getPermissionApiBindingsApi,
  getPermissionPreview as getPermissionPreviewApi,
  getPermissionTree as getPermissionTreeApi,
  getRoles as getRolesApi,
  resetRoleToDefault as resetRoleToDefaultApi,
  getUserAccess as getUserAccessApi,
  removeModuleAdmin as removeModuleAdminApi,
  updateGrant as updateGrantApi,
  updateRole as updateRoleApi,
} from '@/lib/api/server/permission'
import type {
  ApiBindingItem,
  BatchResult,
  DepartmentOption,
  GrantBatchCreateInput,
  GrantCreateInput,
  GrantItem,
  GrantUpdateInput,
  ModuleAdminAssignInput,
  ModuleAdminGroup,
  MyPermissions,
  PermissionActionResult,
  PermissionApiBindingItem,
  PermissionItem,
  PermissionTreeData,
  RoleCreateInput,
  RoleDetail,
  RoleUpdateInput,
  UserAccessData,
} from '@/types/permission'

async function getAuthToken(): Promise<string | undefined> {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

const PERMISSION_PATH = '/settings/permission'

// ── 角色 ──────────────────────────────────────────────────────────

/** `moduleCode` 传入时只返回该模块的角色（模块配置页用；后端同时做作用域校验）。 */
export async function fetchRoles(moduleCode?: string): Promise<RoleDetail[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getRolesApi(moduleCode, token)) ?? []
}

/** 授权数据范围选部门用的部门选项（hr.departments.code + name）。 */
export async function fetchDepartmentOptions(): Promise<DepartmentOption[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getDepartmentsApi(token)) ?? []
}

/** 预览某用户的生效权限码 + 是否超管（授权管理「生效预览」用）。 */
export async function fetchUserPreview(userId: string): Promise<MyPermissions> {
  const token = await getAuthToken()
  const data = unwrapResponse(await getPermissionPreviewApi(userId, token))
  return data ?? { permissions: [], is_superuser: false }
}

export async function createRole(data: RoleCreateInput): Promise<PermissionActionResult<RoleDetail>> {
  const token = await getAuthToken()
  try {
    const role = unwrapResponse(await createRoleApi(data, token))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: role }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '创建角色失败' }
  }
}

export async function updateRole(
  id: string,
  data: RoleUpdateInput,
): Promise<PermissionActionResult<RoleDetail>> {
  const token = await getAuthToken()
  try {
    const role = unwrapResponse(await updateRoleApi(id, data, token))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: role }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '更新角色失败' }
  }
}

/** 把内置角色权限恢复为注册表默认值，并重新纳入启动自动扩量。 */
export async function resetRoleToDefault(id: string): Promise<PermissionActionResult<RoleDetail>> {
  const token = await getAuthToken()
  try {
    const role = unwrapResponse(await resetRoleToDefaultApi(id, token))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: role }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '恢复默认失败' }
  }
}

export async function deleteRole(id: string): Promise<PermissionActionResult<null>> {
  const token = await getAuthToken()
  try {
    await deleteRoleApi(id, token)
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: null }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '删除角色失败' }
  }
}

// ── 权限目录 / 权限树 / 接口绑定 ──────────────────────────────────

export async function fetchPermissions(): Promise<PermissionItem[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getPermissionsApi(token)) ?? []
}

export async function fetchPermissionTree(): Promise<PermissionTreeData> {
  const token = await getAuthToken()
  return unwrapResponse(await getPermissionTreeApi(token)) ?? { tree: [], total_permissions: 0, total_modules: 0 }
}

export async function fetchApiBindings(): Promise<ApiBindingItem[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getApiBindingsApi(token)) ?? []
}

/** 单个权限码绑定的接口清单（权限树点击「N 个接口」时才请求）。 */
export async function fetchPermissionApiBindings(code: string): Promise<PermissionApiBindingItem[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getPermissionApiBindingsApi(code, token)) ?? []
}

// ── 授权 ──────────────────────────────────────────────────────────

export async function fetchGrants(userId?: string, moduleCode?: string): Promise<GrantItem[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getGrantsApi(userId, moduleCode, token)) ?? []
}

// ── 模块负责人 / 模块管理员（系统管理员侧）─────────────────────────────

export async function fetchModuleAdmins(): Promise<ModuleAdminGroup[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getModuleAdminsApi(token)) ?? []
}

export async function assignModuleAdmin(data: ModuleAdminAssignInput): Promise<PermissionActionResult<null>> {
  const token = await getAuthToken()
  try {
    await assignModuleAdminApi(data, token)
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: null }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '指派失败' }
  }
}

export async function removeModuleAdmin(data: ModuleAdminAssignInput): Promise<PermissionActionResult<null>> {
  const token = await getAuthToken()
  try {
    await removeModuleAdminApi(data, token)
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: null }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '移除失败' }
  }
}

// ── 按人查权限（离职 / 调岗收权）──────────────────────────────────────

export async function fetchUserAccess(userId: string): Promise<UserAccessData | null> {
  const token = await getAuthToken()
  return unwrapResponse(await getUserAccessApi(userId, token)) ?? null
}

export async function disableAllUserAccess(userId: string): Promise<PermissionActionResult<number>> {
  const token = await getAuthToken()
  try {
    const data = unwrapResponse(await disableUserAccessApi(userId, token))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: data?.disabled ?? 0 }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '停用失败' }
  }
}

export async function createGrant(data: GrantCreateInput): Promise<GrantItem> {
  const token = await getAuthToken()
  const grant = unwrapResponse(await createGrantApi(data, token))
  revalidatePath(PERMISSION_PATH)
  return grant
}

/** 批量授权：多用户 × 多角色，同一数据范围；已拥有组合由后端幂等跳过。 */
export async function batchCreateGrants(data: GrantBatchCreateInput): Promise<PermissionActionResult<BatchResult>> {
  const token = await getAuthToken()
  try {
    const result = normalizeBatchResult(unwrapResponse(await batchCreateGrantsApi(data, token)))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量授权失败' }
  }
}

export async function updateGrant(id: string, data: GrantUpdateInput): Promise<GrantItem> {
  const token = await getAuthToken()
  const grant = unwrapResponse(await updateGrantApi(id, data, token))
  revalidatePath(PERMISSION_PATH)
  return grant
}

export async function deleteGrant(id: string): Promise<void> {
  const token = await getAuthToken()
  await deleteGrantApi(id, token)
  revalidatePath(PERMISSION_PATH)
}

// ── 批量操作 ──────────────────────────────────────────────────────

/** 批量启用 / 停用角色（内置角色由后端跳过并返回原因）。 */
export async function batchUpdateRoleStatus(
  ids: string[],
  status: 'active' | 'disabled',
): Promise<PermissionActionResult<BatchResult>> {
  const token = await getAuthToken()
  try {
    const result = normalizeBatchResult(unwrapResponse(await batchUpdateRoleStatusApi({ ids, status }, token)))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量操作角色失败' }
  }
}

/** 批量删除角色（内置 / 超管角色由后端跳过并返回原因）。 */
export async function batchDeleteRoles(ids: string[]): Promise<PermissionActionResult<BatchResult>> {
  const token = await getAuthToken()
  try {
    const result = normalizeBatchResult(unwrapResponse(await batchDeleteRolesApi({ ids }, token)))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量删除角色失败' }
  }
}

/** 批量启用 / 停用授权（自己 / 越级 / 最后超管由后端跳过并返回原因）。 */
export async function batchUpdateGrantStatus(
  ids: string[],
  status: 'active' | 'disabled',
): Promise<PermissionActionResult<BatchResult>> {
  const token = await getAuthToken()
  try {
    const result = normalizeBatchResult(unwrapResponse(await batchUpdateGrantStatusApi({ ids, status }, token)))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量操作授权失败' }
  }
}

/** 批量删除授权（自己 / 越级 / 最后超管由后端跳过并返回原因）。 */
export async function batchDeleteGrants(ids: string[]): Promise<PermissionActionResult<BatchResult>> {
  const token = await getAuthToken()
  try {
    const result = normalizeBatchResult(unwrapResponse(await batchDeleteGrantsApi({ ids }, token)))
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量删除授权失败' }
  }
}

// ── 当前用户权限 ──────────────────────────────────────────────────

export async function fetchMyPermissions(): Promise<MyPermissions> {
  const token = await getAuthToken()
  const data = unwrapResponse(await getMyPermissionsApi(token))
  return data ?? { permissions: [], is_superuser: false }
}
