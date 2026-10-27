'use server'

import { cookies, headers } from 'next/headers'
import { redirect } from 'next/navigation'
import { revalidatePath } from 'next/cache'
import type { User, ImpersonationStatusExtended } from '@/types/user'
import type { LoginActionState } from '@/types/auth'
import {
  loginApi,
  getCurrentUserApi,
  startImpersonateApi,
  getImpersonationStatusApi,
} from '@/lib/api/server/auth'
import { getApiBaseUrl } from '@/lib/api/server/base'
import { resolveLandingPath } from '@/lib/permissions/server'

/**
 * 解析「会话过期前所在页面」：只接受站内路径，避免被构造成开放重定向
 * （`//host`、`/\host`、`/login` 自身都拒绝）。
 */
function readSafeRedirect(raw: string | undefined): string | null {
  if (!raw) return null
  let target: string
  try {
    target = decodeURIComponent(raw)
  } catch {
    return null
  }
  const isInternal = target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/\\')
  if (!isInternal || target.startsWith('/login')) return null
  return target
}

function getErrorMessage(value: unknown): string {
  if (!value || typeof value !== 'object') return '登录失败，请重试'
  const payload = value as { message?: string; detail?: string }
  return payload.detail || payload.message || '登录失败，请重试'
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
    return { error: '请输入账号和密码' }
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
      secure: process.env.NODE_ENV === 'production',
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

  // 会话过期回跳：客户端收到 401 时把原地址写进 login_redirect（见 lib/api/client.ts），
  // 这里直接送回去。读后即删，避免下次登录又被弹回旧页面。
  const cookieStore = await cookies()
  const redirectTarget = readSafeRedirect(cookieStore.get('login_redirect')?.value)
  if (redirectTarget) {
    cookieStore.delete('login_redirect')
    redirect(redirectTarget)
  }

  // 落地页 = 第一个「可见」模块（未接入权限控制的模块恒可见，见 lib/permissions/modules.ts）
  const landingPath = await resolveLandingPath()
  redirect(landingPath)
}

export async function logout() {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')?.value
  if (token) {
    // 通知后端把该 jti 写入吊销黑名单（否则退出后 token 在剩余有效期内仍可用）。
    // 失败不阻塞登出：清 cookie 才是用户感知的结果。
    try {
      await fetch(`${getApiBaseUrl()}/api/v1/identity/auth/logout`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      })
    } catch {
      // 忽略：后端不可用时仍允许本地登出
    }
  }
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

  const headersList = await headers()
  const proto = headersList.get('x-forwarded-proto') || 'http'
  const isHttps = proto === 'https'
  cookieStore.set('impersonate_token', impersonateToken, {
    httpOnly: true,
    secure: isHttps,
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
