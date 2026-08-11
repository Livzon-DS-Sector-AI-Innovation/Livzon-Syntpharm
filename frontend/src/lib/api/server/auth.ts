import type { User, ImpersonationStatusExtended } from '@/types/user'
import type { LoginResponse } from '@/types/auth'
import { apiFetch, unwrapResponse, getApiBaseUrl } from './base'

export async function loginApi(body: { username: string; password: string }): Promise<{ response: Response; json: LoginResponse | null }> {
  const url = `${getApiBaseUrl()}/api/v1/identity/auth/local/login`
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
  return { response, json: await response.json().catch(() => null) }
}

export async function getCurrentUserApi(authToken: string): Promise<User | null> {
  try {
    return unwrapResponse(await apiFetch<{ code: number; data: User; message?: string; meta?: unknown }>(
      '/api/v1/identity/me',
      { headers: { Authorization: `Bearer ${authToken}` } },
    ))
  } catch {
    return null
  }
}

export async function startImpersonateApi(authToken: string, targetUserId: string): Promise<string> {
  const result = unwrapResponse(await apiFetch<{ code: number; data: { token: string }; message?: string; meta?: unknown }>(
    '/api/v1/identity/impersonate/start',
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${authToken}` },
      body: JSON.stringify({ target_user_id: targetUserId }),
    },
  ))
  if (!result.token) throw new Error('服务端未返回代理 token')
  return result.token
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
    return unwrapResponse(await apiFetch<{ code: number; data: ImpersonationStatusExtended; message?: string; meta?: unknown }>(
      '/api/v1/identity/impersonate/status',
      { headers },
    ))
  } catch {
    return NO_IMPERSONATION
  }
}
