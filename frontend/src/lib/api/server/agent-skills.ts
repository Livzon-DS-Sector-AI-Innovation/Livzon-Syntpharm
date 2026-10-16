/**
 * Livzon Skill 接口封装（**待后端接入**）。
 *
 * 后端 agent 模块已于迁移 `0035_drop_agent_tables`（2026-07-14）下线，
 * `/api/v1/agent/skills` 已不存在 —— 现在调用这里必然 404。
 * 入口已在系统设置页置灰，后端恢复后再放开。
 */
import type {
  AgentSkill,
  AgentSkillPayload,
  AgentSkillUpdatePayload,
} from '@/types/agent-skills'
import { apiFetch, unwrapResponse } from './base'

export async function getAgentSkills(authToken: string | undefined) {
  return unwrapResponse(await apiFetch<{ code: number; data: AgentSkill[]; message?: string; meta?: unknown }>('/api/v1/agent/skills', {
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  }))
}

export async function createAgentSkill(authToken: string | undefined, payload: AgentSkillPayload) {
  return unwrapResponse(await apiFetch<{ code: number; data: AgentSkill; message?: string; meta?: unknown }>('/api/v1/agent/skills', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  }))
}

export async function updateAgentSkill(authToken: string | undefined, id: string, payload: AgentSkillUpdatePayload) {
  return unwrapResponse(await apiFetch<{ code: number; data: AgentSkill; message?: string; meta?: unknown }>(`/api/v1/agent/skills/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  }))
}

export async function enableAgentSkill(authToken: string | undefined, id: string) {
  return unwrapResponse(await apiFetch<{ code: number; data: AgentSkill; message?: string; meta?: unknown }>(`/api/v1/agent/skills/${id}/enable`, {
    method: 'POST',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  }))
}

export async function disableAgentSkill(authToken: string | undefined, id: string) {
  return unwrapResponse(await apiFetch<{ code: number; data: AgentSkill; message?: string; meta?: unknown }>(`/api/v1/agent/skills/${id}/disable`, {
    method: 'POST',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  }))
}

export async function deleteAgentSkill(authToken: string | undefined, id: string) {
  return unwrapResponse(await apiFetch<{ code: number; data: { ok: boolean }; message?: string; meta?: unknown }>(`/api/v1/agent/skills/${id}`, {
    method: 'DELETE',
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  }))
}