import type { components } from '@/types/generated/schema'

export interface AIWorkflowConfig {
  id: string
  module_code: string
  workflow_name: string
  workflow_description: string
  trigger_event: string
  is_enabled: boolean
  script_configs: WorkflowStepItem[]
  sort_order: number
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface WorkflowStepItem {
  name: string
  is_enabled: boolean
  input_info: string
  work_rules: string
  reference_docs: ReferenceDocsValue | string
  output_format: string
  expected_keys?: string[]
  prompt_template?: string
}

export interface ReferenceDocsValue {
  text: string
  attachments: string[]
}

export const TRIGGER_EVENT_OPTIONS = [
  { value: 'submit', label: '提交时触发' },
  { value: 'approve', label: '审批时触发' },
  { value: 'reject', label: '驳回时触发' },
  { value: 'complete', label: '完成时触发' },
  { value: 'delete', label: '删除时触发' },
  { value: 'manual', label: '手动触发' },
  { value: 'scheduled', label: '定时触发' },
]

export const WORKFLOW_MENU_MAP: Record<string, { group: string; subgroup: string }> = {
  hazard: { group: '隐患管理', subgroup: '隐患识别' },
  hazard_rectification: { group: '隐患管理', subgroup: '整改管理' },
  hazard_verification: { group: '隐患管理', subgroup: '验收管理' },
  accident: { group: '事故管理', subgroup: '事故处理' },
  check: { group: '安全检查', subgroup: '检查流程' },
  regulation: { group: '法规管理', subgroup: '法规识别' },
  knowledge: { group: '知识管理', subgroup: '知识处理' },
  training: { group: '培训管理', subgroup: '培训流程' },
  contractor: { group: '承包商', subgroup: '承包商管理' },
  special_ops: { group: '特殊作业', subgroup: '作业审批' },
  ehs_change: { group: '变更管理', subgroup: 'MOC流程' },
  oh_monitor: { group: '职业健康', subgroup: '危害监测' },
  oh_exam: { group: '职业健康', subgroup: '体检管理' },
}

export const WORKFLOW_ICONS: Record<string, string> = {
  hazard: '⚠️',
  hazard_rectification: '🛠️',
  hazard_verification: '✅',
  accident: '💥',
  check: '🔍',
  regulation: '📋',
  knowledge: '📚',
  training: '🎓',
  contractor: '🏗️',
  special_ops: '🔥',
  ehs_change: '🔄',
  oh_monitor: '🔬',
  oh_exam: '🏥',
}
