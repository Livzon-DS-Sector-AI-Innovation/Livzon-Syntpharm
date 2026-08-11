import { ProcessOptimizationPage } from '@/components/research/process-optimization'
import { fetchOptimizations } from '@/lib/api/server/research/process-optimization'

export const dynamic = 'force-dynamic'

export default async function ProcessOptimizationPageWrapper() {
  let initialOptimizations = []
  let initialTotal = 0
  
  try {
    const result = await fetchOptimizations({ page: 1, page_size: 10 })
    initialOptimizations = result.items || []
    initialTotal = result.total || 0
  } catch (error) {
    console.warn('Failed to fetch optimizations:', error)
  }
  
  return (
    <>
      <h1 className="text-2xl font-semibold text-gray-800 mb-4">工艺优化</h1>
      <ProcessOptimizationPage
        initialOptimizations={initialOptimizations}
        initialTotal={initialTotal}
      />
    </>
  )
}
