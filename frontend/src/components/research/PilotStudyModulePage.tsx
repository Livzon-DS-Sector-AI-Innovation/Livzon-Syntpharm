'use client'

import { StageModuleLayout } from './StageModuleLayout'
import { PilotStudyPage } from './PilotStudyPage'

export function PilotStudyModulePage() {
  return (
    <StageModuleLayout
      title="中试研究"
      description="管理放大效应、物料衡算、设备选型、工程计算、EHS 评估"
      stage="pilot"
    >
      {(projectId) => <PilotStudyPage projectId={projectId} />}
    </StageModuleLayout>
  )
}
