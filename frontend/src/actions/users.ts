'use server'

import { cookies } from 'next/headers'
import { revalidatePath } from 'next/cache'
import {
  getUsers as getUsersServer,
  createUser as createUserServer,
  updateUser as updateUserServer,
  resetUserPassword as resetUserPasswordServer,
} from '@/lib/api/server/users'
import type {
  UserManagementItem,
  UserManagementListResponse,
  LocalUserCreate,
  UserManagementUpdate,
  PasswordResetRequest,
} from '@/types/users'

async function getAuthToken(): Promise<string | undefined> {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

export async function getUsers(params?: {
  keyword?: string
  role?: 'admin' | 'user'
  status?: 'active' | 'disabled'
}) {
  const token = await getAuthToken()
  return getUsersServer(params, token) as Promise<UserManagementListResponse>
}

export async function createUser(data: LocalUserCreate) {
  const token = await getAuthToken()
  const result = await createUserServer(data, token) as UserManagementItem
  revalidatePath('/settings')
  return result
}

export async function updateUser(id: string, data: UserManagementUpdate) {
  const token = await getAuthToken()
  const result = await updateUserServer(id, data, token) as UserManagementItem
  revalidatePath('/settings')
  return result
}

export async function resetUserPassword(id: string, data: PasswordResetRequest) {
  const token = await getAuthToken()
  const result = await resetUserPasswordServer(id, data, token) as { message: string }
  revalidatePath('/settings')
  return result
}