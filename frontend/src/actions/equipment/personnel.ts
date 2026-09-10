'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import type {
  CreateRoleInput, UpdateRoleInput, AddPersonnelInput,
  AssignRolesInput, AssignCategoriesInput,
} from '@/types/equipment/generated-bridge'
import {
  createPersonnelRoleApiTyped,
  updatePersonnelRoleApiTyped,
  deletePersonnelRoleApi,
  addPersonnelApiTyped,
  deletePersonnelApi,
  assignRolesApiTyped,
  assignCategoriesApiTyped,
  refreshFeishuApi,
} from '@/lib/api/server/equipment'

async function wrapApiCall<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn()
  } catch {
    return null
  }
}

// ── 角色 Actions ──

export async function createRole(data: CreateRoleInput) {
  const authHeaders = await getAuthHeaders()
  const result = await createPersonnelRoleApiTyped(data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result
}

export async function updateRole(id: string, data: UpdateRoleInput) {
  const authHeaders = await getAuthHeaders()
  const result = await updatePersonnelRoleApiTyped(id, data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result
}

export async function deleteRole(id: string) {
  const authHeaders = await getAuthHeaders()
  const result = await deletePersonnelRoleApi(id, authHeaders)
  revalidatePath('/equipment/personnel')
  return result
}

// ── 人员 Actions ──

export async function addPersonnel(data: AddPersonnelInput) {
  const authHeaders = await getAuthHeaders()
  const result = await addPersonnelApiTyped(data as any, authHeaders)
  revalidatePath('/equipment/personnel')
  return result
}

export async function deletePersonnel(id: string) {
  const authHeaders = await getAuthHeaders()
  const result = await deletePersonnelApi(id, authHeaders)
  revalidatePath('/equipment/personnel')
  return result
}

export async function assignRoles(
  personnelId: string, data: AssignRolesInput,
) {
  const authHeaders = await getAuthHeaders()
  const result = await assignRolesApiTyped(personnelId, data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result
}

export async function assignCategories(
  personnelId: string, data: AssignCategoriesInput,
) {
  const authHeaders = await getAuthHeaders()
  const result = await assignCategoriesApiTyped(personnelId, data, authHeaders)
  revalidatePath('/equipment/personnel')
  return result
}

export async function refreshFeishu() {
  const authHeaders = await getAuthHeaders()
  const result = await refreshFeishuApi(authHeaders)
  revalidatePath('/equipment/personnel')
  return result
}