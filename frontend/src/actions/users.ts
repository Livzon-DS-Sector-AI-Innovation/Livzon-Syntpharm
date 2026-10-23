'use server'

import { cookies } from 'next/headers'
import { revalidatePath } from 'next/cache'
import { unwrapResponse } from '@/lib/api/server/base'
import { normalizeUserBatchStatus } from '@/lib/api/batch'
import {
  getUsers as getUsersServer,
  createUser as createUserServer,
  updateUser as updateUserServer,
  deleteUser as deleteUserServer,
  batchUpdateUserStatus as batchUpdateUserStatusServer,
  resetUserPassword as resetUserPasswordServer,
  changeMyPassword as changeMyPasswordServer,
  unbindFeishuUser as unbindFeishuUserServer,
  revokeUserSessions as revokeUserSessionsServer,
  listSessions as listSessionsServer,
  revokeSession as revokeSessionServer,
} from '@/lib/api/server/users'
import type {
  UserManagementItem,
  UserManagementListResponse,
  LocalUserCreate,
  UserCreateResult,
  UserManagementUpdate,
  PasswordResetRequest,
  PasswordResetResult,
  UserBatchStatusRequest,
  UserBatchStatusResult,
  ChangePasswordRequest,
  UserDeleteResult,
  UserSession,
  UserUnbindResult,
} from '@/types/users'

async function getAuthToken(): Promise<string | undefined> {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

/**
 * 写操作统一返回结果对象，业务错误（如「用户名已存在」）不抛异常。
 * 原因：Server Action 抛错会让整个 RSC 请求返回 500，客户端只能拿到
 * 脱敏后的通用错误（dev 下还会弹出错误遮罩），用户看不到真实原因。
 * 不 export：`'use server'` 文件只允许导出异步函数。
 */
type UsersActionResult<T> = { ok: true; data: T } | { ok: false; message: string }

export async function getUsers(params?: {
  keyword?: string
  role?: 'admin' | 'user'
  status?: 'active' | 'disabled'
  auth_source?: 'local' | 'feishu'
  unbound_only?: boolean
  must_change_password?: boolean
}): Promise<UserManagementListResponse> {
  const token = await getAuthToken()
  const data = unwrapResponse(await getUsersServer(params, token))
  return data ?? { items: [], total: 0 }
}

export async function createUser(data: LocalUserCreate): Promise<UsersActionResult<UserCreateResult>> {
  const token = await getAuthToken()
  try {
    const created = unwrapResponse(await createUserServer(data, token))
    revalidatePath('/settings/users')
    return { ok: true, data: created }
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
    const updated = unwrapResponse(await updateUserServer(id, data, token))
    revalidatePath('/settings/users')
    return { ok: true, data: updated }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '更新用户失败' }
  }
}

/** 批量启用 / 禁用账号：逐条汇总成功与失败原因。 */
export async function batchUpdateUserStatus(
  data: UserBatchStatusRequest,
): Promise<UsersActionResult<UserBatchStatusResult>> {
  const token = await getAuthToken()
  try {
    const result = normalizeUserBatchStatus(unwrapResponse(await batchUpdateUserStatusServer(data, token)))
    revalidatePath('/settings/users')
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '批量操作失败' }
  }
}

/** 删除账号：软删除 + 清空授权 + 吊销会话（后端限定仅超级管理员）。 */
export async function deleteUser(id: string): Promise<UsersActionResult<UserDeleteResult>> {
  const token = await getAuthToken()
  try {
    const result = unwrapResponse(await deleteUserServer(id, token))
    revalidatePath('/settings/users')
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '删除用户失败' }
  }
}

/**
 * 重置用户密码；`data.password` 留空表示随机生成。
 * 随机生成的明文密码只在本次响应里返回一次（后端不落库），调用方必须当场展示。
 */
export async function resetUserPassword(
  id: string,
  data: PasswordResetRequest,
): Promise<UsersActionResult<PasswordResetResult>> {
  const token = await getAuthToken()
  try {
    const result = unwrapResponse(await resetUserPasswordServer(id, data, token))
    revalidatePath('/settings/users')
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '重置密码失败' }
  }
}

/** 当前登录用户自助改密（被标记「首登强制改密」的用户必须走这里）。 */
export async function changeMyPassword(
  data: ChangePasswordRequest,
): Promise<UsersActionResult<{ message: string }>> {
  const token = await getAuthToken()
  try {
    const result = unwrapResponse(await changeMyPasswordServer(data, token))
    // 清掉客户端路由缓存：改密会解除「首登强制改密」，导航与守卫都要按新状态重算
    revalidatePath('/', 'layout')
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '修改密码失败' }
  }
}

export async function unbindFeishuUser(id: string): Promise<UsersActionResult<UserUnbindResult>> {
  const token = await getAuthToken()
  try {
    const result = unwrapResponse(await unbindFeishuUserServer(id, token))
    revalidatePath('/settings/users')
    return { ok: true, data: result }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '解绑飞书账号失败' }
  }
}

/** 吊销某用户的全部在线会话（强制下线）。 */
export async function revokeUserSessions(
  id: string,
): Promise<UsersActionResult<{ revoked: number }>> {
  const token = await getAuthToken()
  try {
    const result = unwrapResponse(await revokeUserSessionsServer(id, token))
    // 后端两个吊销接口共用 SessionRevokeData（revoked: bool | int），这里按语义收窄成条数
    const revoked = typeof result.revoked === 'number' ? result.revoked : result.revoked ? 1 : 0
    return { ok: true, data: { revoked } }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '强制下线失败' }
  }
}

/** 拉取全部在线会话（前端按 user_id 过滤到具体用户）。 */
export async function listSessions(): Promise<UserSession[]> {
  const token = await getAuthToken()
  const data = unwrapResponse(await listSessionsServer(token))
  return data ?? []
}

/** 吊销单个在线会话（踢下线）。 */
export async function revokeSession(jti: string): Promise<UsersActionResult<{ revoked: boolean }>> {
  const token = await getAuthToken()
  try {
    const result = unwrapResponse(await revokeSessionServer(jti, token))
    return { ok: true, data: { revoked: Boolean(result.revoked) } }
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : '踢下线失败' }
  }
}
