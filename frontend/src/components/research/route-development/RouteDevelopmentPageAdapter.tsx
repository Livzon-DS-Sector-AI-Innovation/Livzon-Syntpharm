import { RouteDevelopmentPage } from './RouteDevelopmentPage'

interface Props {
  projectId: string
}

export function RouteDevelopmentPageAdapter({ projectId }: Props) {
  return <RouteDevelopmentPage initialRoutes={[]} initialTotal={0} projectId={projectId} />
}
