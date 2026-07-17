import { ProcessOptimizationPage } from './ProcessOptimizationPage'

interface Props {
  projectId: string
}

export function ProcessOptimizationPageAdapter({ projectId }: Props) {
  return <ProcessOptimizationPage initialOptimizations={[]} initialTotal={0} projectId={projectId} />
}
