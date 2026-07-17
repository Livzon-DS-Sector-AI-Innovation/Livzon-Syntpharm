import { ProjectDetailPage } from '@/components/research'
import { fetchRdProject } from '@/lib/api/server/research/rd-project'

export const dynamic = 'force-dynamic'

export default async function RdProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  let project = null
  try {
    project = await fetchRdProject(id)
  } catch (error) {
    console.warn('项目加载失败:', error)
  }

  if (!project) {
    return <div className="p-6">项目不存在</div>
  }

  return <ProjectDetailPage project={project} />
}
