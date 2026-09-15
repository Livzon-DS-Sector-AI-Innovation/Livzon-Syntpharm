import { PilotWorkflowList } from '@/components/research/pilot-workflow'
import { fetchPilotWorkflows } from '@/actions/research'
import { PilotWorkflowListResponse } from '@/types/pilot-workflow'

export const dynamic = 'force-dynamic'

export default async function PilotWorkflowListPage() {
  let initialData: PilotWorkflowListResponse = {
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
  }

  try {
    initialData = await fetchPilotWorkflows({ page: 1, page_size: 20 }) as PilotWorkflowListResponse
  } catch (error) {
    console.warn('中试工作流加载失败:', error)
  }

  return <PilotWorkflowList initialData={initialData} />
}
