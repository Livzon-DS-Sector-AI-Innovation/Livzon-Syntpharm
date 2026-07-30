'use server'

import { revalidatePath } from 'next/cache'
import { getServerToken } from '@/lib/auth'
import type {
  CreateRoleInput, UpdateRoleInput, AddPersonnelInput,
  AssignRolesInput, AssignCategoriesInput,
} from '@/types/equipment-personnel'
import {
  createRoleApi, updateRoleApi, deleteRoleApi,
  addPersonnelApi, deletePersonnelApi, assignRolesApi,
  assignCategoriesApi, refreshFeishuApi,
} from '@/lib/api/server/equipment-personnel'

async function authHeaders(): Promise<Record<string, string>> {
  return { Authorization: `Bearer ${await getServerToken()}` }
}

export async function createRole(data: CreateRoleInput) {
  const result = await createRoleApi(data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function updateRole(id: string, data: UpdateRoleInput) {
  const result = await updateRoleApi(id, data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function deleteRole(id: string) {
  const result = await deleteRoleApi(id, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function addPersonnel(data: AddPersonnelInput) {
  const result = await addPersonnelApi(data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function deletePersonnel(id: string) {
  const result = await deletePersonnelApi(id, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function assignRoles(personnelId: string, data: AssignRolesInput) {
  const result = await assignRolesApi(personnelId, data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function assignCategories(personnelId: string, data: AssignCategoriesInput) {
  const result = await assignCategoriesApi(personnelId, data, await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}

export async function refreshFeishu() {
  const result = await refreshFeishuApi(await authHeaders())
  revalidatePath('/equipment/personnel')
  return result
}
