'use server'

import { cookies } from 'next/headers'
import { revalidatePath } from 'next/cache'
import {
  getUsers as getUsersServer,
  createUser as createUserServer,
  updateUser as updateUserServer,
  resetUserPassword as resetUserPasswordServer,
  bindFeishuUser as bindFeishuUserServer,
  unbindFeishuUser as unbindFeishuUserServer,
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

/**
 * 写操作统一返回结果对象，业务错误（如「用户名已存在」）不抛异常。
 * 原因：Server Action 抛错会让整个 RSC 请求返回 500，客户端只能拿到
 * 脱敏后的通用错误（dev 下还会弹出错误遮罩），用户看不到真实原因。
 */
export type UsersActionResult<T> = { ok: true; data: T } | { ok: false; message: string }

export async function getUsers(params?: {
  keyword?: string
  role?: 'admin' | 'user'
  status?: 'active' | 'disabled'
  auth_source?: 'local' | 'feishu'
}): Promise<UserManagementListResponse> {
  const token = await getAuthToken()
  const res = (await getUsersServer(params, token)) as { data: UserManagementListResponse }
  return res.data ?? { items: [], total: 0 }
}

export async function createUser(data: LocalUserCreate): Promise<UsersActionResult<UserManagementItem>> {
  const token = await getAuthToken()
  try {
    const res = (await createUserServer(data, token)) as { data: UserManagementItem }
    revalidatePath('/settings/users')
    return { ok: true, data: res.data }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '创建用户失败' }
  }
}

export async function updateUser(
  id: string,
  data: UserManagementUpdate,
): Promise<UsersActionResult<UserManagementItem>> {
  const token = await getAuthToken()
  try {
    const res = (await updateUserServer(id, data, token)) as { data: UserManagementItem }
    revalidatePath('/settings/users')
    return { ok: true, data: res.data }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '更新用户失败' }
  }
}

export async function resetUserPassword(
  id: string,
  data: PasswordResetRequest,
): Promise<UsersActionResult<{ message: string }>> {
  const token = await getAuthToken()
  try {
    const res = (await resetUserPasswordServer(id, data, token)) as { data: { message: string } }
    revalidatePath('/settings/users')
    return { ok: true, data: res.data }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '重置密码失败' }
  }
}

/** 拉取可绑定的飞书用户（库里已有、且尚未绑定飞书身份的账号）。 */
export async function getFeishuCandidates(
  keyword?: string,
): Promise<UserManagementListResponse> {
  const token = await getAuthToken()
  const res = (await getUsersServer(
    { keyword, auth_source: 'feishu', limit: 100 },
    token,
  )) as { data: UserManagementListResponse }
  return res.data ?? { items: [], total: 0 }
}

export async function bindFeishuUser(
  id: string,
  sourceUserId: string,
): Promise<UsersActionResult<UserManagementItem>> {
  const token = await getAuthToken()
  try {
    const res = (await bindFeishuUserServer(id, { source_user_id: sourceUserId }, token)) as {
      data: UserManagementItem
    }
    revalidatePath('/settings/users')
    return { ok: true, data: res.data }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '绑定飞书账号失败' }
  }
}

export async function unbindFeishuUser(id: string): Promise<UsersActionResult<UserManagementItem>> {
  const token = await getAuthToken()
  try {
    const res = (await unbindFeishuUserServer(id, token)) as { data: UserManagementItem }
    revalidatePath('/settings/users')
    return { ok: true, data: res.data }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '解绑飞书账号失败' }
  }
}
