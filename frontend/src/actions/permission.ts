'use server'

import { cookies } from 'next/headers'
import { revalidatePath } from 'next/cache'
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

/**
 * 角色写操作统一返回结果对象，业务错误（如「角色编码已存在」）不抛异常。
 * 原因：Server Action 抛错会让整个 RSC 请求返回 500，客户端只能拿到脱敏的通用错误。
 */
export type PermissionActionResult<T> = { ok: true; data: T } | { ok: false; message: string }

const PERMISSION_PATH = '/settings/permission'

// ── 角色 ──────────────────────────────────────────────────────────

export async function fetchRoles(): Promise<RoleDetail[]> {
  const token = await getAuthToken()
  const res = (await getRolesApi(token)) as { data: RoleDetail[] }
  return res.data ?? []
}

/** 授权数据范围选部门用的部门选项（hr.departments.code + name）。 */
export async function fetchDepartmentOptions(): Promise<DepartmentOption[]> {
  const token = await getAuthToken()
  const res = (await getDepartmentsApi(token)) as { data: DepartmentOption[] }
  return res.data ?? []
}

/** 预览某用户的生效权限码 + 是否超管（授权管理「生效预览」用）。 */
export async function fetchUserPreview(
  userId: string,
): Promise<{ permissions: string[]; is_superuser: boolean }> {
  const token = await getAuthToken()
  const res = (await getPermissionPreviewApi(userId, token)) as {
    data: { permissions: string[]; is_superuser: boolean }
  }
  return res.data ?? { permissions: [], is_superuser: false }
}

export async function createRole(data: RoleCreateInput): Promise<PermissionActionResult<RoleDetail>> {
  const token = await getAuthToken()
  try {
    const res = (await createRoleApi(data, token)) as { data: RoleDetail }
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: res.data }
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
    const res = (await updateRoleApi(id, data, token)) as { data: RoleDetail }
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: res.data }
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
  const res = (await getPermissionsApi(token)) as { data: PermissionItem[] }
  return res.data ?? []
}

export async function fetchPermissionTree(): Promise<PermissionTreeData> {
  const token = await getAuthToken()
  const res = (await getPermissionTreeApi(token)) as { data: PermissionTreeData }
  return res.data ?? { tree: [], total_permissions: 0, total_modules: 0 }
}

export async function fetchApiBindings(): Promise<ApiBindingItem[]> {
  const token = await getAuthToken()
  const res = (await getApiBindingsApi(token)) as { data: ApiBindingItem[] }
  return res.data ?? []
}

// ── 授权 ──────────────────────────────────────────────────────────

export async function fetchGrants(userId?: string): Promise<GrantItem[]> {
  const token = await getAuthToken()
  const res = (await getGrantsApi(userId, token)) as { data: GrantItem[] }
  return res.data ?? []
}

export async function createGrant(data: GrantCreateInput): Promise<GrantItem> {
  const token = await getAuthToken()
  const res = (await createGrantApi(data, token)) as { data: GrantItem }
  revalidatePath(PERMISSION_PATH)
  return res.data
}

export async function updateGrant(id: string, data: GrantUpdateInput): Promise<GrantItem> {
  const token = await getAuthToken()
  const res = (await updateGrantApi(id, data, token)) as { data: GrantItem }
  revalidatePath(PERMISSION_PATH)
  return res.data
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
    const res = (await batchUpdateRoleStatusApi({ ids, status }, token)) as { data: BatchResult }
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: res.data }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量操作角色失败' }
  }
}

/** 批量删除角色（内置 / 超管角色由后端跳过并返回原因）。 */
export async function batchDeleteRoles(ids: string[]): Promise<PermissionActionResult<BatchResult>> {
  const token = await getAuthToken()
  try {
    const res = (await batchDeleteRolesApi({ ids }, token)) as { data: BatchResult }
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: res.data }
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
    const res = (await batchUpdateGrantStatusApi({ ids, status }, token)) as { data: BatchResult }
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: res.data }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量操作授权失败' }
  }
}

/** 批量删除授权（自己 / 越级 / 最后超管由后端跳过并返回原因）。 */
export async function batchDeleteGrants(ids: string[]): Promise<PermissionActionResult<BatchResult>> {
  const token = await getAuthToken()
  try {
    const res = (await batchDeleteGrantsApi({ ids }, token)) as { data: BatchResult }
    revalidatePath(PERMISSION_PATH)
    return { ok: true, data: res.data }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量删除授权失败' }
  }
}

// ── 用户选择列表 ──────────────────────────────────────────────────

export async function fetchUserOptions(): Promise<UserOption[]> {
  const token = await getAuthToken()
  const res = (await getUsersForSelect(token)) as {
    data: { items: Array<{ id: string; name: string; username: string | null }> }
  }
  return res.data?.items ?? []
}

// ── 当前用户权限 ──────────────────────────────────────────────────

export async function fetchMyPermissions(): Promise<{
  permissions: string[]
  is_superuser: boolean
}> {
  const token = await getAuthToken()
  const res = (await getMyPermissionsApi(token)) as {
    data: { permissions: string[]; is_superuser: boolean }
  }
  return res.data ?? { permissions: [], is_superuser: false }
}
