import type { User, ImpersonationStatusExtended } from '@/types/user'
import type { components } from '@/types/generated/schema'
import { apiFetch, apiFetchRaw, unwrapResponse, getApiBaseUrl } from './base'

export async function loginApi(
  body: components['schemas']['LocalLoginRequest'],
): Promise<{ response: Response; json: components['schemas']['LocalLoginApiResponse'] | null }> {
  const url = `${getApiBaseUrl()}/api/v1/identity/auth/local/login`
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
  return { response, json: await response.json().catch(() => null) }
}

/**
 * 契约数据（`UserResponse`）→ 前端展示用 `User`。
 *
 * 两个类型不是同一个东西：`User` 是 UI/display 类型（见 `types/user.ts` 的说明），
 * 只保留界面要用的字段；`/me` 不返回账号状态，因此不在此处凭空补 `status`。
 */
function toDisplayUser(data: components['schemas']['UserResponse']): User {
  return {
    id: data.id,
    name: data.name,
    username: data.username ?? null,
    auth_source: data.auth_source,
    email: data.email ?? null,
    mobile: data.mobile ?? null,
    avatar_url: data.avatar_url ?? null,
    employee_no: data.employee_no ?? null,
    department: data.department ?? null,
    position: data.position ?? null,
    must_change_password: data.must_change_password,
  }
}

export async function getCurrentUserApi(authToken: string): Promise<User | null> {
  try {
    const data = unwrapResponse(
      await apiFetch<components['schemas']['CurrentUserApiResponse']>('/api/v1/identity/me', {
        headers: { Authorization: `Bearer ${authToken}` },
      }),
    )
    return toDisplayUser(data)
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
    return unwrapResponse(
      await apiFetch<components['schemas']['FeishuH5ConfigApiResponse']>('/api/v1/identity/auth/h5/config'),
    )
  } catch {
    return { enabled: false, app_id: '' }
  }
}

/**
 * 登出：让后端把当前 token 的 jti 写入吊销黑名单（否则退出后 token 在剩余有效期内仍可用）。
 *
 * 后端会 302 到 `/login`，重定向结果无意义，只有「请求是否送达」有意义；
 * 是否阻塞登出由调用方决定（清 cookie 才是用户感知的结果）。
 */
export async function logoutApi(authToken: string): Promise<void> {
  await apiFetchRaw('/api/v1/identity/auth/logout', {
    headers: { Authorization: `Bearer ${authToken}` },
  })
}
