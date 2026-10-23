import { KnowledgeBasePage } from '@/components/research'

/**
 * 项目知识库页面。
 *
 * 支持带参跳转，用于「上传资料到知识库 → 返回原处」的往返：
 * - 从新建报告页来：`?projectId=<id>&from=report-new`（顶部给「返回新建报告」）
 * - 从研发项目详情来：`?projectId=<id>&from=project-detail`（顶部给「返回项目详情」）
 * 数据由客户端组件按项目加载。
 */
export default async function ResearchKnowledgeBasesPage({
  searchParams,
}: {
  searchParams: Promise<{ projectId?: string; from?: string }>
}) {
  const params = await searchParams
  const from = params.from
  return (
    <KnowledgeBasePage
      initialProjectId={params.projectId ?? ''}
      fromReport={from === 'report-new'}
      fromProjectDetail={from === 'project-detail'}
    />
  )
}
