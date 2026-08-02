import type {
  AgentSkill,
  AgentSkillPayload,
  AgentSkillUpdatePayload,
} from '@/actions/agent-skills'

export function getApiBaseUrl(): string {
  return process.env.API_BASE_URL || 'http://dazah-backend-app-1:8000'
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    cache: 'no-store',
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.message || `请求失败 (${response.status})`)
  }
  return payload.data as T
}

export async function getAgentSkills(authToken: string | undefined) {
  return apiFetch<AgentSkill[]>('/api/v1/agent/skills', {
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function createAgentSkill(authToken: string | undefined, payload: AgentSkillPayload) {
  return apiFetch<AgentSkill>('/api/v1/agent/skills', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function updateAgentSkill(authToken: string | undefined, id: string, payload: AgentSkillUpdatePayload) {
  return apiFetch<AgentSkill>(`/api/v1/agent/skills/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function enableAgentSkill(authToken: string | undefined, id: string) {
  return apiFetch<AgentSkill>(`/api/v1/agent/skills/${id}/enable`, {
    method: 'POST',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function disableAgentSkill(authToken: string | undefined, id: string) {
  return apiFetch<AgentSkill>(`/api/v1/agent/skills/${id}/disable`, {
    method: 'POST',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}

export async function deleteAgentSkill(authToken: string | undefined, id: string) {
  return apiFetch<{ ok: boolean }>(`/api/v1/agent/skills/${id}`, {
    method: 'DELETE',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })
}
