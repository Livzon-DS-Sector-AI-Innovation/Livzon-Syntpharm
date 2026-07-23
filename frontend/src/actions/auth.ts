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

export interface LoginActionState {
  error?: string
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

  revalidatePath('/')
  redirect('/production')
}

export async function logout() {
  const cookieStore = await cookies()
  cookieStore.delete('auth_token')
  revalidatePath('/')
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
