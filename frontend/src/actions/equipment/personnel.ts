'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import type {
  CreateRoleInput, UpdateRoleInput, AddPersonnelInput,
  AssignRolesInput, AssignCategoriesInput,
} from '@/types/equipment'
import {
  createPersonnelRoleApi,
  updatePersonnelRoleApi,
  deletePersonnelRoleApi,
  addPersonnelApi,
  deletePersonnelApi,
  assignRolesApi,
  assignCategoriesApi,
  refreshFeishuApi,
} from '@/lib/api/server/equipment'


// ── 角色 Actions ──

export async function createRole(data: CreateRoleInput) {
  const authHeaders = await getAuthHeaders()
  const result = await createPersonnelRoleApi(data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result as any
}

export async function updateRole(id: string, data: UpdateRoleInput) {
  const authHeaders = await getAuthHeaders()
  const result = await updatePersonnelRoleApi(id, data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result as any
}

export async function deleteRole(id: string) {
  const authHeaders = await getAuthHeaders()
  const result = await deletePersonnelRoleApi(id, authHeaders)
  revalidatePath('/equipment/personnel')
  return result as any
}

// ── 人员 Actions ──

export async function addPersonnel(data: AddPersonnelInput) {
  const authHeaders = await getAuthHeaders()
  const result = await addPersonnelApi(data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result as any
}

export async function deletePersonnel(id: string) {
  const authHeaders = await getAuthHeaders()
  const result = await deletePersonnelApi(id, authHeaders)
  revalidatePath('/equipment/personnel')
  return result as any
}

export async function assignRoles(
  personnelId: string, data: AssignRolesInput,
) {
  const authHeaders = await getAuthHeaders()
  const result = await assignRolesApi(personnelId, data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result as any
}

export async function assignCategories(
  personnelId: string, data: AssignCategoriesInput,
) {
  const authHeaders = await getAuthHeaders()
  const result = await assignCategoriesApi(personnelId, data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result as any
}

export async function refreshFeishu() {
  const authHeaders = await getAuthHeaders()
  const result = await refreshFeishuApi(authHeaders)
  revalidatePath('/equipment/personnel')
  return result as any
}