'use server'

import { cookies, headers } from 'next/headers'
import { redirect } from 'next/navigation'
import { revalidatePath } from 'next/cache'
import type { User, ImpersonationStatusExtended } from '@/types/user'
import {
  loginApi,
  getCurrentUserApi,
  startImpersonateApi,
  getImpersonationStatusApi,
} from '@/lib/api/server/auth'
import { resolveLandingPath } from '@/lib/permissions/server'

export interface LoginActionState {
  error?: string
}

function getErrorMessage(value: unknown): string {
  if (!value || typeof value !== 'object') return '登录失败，请重试'
  const payload = value as { message?: string; detail?: string }
  return payload.detail || payload.message || '登录失败，请重试'
}

/**
 * 当前请求是否走 HTTPS。
 * 不能只看 NODE_ENV：UAT/生产镜像固定 NODE_ENV=production，但入口 nginx 是 HTTP，
 * 若给 cookie 打 Secure 标记，浏览器会直接丢弃，表现为「登录后仍提示未登录」。
 */
async function isHttpsRequest(): Promise<boolean> {
  const headersList = await headers()
  const proto = (headersList.get('x-forwarded-proto') || 'http').split(',')[0].trim()
  return proto === 'https'
}

export async function getCurrentUser(): Promise<User | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')
  if (!token?.value) return null
  return getCurrentUserApi(token.value)
}

export async function loginWithPassword(
  _prevState: LoginActionState,
  formData: FormData
): Promise<LoginActionState> {
  const username = String(formData.get('username') || '').trim()
  const password = String(formData.get('password') || '')

  if (!username || !password) {
    return { error: '请输入用户名和密码' }
  }

  try {
    const { response, json } = await loginApi({ username, password })

    if (!response.ok) {
      return { error: getErrorMessage(json) }
    }

    const token = json?.data?.access_token
    if (!token) {
      return { error: '登录响应缺少 token，请检查后端接口' }
    }

    const cookieStore = await cookies()
    cookieStore.set('auth_token', token, {
      httpOnly: true,
      secure: await isHttpsRequest(),
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7,
    })
  } catch (error) {
    return {
      error:
        error instanceof Error
          ? error.message
          : '网络异常，请稍后重试',
    }
  }

  // 失效整棵 layout 树（不只是 `/`）：切换账号后 dashboard layout / 导航 / 权限
  // 都必须按新 cookie 重新渲染，否则会复用上一个账号的 RSC 结果。
  revalidatePath('/', 'layout')
  // 落地页 = 第一个「可见」模块（未接入权限控制的模块恒可见，见 lib/permissions/modules.ts）
  const landingPath = await resolveLandingPath()
  redirect(landingPath)
}

export async function logout() {
  const cookieStore = await cookies()
  cookieStore.delete('auth_token')
  // 整棵 layout 失效：否则退出后仍可能命中带旧账号数据的 RSC 缓存
  revalidatePath('/', 'layout')
  redirect('/login')
}

export async function startImpersonate(targetUserId: string): Promise<void> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')
  if (!token?.value) throw new Error('未登录')

  const impersonateToken = await startImpersonateApi(token.value, targetUserId)

  cookieStore.set('impersonate_token', impersonateToken, {
    httpOnly: true,
    secure: await isHttpsRequest(),
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 2,
  })
}

export async function stopImpersonate(): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.delete('impersonate_token')
}

export async function getImpersonationStatusExtended(): Promise<ImpersonationStatusExtended> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')
  const impCookie = cookieStore.get('impersonate_token')
  if (!token?.value) {
    return { is_impersonating: false, real_user: undefined, target_user: undefined, expires_at: undefined }
  }
  return getImpersonationStatusApi(token.value, impCookie?.value)
}
