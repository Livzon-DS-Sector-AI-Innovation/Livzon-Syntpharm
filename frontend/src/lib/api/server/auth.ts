import type { User, ImpersonationStatusExtended } from '@/types/user'
import type { LoginResponse } from '@/types/auth'
import type { components } from '@/types/generated/schema'
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

/**
 * 飞书网页应用免登：把 H5 JSSDK 取到的预授权码交给后端换 token。
 *
 * 用原始 fetch（与 loginApi 同理）：登录前没有 token，且需要区分 HTTP 状态码与业务错误。
 * 契约类型直接取生成的 OpenAPI schema，避免手写类型与后端漂移。
 */
export async function h5LoginApi(
  code: string,
): Promise<{ response: Response; json: components['schemas']['FeishuH5LoginApiResponse'] | null }> {
  const url = `${getApiBaseUrl()}/api/v1/identity/auth/h5/login`
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
    cache: 'no-store',
  })
  return { response, json: await response.json().catch(() => null) }
}

/**
 * 飞书网页应用免登配置（公开接口）。
 *
 * 登录页在服务端取，客户端不再用 useEffect 取数；取不到时按「未启用」处理，
 * 面板自然退回 OAuth 授权按钮。
 */
export async function getFeishuH5ConfigApi(): Promise<components['schemas']['FeishuH5ConfigData']> {
  try {
    const res = await apiFetch<components['schemas']['FeishuH5ConfigApiResponse']>(
      '/api/v1/identity/auth/h5/config',
    )
    return res.data
  } catch {
    return { enabled: false, app_id: '' }
  }
}
