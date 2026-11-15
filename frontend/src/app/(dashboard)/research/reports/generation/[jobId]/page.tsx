import { ReportGenDetail } from '@/components/research'
import { fetchReportGenJobServer } from '@/lib/api/server/research/report-gen'
import type { ReportGenJob } from '@/types/research/report-gen'

export const dynamic = 'force-dynamic'

/** AI 报告执行过程详情页：首屏服务端取任务快照，后续由客户端轮询增量。 */
export default async function ReportGenerationDetailPage({
  params,
}: {
  params: Promise<{ jobId: string }>
}) {
  const { jobId } = await params
  let job: ReportGenJob | null = null
  try {
    job = await fetchReportGenJobServer(jobId)
  } catch (error) {
    console.warn('生成任务详情加载失败:', error)
  }

  return <ReportGenDetail jobId={jobId} initialJob={job} />
}