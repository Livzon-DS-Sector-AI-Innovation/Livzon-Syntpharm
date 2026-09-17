'use client'

import { useState, useEffect, useRef } from 'react'
import { App, Card, Table, Button, Tag, Space, Popconfirm, Switch, Progress, Tooltip, Modal, Spin } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, DownloadOutlined } from '@ant-design/icons'
import { fetchReports } from '@/lib/api/client/research/rd-project'
import { useDocxPreview } from './useDocxPreview'
import {
  fetchDocGenJobsByProject, fetchDocGenDocumentBlob, downloadDocGenDocument,
  type DocGenJobResponse,
} from '@/lib/api/client/research/doc-gen'
import {
  DOC_GEN_STATUS_COLORS, DOC_GEN_STATUS_LABELS,
  isDocGenTerminal,
} from '@/types/research/doc-gen'
import { CreateReportModal } from './CreateReportModal'
import { deleteReport } from '@/actions/research/modules'
import { updateReport } from '@/actions/research/rd-project'
import {
  RdReport, RdReportType, RdReportStatus,
  REPORT_TYPE_LABELS, REPORT_STATUS_LABELS, STAGE_LABELS,
} from '@/types/research/rd-project'

interface Props { projectId: string }

const statusColorMap: Record<string, string> = {
  draft: 'default',
  in_progress: 'processing',
  reviewed: 'cyan',
  approved: 'success',
}

const typeColorMap: Record<string, string> = {
  summary: 'blue',
  stage: 'purple',
  annual: 'orange',
  final: 'green',
  custom: 'default',
}

