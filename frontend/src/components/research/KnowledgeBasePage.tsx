'use client'

/**
 * 研发项目知识库页面（独立路由 `/research/knowledge-bases`）。
 *
 * 只负责页面级外壳：标题、项目选择、返回新建报告的入口；
 * 具体管理能力全部来自 KnowledgeBaseManager（与新建报告弹窗内的弹窗版共用）。
 */
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { App, Button, Card, Select, Space } from 'antd'
import { RollbackOutlined } from '@ant-design/icons'
import { fetchRdProjects } from '@/lib/api/client/research/rd-project'
import type { RdProject } from '@/types/research/rd-project'
import { KnowledgeBaseManager } from './KnowledgeBaseManager'

interface Props {
  /** 从新建报告页 / 项目详情页跳转过来时带的项目 id，直接定位到该项目 */
  initialProjectId?: string
  /** true 表示入口是新建报告页，页面顶部给出返回入口 */
  fromReport?: boolean
  /** true 表示入口是「研发项目详情 → 知识库 tab」，页面顶部给出返回项目详情的入口 */
  fromProjectDetail?: boolean
}

const NEW_REPORT_PATH = '/research/reports'

export function KnowledgeBasePage({
  initialProjectId = '',
  fromReport = false,
  fromProjectDetail = false,
}: Props) {
  const { message: msgApi } = App.useApp()
  const [projects, setProjects] = useState<RdProject[]>([])
  const [projectId, setProjectId] = useState<string>(initialProjectId)

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const result = await fetchRdProjects({ page_size: 100 })
        setProjects(result.items)
      } catch (e: unknown) {
        msgApi.error(e instanceof Error ? e.message : '加载项目列表失败')
      }
    }
    loadProjects()
  }, [msgApi])

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>项目知识库</h1>
          <p style={{ color: '#666', margin: '4px 0 0 0' }}>
            每个研发项目一个知识库：上传项目资料后自动解析，AI 生成报告时会从中检索并填入模板
          </p>
        </div>
        {fromReport || (fromProjectDetail && (projectId || initialProjectId)) ? (
          <Space>
            {fromReport ? (
              <Link href={NEW_REPORT_PATH}>
                <Button icon={<RollbackOutlined />}>返回新建报告</Button>
              </Link>
            ) : null}
            {fromProjectDetail && (projectId || initialProjectId) ? (
              <Link href={`/research/projects/${projectId || initialProjectId}`}>
                <Button icon={<RollbackOutlined />}>返回项目详情</Button>
              </Link>
            ) : null}
          </Space>
        ) : null}
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <span>选择项目：</span>
          <Select
            style={{ width: 320 }}
            placeholder="请选择研发项目"
            value={projectId || undefined}
            onChange={(value) => setProjectId(value)}
            showSearch
            optionFilterProp="label"
            options={projects.map((p) => ({ value: p.id, label: `${p.name} (${p.api_name})` }))}
          />
        </div>
      </Card>

      <KnowledgeBaseManager projectId={projectId} variant="page" />
    </div>
  )
}
