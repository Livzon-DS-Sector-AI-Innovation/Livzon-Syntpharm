'use server'

import { cookies } from 'next/headers'
import { revalidatePath } from 'next/cache'
import { unwrapResponse } from '@/lib/api/server/base'
import { normalizeBatchResult } from '@/lib/api/batch'
import {
  batchDeleteGrants as batchDeleteGrantsApi,
  batchDeleteRoles as batchDeleteRolesApi,
  batchUpdateGrantStatus as batchUpdateGrantStatusApi,
  batchUpdateRoleStatus as batchUpdateRoleStatusApi,
  createGrant as createGrantApi,
  createRole as createRoleApi,
  deleteGrant as deleteGrantApi,
  deleteRole as deleteRoleApi,
  getApiBindings as getApiBindingsApi,
  getDepartments as getDepartmentsApi,
  getGrants as getGrantsApi,
  getMyPermissions as getMyPermissionsApi,
  getPermissions as getPermissionsApi,
  getPermissionPreview as getPermissionPreviewApi,
  getPermissionTree as getPermissionTreeApi,
  getRoles as getRolesApi,
  getUsersForSelect,
  updateGrant as updateGrantApi,
  updateRole as updateRoleApi,
} from '@/lib/api/server/permission'
import type {
  ApiBindingItem,
  BatchResult,
  DepartmentOption,
  GrantCreateInput,
  GrantItem,
  GrantUpdateInput,
  MyPermissions,
  PermissionActionResult,
  PermissionItem,
  PermissionTreeData,
  RoleCreateInput,
  RoleDetail,
  RoleUpdateInput,
  UserOption,
} from '@/types/permission'

async function getAuthToken(): Promise<string | undefined> {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

const PERMISSION_PATH = '/settings/permission'

// ── 角色 ──────────────────────────────────────────────────────────

export async function fetchRoles(): Promise<RoleDetail[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getRolesApi(token)) ?? []
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

// ── 授权 ──────────────────────────────────────────────────────────

export async function fetchGrants(userId?: string): Promise<GrantItem[]> {
  const token = await getAuthToken()
  return unwrapResponse(await getGrantsApi(userId, token)) ?? []
}

export async function createGrant(data: GrantCreateInput): Promise<GrantItem> {
  const token = await getAuthToken()
  const grant = unwrapResponse(await createGrantApi(data, token))
  revalidatePath(PERMISSION_PATH)
  return grant
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

// ── 用户选择列表 ──────────────────────────────────────────────────

export async function fetchUserOptions(): Promise<UserOption[]> {
  const token = await getAuthToken()
  const data = unwrapResponse(await getUsersForSelect(token))
  return (data?.items ?? []).map(item => ({ ...item, username: item.username ?? null }))
}

// ── 当前用户权限 ──────────────────────────────────────────────────

export async function fetchMyPermissions(): Promise<MyPermissions> {
  const token = await getAuthToken()
  const data = unwrapResponse(await getMyPermissionsApi(token))
  return data ?? { permissions: [], is_superuser: false }
}
