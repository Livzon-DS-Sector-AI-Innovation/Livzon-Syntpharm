import { ProjectListPage } from '@/components/research'
import { fetchRdProjects } from '@/lib/api/server/research/rd-project'

export const dynamic = 'force-dynamic'

export default async function RdProjectsPage() {
  let projects = []
  let total = 0
  try {
    const result = await fetchRdProjects({ page: 1, page_size: 20 })
    projects = result.items
    total = result.total
  } catch (error) {
    console.warn('加载项目列表失败:', error)
  }

  return <ProjectListPage initialProjects={projects} initialTotal={total} />
}
