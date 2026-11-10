import { ReportModulePage } from '@/components/research'

/**
 * 研发报告列表页。
 *
 * 支持带参直达：`?projectId=<id>` 时直接定位到该项目的报告；
 * 不带参数即「全部项目」汇总视图（项目下拉作为过滤器）。
 */
export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ projectId?: string }>
}) {
  const params = await searchParams
  return <ReportModulePage initialProjectId={params.projectId ?? ''} />
}