'use client'

/**
 * 研发项目知识库页面（独立路由 `/research/knowledge-bases`）。
 *
 * 默认展示「全部项目知识库」总览，顶部项目下拉作为过滤器：
 * - 未选项目：KnowledgeBaseOverview 一览各项目知识库状态，点行即切到该项目
 * - 选中项目：KnowledgeBaseManager 管理该项目的资料（与新建报告弹窗内的弹窗版共用）
 */
import { useQuery } from '@tanstack/react-query'
import { Button, Card, Select, Space, Tooltip } from 'antd'
import { RollbackOutlined } from '@ant-design/icons'
import { fetchRdProjects } from '@/lib/api/client/research/rd-project'
import type { RdProject } from '@/types/research/rd-project'
import { KnowledgeBaseManager } from './KnowledgeBaseManager'
import { KnowledgeBaseOverview } from './KnowledgeBaseOverview'
import { ALL_PROJECTS_VALUE, useProjectFilter } from './useProjectFilter'
import { ModuleGuide } from './ModuleGuide'
import { useSmartBack } from './useSmartBack'
import { KB_COPY } from '@/lib/ui/research-copy'

const STORAGE_KEY = 'research:knowledge-bases:projectId'

interface Props {
  /** 从项目详情页跳转过来时带的项目 id，直接定位到该项目 */
  initialProjectId?: string
  /** true 表示入口是「研发项目详情 → 知识库 tab」，页面顶部给出返回项目详情的入口 */
  fromProjectDetail?: boolean
}

export function KnowledgeBasePage({
  initialProjectId = '',
  fromProjectDetail = false,
}: Props) {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['rd-projects', 'options'],
    queryFn: async () => {
      const result = await fetchRdProjects({ page_size: 100 })
      return (result.items ?? []) as RdProject[]
    },
    staleTime: 5 * 60_000,
  })

  const basePath = fromProjectDetail
    ? '/research/knowledge-bases?from=project-detail'
    : '/research/knowledge-bases'

  const { projectId, selectProject } = useProjectFilter({
    basePath,
    storageKey: STORAGE_KEY,
    initialProjectId,
    projectCount: projects.length,
    soleProjectId: projects[0]?.id,
  })

  // 回项目详情：优先按来源签名回到原页签，无来源时落回知识库页签
  const smartBack = useSmartBack({
    fallbackHref: `/research/projects/${projectId}?tab=knowledge-base`,
    fallbackLabel: '项目详情',
  })

  const options = [
    { value: ALL_PROJECTS_VALUE, label: '全部项目（知识库总览）' },
    ...projects.map((p) => ({ value: p.id, label: `${p.name} (${p.api_name})` })),
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>{KB_COPY.title}</h1>
          <p style={{ color: '#666', margin: '4px 0 0 0' }}>{KB_COPY.subtitle}</p>
        </div>
        {fromProjectDetail && projectId ? (
          <Space>
            <Tooltip title={smartBack.hint}>
              <Button icon={<RollbackOutlined />} onClick={smartBack.back}>
                {smartBack.label}
              </Button>
            </Tooltip>
          </Space>
        ) : null}
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
            {projectId ? '正在管理这个项目的知识库' : '下面汇总了所有项目的情况，选中某个项目可以上传和管理资料'}
          </span>
        </div>
      </Card>

      <ModuleGuide title={KB_COPY.guideTitle} steps={KB_COPY.guideSteps} compact={Boolean(projectId)} />

      {projectId ? (
        <KnowledgeBaseManager projectId={projectId} variant="page" />
      ) : (
        <KnowledgeBaseOverview onSelectProject={selectProject} />
      )}
    </div>
  )
}