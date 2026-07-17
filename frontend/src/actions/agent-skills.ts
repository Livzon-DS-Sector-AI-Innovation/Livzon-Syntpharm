'use server'

import { cookies } from 'next/headers'
import {
  getAgentSkills as getAgentSkillsApi,
  createAgentSkill as createAgentSkillApi,
  updateAgentSkill as updateAgentSkillApi,
  enableAgentSkill as enableAgentSkillApi,
  disableAgentSkill as disableAgentSkillApi,
  deleteAgentSkill as deleteAgentSkillApi,
} from '@/lib/api/server/agent-skills'

export interface AgentSkill {
  id: string
  name: string
  title: string
  description: string
  trigger_keywords: string[]
  content: string
  status: string
  is_builtin: boolean
  version: number
  created_at?: string | null
  updated_at?: string | null
}

export interface AgentSkillPayload {
  name: string
  title: string
  description: string
  trigger_keywords: string[]
  content: string
  status?: 'active' | 'disabled'
  is_builtin?: boolean
}

export type AgentSkillUpdatePayload = Partial<Omit<AgentSkillPayload, 'name' | 'is_builtin'>>

async function getAuthToken() {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

export async function getAgentSkills() {
  return getAgentSkillsApi(await getAuthToken())
}

export async function createAgentSkill(payload: AgentSkillPayload) {
  return createAgentSkillApi(await getAuthToken(), payload)
}

export async function updateAgentSkill(id: string, payload: AgentSkillUpdatePayload) {
  return updateAgentSkillApi(await getAuthToken(), id, payload)
}

export async function enableAgentSkill(id: string) {
  return enableAgentSkillApi(await getAuthToken(), id)
}

export async function disableAgentSkill(id: string) {
  return disableAgentSkillApi(await getAuthToken(), id)
}

export async function deleteAgentSkill(id: string) {
  return deleteAgentSkillApi(await getAuthToken(), id)
}
