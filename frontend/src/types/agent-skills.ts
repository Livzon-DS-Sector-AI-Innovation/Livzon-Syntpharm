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
