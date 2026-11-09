'use client'

/**
 * 研发报告模块外壳。
 *
 * 不再要求「先选项目」：默认进入即展示全部项目的报告，顶部项目下拉作为过滤器；
 * 选择结果通过 URL（刷新/分享不丢）与 localStorage（下次进来记住）保留。
 */
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { Card, Empty, Select } from 'antd'
import { fetchRdProjects } from '@/lib/api/client/research/rd-project'
import type { RdProject } from '@/types/research/rd-project'
import { ReportPage } from './ReportPage'
import { ReportProjectOverview } from './ReportProjectOverview'
import { ALL_PROJECTS_VALUE, useProjectFilter } from './useProjectFilter'
import { ModuleGuide } from './ModuleGuide'
import { REPORT_COPY } from '@/lib/ui/research-copy'

const BASE_PATH = '/research/reports'
const STORAGE_KEY = 'research:reports:projectId'

interface Props {
  /** 从 URL `?projectId=` 带入的项目 id */
  initialProjectId?: string
}

export function ReportModulePage({ initialProjectId = '' }: Props) {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['rd-projects', 'options'],
    queryFn: async () => {
      const result = await fetchRdProjects({ page_size: 100 })
      return (result.items ?? []) as RdProject[]
    },
    staleTime: 5 * 60_000,
  })

  const { projectId, selectProject } = useProjectFilter({
    basePath: BASE_PATH,
    storageKey: STORAGE_KEY,
    initialProjectId,
    projectCount: projects.length,
    soleProjectId: projects[0]?.id,
  })

  const options = [
    { value: ALL_PROJECTS_VALUE, label: '全部项目（跨项目汇总）' },
    ...projects.map((p) => ({ value: p.id, label: `${p.name} (${p.api_name})` })),
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>{REPORT_COPY.title}</h1>
        <p style={{ color: '#666', margin: '4px 0 0 0' }}>{REPORT_COPY.subtitle}</p>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <span>选择项目：</span>
          <Select
            style={{ minWidth: 320 }}
            loading={isLoading}
            value={projectId || ALL_PROJECTS_VALUE}
            onChange={selectProject}
            options={options}
            showSearch
            optionFilterProp="label"
          />
          <span style={{ color: '#999' }}>
            {projectId ? '只看这个项目的报告' : '下面按项目汇总，点某个项目可以看它的全部报告'}
          </span>
        </div>
      </Card>

      <ModuleGuide
        title={REPORT_COPY.guideTitle}
        steps={REPORT_COPY.guideSteps}
        compact={Boolean(projectId)}
      />

      {!isLoading && projects.length === 0 ? (
        <Card>
          <Empty
            description={
              <span>
                还没有研发项目。报告要挂在项目下，先
                <Link href="/research/projects"> 创建研发项目</Link>
                ，再回来生成报告
              </span>
            }
          />
        </Card>
      ) : projectId ? (
        <ReportPage projectId={projectId} />
      ) : (
        /* 未选项目即「全部项目」：先按项目汇总，点进去才看报告明细 */
        <ReportProjectOverview onSelectProject={selectProject} />
      )}
    </div>
  )
}