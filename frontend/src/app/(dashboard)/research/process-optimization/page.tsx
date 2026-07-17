import { ProcessOptimizationPage } from '@/components/research/process-optimization'
import { fetchOptimizations } from '@/lib/api/server/research/process-optimization'
import { ProcessOptimization } from '@/types/research'

export const dynamic = 'force-dynamic'

export default async function ProcessOptimizationPageWrapper() {
  const result = await fetchOptimizations({ page: 1, page_size: 10 })
  
  return (
    <ProcessOptimizationPage
      initialOptimizations={result.items || []}
      initialTotal={result.total || 0}
    />
  )
}
