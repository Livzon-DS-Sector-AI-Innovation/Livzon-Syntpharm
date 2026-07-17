'use client'

import { StageModuleLayout } from './StageModuleLayout'
import { RouteDevelopmentPageAdapter } from './route-development/RouteDevelopmentPageAdapter'

export function RouteDevelopmentModulePage() {
  return (
    <StageModuleLayout
      title="打通路线"
      description="工艺路线研究、试验、评估与确认"
      stage="route_dev"
    >
      {(projectId) => <RouteDevelopmentPageAdapter projectId={projectId} />}
    </StageModuleLayout>
  )
}