export function ReportPage({ projectId }: Props) {
  const { message: msgApi } = App.useApp()
  const [reports, setReports] = useState<RdReport[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<RdReport | null>(null)
  /** 各报告最新一次文档生成任务，key = reportId */
  const [docGenMap, setDocGenMap] = useState<Record<string, DocGenJobResponse>>({})
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 报告预览弹窗
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewJobId, setPreviewJobId] = useState<string | null>(null)
  const [previewTitle, setPreviewTitle] = useState('报告预览')
  const previewContentRef = useRef<HTMLDivElement | null>(null)
  const { loading: previewLoading, error: previewError, renderDocx, reset: resetPreview } = useDocxPreview()

  /**
   * 加载项目下全部生成任务，按报告取最新一条（后端按 created_at 倒序返回）。
   * 一次请求覆盖整个列表，避免逐报告查询造成 N+1。
   */
  const loadDocGenMap = async () => {
    try {
      const jobs = await fetchDocGenJobsByProject(projectId)
      const map: Record<string, DocGenJobResponse> = {}
      jobs.forEach((job) => {
        if (job.report_id && !map[job.report_id]) map[job.report_id] = job
      })
      setDocGenMap(map)
      return map
    } catch {
      // 状态列属于附加信息，取不到时不影响报告列表本身
      return {}
    }
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchReports(projectId)
      setReports(data)
      void loadDocGenMap()
    } catch (e: any) {
      msgApi.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [projectId])

  // 轮询：存在进行中任务时每 3 秒刷新 docGenMap，全部到达终态后停止
  useEffect(() => {
    const hasActive = Object.values(docGenMap).some((j) => !isDocGenTerminal(j.status))
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
    if (!hasActive) return
    pollTimerRef.current = setInterval(() => { void loadDocGenMap() }, 3000)
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [docGenMap]) // eslint-disable-line react-hooks/exhaustive-deps

  const openCreate = () => {
    setEditingRecord(null)
    setCreateModalOpen(true)
  }

  const openEdit = (record: RdReport) => {
    setEditingRecord(record)
    setCreateModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteReport(id)
      msgApi.success('删除成功')
      loadData()
    } catch (e: any) {
      msgApi.error(e.message || '删除失败')
    }
  }

  const handleToggleActive = async (id: string, active: boolean) => {
    try {
      await updateReport(id, { status: active ? 'approved' : 'draft' })
      msgApi.success(active ? '已启用' : '已停用')
      loadData()
    } catch (e: any) {
      msgApi.error(e.message || '操作失败')
    }
  }

  /** 判断报告是否有已完成的文档产物 */
  const hasCompletedDoc = (record: RdReport): boolean => {
    const job = docGenMap[record.id]
    return !!job && (job.status === 'completed' || job.status === 'ready') && job.has_document
  }

  /** 在线预览生成的 docx 报告 */
  const handlePreview = async (record: RdReport) => {
    const job = docGenMap[record.id]
    if (!job) return
    setPreviewJobId(job.id)
    setPreviewTitle(record.title || '报告预览')
    setPreviewOpen(true)
    try {
      const blob = await fetchDocGenDocumentBlob(job.id)
      // 等 DOM 就绪后再渲染
      setTimeout(async () => {
        await renderDocx(blob, previewContentRef.current)
      }, 0)
    } catch {
      msgApi.error('加载文档预览失败')
    }
  }

  /** 下载生成的 docx 报告 */
  const handleDownload = async (record: RdReport) => {
    const job = docGenMap[record.id]
    if (!job) return
    const filename = `${record.title || '报告'}.docx`
    try {
      await downloadDocGenDocument(job.id, filename)
      msgApi.success('下载成功')
    } catch {
      msgApi.error('下载失败')
    }
  }

  const columns = [
    { title: '报告标题', dataIndex: 'title', key: 'title', width: 250, ellipsis: true },
    { title: '类型', dataIndex: 'report_type', key: 'report_type', width: 110,
      render: (v: string) => <Tag color={typeColorMap[v] || 'default'}>{REPORT_TYPE_LABELS[v as RdReportType] || v}</Tag> },
    { title: '阶段', dataIndex: 'stage', key: 'stage', width: 90,
      render: (v: string) => v ? (STAGE_LABELS[v as keyof typeof STAGE_LABELS] || v) : '-' },
    { title: '版本', dataIndex: 'version', key: 'version', width: 70 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string) => <Tag color={statusColorMap[v] || 'default'}>{REPORT_STATUS_LABELS[v as RdReportStatus] || v}</Tag> },
    {
      title: '生成进度', key: 'doc_gen_progress', width: 180,
      render: (_: any, record: RdReport) => {
        const job = docGenMap[record.id]
        if (!job) return <span style={{ color: '#bfbfbf' }}>未生成</span>
        const statusLabel = DOC_GEN_STATUS_LABELS[job.status] || job.status
        const statusColor = DOC_GEN_STATUS_COLORS[job.status] || 'default'
        // 终态：只显示状态标签
        if (isDocGenTerminal(job.status)) {
          return <Tag color={statusColor}>{statusLabel}</Tag>
        }
        // 进行中：进度条 + 状态标签 + 当前步骤
        return (
          <Tooltip title={job.step || statusLabel}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Progress
                percent={job.progress ?? 0}
                size="small"
                style={{ flex: 1, marginBottom: 0 }}
                status="active"
              />
              <Tag color={statusColor} style={{ margin: 0, flexShrink: 0 }}>{statusLabel}</Tag>
            </div>
            {job.step && (
              <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>{job.step}</div>
            )}
          </Tooltip>
        )
      },
    },
    { title: '摘要', dataIndex: 'summary', key: 'summary', width: 200, ellipsis: true, render: (v: string) => v || '-' },
    {
      title: '操作', key: 'action', width: 260, fixed: 'right' as const,
      render: (_: any, record: RdReport) => {
        const docReady = hasCompletedDoc(record)
        return (
          <Space size="small" wrap>
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
            {docReady && (
              <>
                <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record)}>预览</Button>
                <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => handleDownload(record)}>下载</Button>
              </>
            )}
            <Popconfirm title="确认删除此报告？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消">
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
            <Switch
              size="small"
              checkedChildren="启用"
              unCheckedChildren="停用"
              defaultChecked={record.status === 'approved'}
              onChange={(checked) => handleToggleActive(record.id, checked)}
            />
          </Space>
        )
      },
    },
  ]

  return (
    <div>
      <Card
        title="研发报告"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建报告</Button>}
      >
        <Table
          dataSource={reports}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1380 }}
        />
      </Card>

      {/* 新建/编辑报告：居中弹窗 + AI 提取/生成流程 */}
      <CreateReportModal
        open={createModalOpen}
        projectId={projectId}
        onCancel={() => { setCreateModalOpen(false); setEditingRecord(null) }}
        onCreated={() => { loadData(); void loadDocGenMap(); setEditingRecord(null) }}
        editingReport={editingRecord}
      />

      {/* 报告文档预览弹窗 */}
      <Modal
        open={previewOpen}
        title={previewTitle}
        width={960}
        onCancel={() => { setPreviewOpen(false); setPreviewJobId(null); resetPreview(); if (previewContentRef.current) previewContentRef.current.innerHTML = '' }}
        footer={
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button
              icon={<DownloadOutlined />}
              disabled={!previewJobId}
              onClick={async () => {
                if (!previewJobId) return
                try {
                  await downloadDocGenDocument(previewJobId, `${previewTitle}.docx`)
                  msgApi.success('下载成功')
                } catch {
                  msgApi.error('下载失败')
                }
              }}
            >
              下载报告
            </Button>
          </div>
        }
        destroyOnClose
      >
        {previewError && (
          <div style={{ color: '#ff4d4f', padding: '8px 0', fontSize: 12 }}>{previewError}</div>
        )}
        {previewLoading && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}><Spin tip="加载文档中..." /></div>
        )}
        <div
          ref={previewContentRef}
          style={{ maxHeight: '75vh', overflow: 'auto', background: '#f5f5f5', padding: 8 }}
        />
      </Modal>
    </div>
  )
}
