import { KnowledgeBasePage } from '@/components/research'

/**
 * 项目知识库页面。
 *
 * 支持带参跳转：从研发项目详情来 `?projectId=<id>&from=project-detail` 时，
 * 页面顶部给出「返回项目详情」入口。
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
      fromProjectDetail={from === 'project-detail'}
    />
  )
}
