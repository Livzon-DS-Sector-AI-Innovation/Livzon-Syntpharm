'use server'

import { revalidatePath } from 'next/cache'
import { getServerToken } from '@/lib/auth'
import type { components } from '@/types/generated/schema'
import {
  createRoleApi, updateRoleApi, deleteRoleApi,
  addPersonnelApi, deletePersonnelApi, assignRolesApi,
  assignCategoriesApi, refreshFeishuApi,
} from '@/lib/api/server/equipment-personnel'

async function authHeaders(): Promise<Record<string, string>> {
  return { Authorization: `Bearer ${await getServerToken()}` }
}

export async function createRole(data: components['schemas']['RoleCreate']) {
  const result = await createRoleApi(data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function updateRole(id: string, data: components['schemas']['RoleUpdate']) {
  const result = await updateRoleApi(id, data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function deleteRole(id: string) {
  const result = await deleteRoleApi(id, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function addPersonnel(data: components['schemas']['PersonnelAddRequest']) {
  const result = await addPersonnelApi(data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function deletePersonnel(id: string) {
  const result = await deletePersonnelApi(id, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function assignRoles(personnelId: string, data: components['schemas']['PersonnelRoleAssign']) {
  const result = await assignRolesApi(personnelId, data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function assignCategories(personnelId: string, data: components['schemas']['PersonnelCategoryAssign']) {
  const result = await assignCategoriesApi(personnelId, data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function refreshFeishu() {
  const result = await refreshFeishuApi(await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}
