'use client'

import { StageModuleLayout } from './StageModuleLayout'
import { RegistrationFilingPage } from './RegistrationFilingPage'

export function RegistrationFilingModulePage() {
  return (
    <StageModuleLayout
      title="申报资料"
      description="管理 CTD 文档结构、申报进度、补充资料"
      stage="filing"
    >
      {(projectId) => <RegistrationFilingPage projectId={projectId} />}
    </StageModuleLayout>
  )
}
