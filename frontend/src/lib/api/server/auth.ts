import type { User, ImpersonationStatusExtended } from '@/types/user'
import type { LoginResponse } from '@/types/auth'
import { getApiBaseUrl } from './base'

function getApiBaseCandidates() {
  return Array.from(
    new Set([
      getApiBaseUrl(),
      'http://app:8000',
      'http://backend:8000',
      'http://dazah-backend:8000',
      'http://dazah-backend-app:8000',
      'http://dazah-backend-app-1:8000',
      'http://host.docker.internal:8000',
    ])
  )
}

export async function loginApi(body: { username: string; password: string }): Promise<{ response: Response; json: LoginResponse | null }> {
  let lastError: unknown
  const attemptedUrls: string[] = []
  for (const baseUrl of getApiBaseCandidates()) {
    const url = `${baseUrl}/api/v1/identity/auth/local/login`
    attemptedUrls.push(url)
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        cache: 'no-store',
      })
      return { response, json: await response.json().catch(() => null) }
    } catch (error) {
      lastError = error
    }
  }

  const cause =
    lastError instanceof Error ? lastError.message : 'unknown network error'
  throw new Error(
    `无法连接后端服务，已尝试：${attemptedUrls.join('、')}。最后错误：${cause}`
  )
}

export async function getCurrentUserApi(authToken: string): Promise<User | null> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/identity/me`, {
      headers: { Authorization: `Bearer ${authToken}` },
      cache: 'no-store',
    })
    if (!res.ok) return null
    const json = await res.json()
    return json.data ?? null
  } catch {
    return null
  }
}

export async function startImpersonateApi(authToken: string, targetUserId: string): Promise<string> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/identity/impersonate/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ target_user_id: targetUserId }),
    cache: 'no-store',
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.message || `开始代理失败 (${res.status})`)
  }

  const body = await res.json()
  const data = body.data
  if (!data?.token) throw new Error('服务端未返回代理 token')
  return data.token
}

export async function getImpersonationStatusApi(
  authToken: string,
  impersonateToken?: string,
): Promise<ImpersonationStatusExtended> {
  const NO_IMPERSONATION: ImpersonationStatusExtended = {
    is_impersonating: false,
    real_user: undefined,
    target_user: undefined,
    expires_at: undefined,
  }

  try {
    const headers: Record<string, string> = { Authorization: `Bearer ${authToken}` }
    if (impersonateToken) {
      headers['Cookie'] = `impersonate_token=${impersonateToken}`
    }
    const res = await fetch(`${getApiBaseUrl()}/api/v1/identity/impersonate/status`, {
      headers,
      cache: 'no-store',
    })
    if (!res.ok) return NO_IMPERSONATION
    const body = await res.json()
    return body.data as ImpersonationStatusExtended
  } catch {
    return NO_IMPERSONATION
  }
}
