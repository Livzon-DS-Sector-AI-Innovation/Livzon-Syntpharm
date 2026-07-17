'use client'

import { StageModuleLayout } from './StageModuleLayout'
import { InitiationPage } from './InitiationPage'

export function InitiationModulePage() {
  return (
    <StageModuleLayout
      title="立项管理"
      description="管理研发项目立项申请、评审和批准流程"
      stage="initiation"
    >
      {(projectId) => <InitiationPage projectId={projectId} />}
    </StageModuleLayout>
  )
}
