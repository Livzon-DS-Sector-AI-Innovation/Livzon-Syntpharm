'use client'

import { StageModuleLayout } from './StageModuleLayout'
import { ProcessValidationPage } from './ProcessValidationPage'

export function ProcessValidationModulePage() {
  return (
    <StageModuleLayout
      title="工艺验证"
      description="管理验证方案、验证批次、统计分析、验证结论"
      stage="validation"
    >
      {(projectId) => <ProcessValidationPage projectId={projectId} />}
    </StageModuleLayout>
  )
}
