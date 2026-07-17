'use client'

import { StageModuleLayout } from './StageModuleLayout'
import { ProcessOptimizationPageAdapter } from './process-optimization/ProcessOptimizationPageAdapter'

export function ProcessOptimizationModulePage() {
  return (
    <StageModuleLayout
      title="工艺优化"
      description="DOE实验设计、杂质研究、晶型研究、质量标准、公斤级放大"
      stage="optimization"
    >
      {(projectId) => <ProcessOptimizationPageAdapter projectId={projectId} />}
    </StageModuleLayout>
  )
}
