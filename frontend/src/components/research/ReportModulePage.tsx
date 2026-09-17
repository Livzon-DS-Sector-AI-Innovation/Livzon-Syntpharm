'use client'

import { useState, useEffect } from 'react'
import { App, Card, Select, Empty } from 'antd'
import { fetchRdProjects } from '@/lib/api/client/research/rd-project'
import { RdProject } from '@/types/research/rd-project'
import { ReportPage } from './ReportPage'

export function ReportModulePage() {
  const { message: msgApi } = App.useApp()
  const [projects, setProjects] = useState<RdProject[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const loadProjects = async () => {
      setLoading(true)
      try {
        const result = await fetchRdProjects({ page_size: 100 })
        setProjects(result.items)
      } catch (e: any) {
        msgApi.error(e.message || '加载项目列表失败')
      } finally {
        setLoading(false)
      }
    }
    loadProjects()
  }, [])

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>研发报告</h1>
        <p style={{ color: '#666', margin: '4px 0 0 0' }}>生成和管理研发总结报告、阶段报告、年度报告等</p>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span>选择项目：</span>
          <Select
            style={{ width: 300 }}
            placeholder="请选择研发项目"
            loading={loading}
            value={selectedProjectId}
            onChange={(v) => setSelectedProjectId(v)}
            options={projects.map(p => ({ value: p.id, label: `${p.name} (${p.api_name})` }))}
          />
        </div>
      </Card>

      {selectedProjectId ? (
        <ReportPage projectId={selectedProjectId} />
      ) : (
        <Card>
          <Empty description="请先选择一个项目" />
        </Card>
      )}
    </div>
  )
}
