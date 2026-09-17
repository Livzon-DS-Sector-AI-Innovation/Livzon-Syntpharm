// Stub implementation for workflow templates
export interface WorkflowStep {
  num: number
  name: string
  desc: string
  expected_keys: string[]
}

export function getWorkflowStepList(_workflowType: string): WorkflowStep[] {
  // Stub implementation - returns empty array
  return []
}

// Built-in workflows
export const BUILT_IN_WORKFLOWS: Array<{
  module_code: string
  workflow_name: string
  workflow_description?: string
  trigger_event?: string
  script_configs?: any[]
  steps?: WorkflowStep[]
}> = []

// Excluded module codes
export const EXCLUDED_MODULE_CODES: Set<string> = new Set()
