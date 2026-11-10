'use client'

import { useState, useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Card, Table, Button, Tag, Space, Popconfirm, Switch, Progress, Tooltip } from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, DownloadOutlined, HistoryOutlined,
} from '@ant-design/icons'
import { fetchReports, fetchDeliverableReportLinks } from '@/lib/api/client/research/rd-project'
import { fetchReportGenJobs, fetchReportGenDocumentBlob, downloadReportGenFile } from '@/lib/api/client/research/report-gen'
import { DocxPreviewModal } from './DocxPreviewModal'
import { CreateReportModal } from './CreateReportModal'
import { deleteReport } from '@/actions/research/modules'
import { getModuleSettings } from '@/actions/module-settings'
import { updateReport } from '@/actions/research/rd-project'
import { PermissionGate } from '@/components/auth/PermissionGate'
import { PERM } from '@/lib/permissions/codes'
import {
  RdReport, RdReportType, RdReportStatus,
  REPORT_TYPE_LABELS, REPORT_STATUS_LABELS, STAGE_LABELS,
} from '@/types/research/rd-project'
import {
  hasActiveJob, isTerminal, latestJobByReport, modelLabel, pickReportGenModels, statusMeta,
} from '@/types/research/report-gen'
import { REPORT_COPY } from '@/lib/ui/research-copy'
import { withReturnTo } from '@/lib/navigation/returnTo'

interface Props {
  /** 报告所属项目：本组件只在项目视图下渲染，「全部项目」由 ReportProjectOverview 承担 */
  projectId: string
}

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
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  // 当前列表地址（含 projectId 过滤），进详情时作为 returnTo 带上，回来才不会丢筛选
  const currentUrl = searchParams.toString() ? `${pathname}?${searchParams.toString()}` : pathname
  const queryClient = useQueryClient()
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<RdReport | null>(null)
  const [togglingId, setTogglingId] = useState<string>('')

  const { data: reports = [], isLoading: loading } = useQuery({
    queryKey: ['reports', projectId],
    queryFn: async () => {
      const data = await fetchReports(projectId)
      return data || []
    },
  })

  /** 整个项目的生成任务一次取回，前端按报告归集「最近一次」。 */
  const { data: jobsData } = useQuery({
    queryKey: ['report-gen-jobs', projectId],
    // 单项目任务数可能超过后端默认 100 条，显式抬到上限，否则老任务会被截断成「未生成」
    queryFn: () => fetchReportGenJobs({ projectId, limit: 200 }),
    // 有任务在跑才轮询；全部终态就停下来
    refetchInterval: (query) => (hasActiveJob(query.state.data?.items ?? []) ? 3000 : false),
  })
  const jobMap = useMemo(() => latestJobByReport(jobsData?.items ?? []), [jobsData])

  /** 从「阶段交付文档」发起的报告会带上来源；一条请求批量取回，列表才能显示来源列。 */
  // 后端一次最多接受 200 个 ID，超出的行只是不显示来源，不影响报告本身
  const reportIds = useMemo(() => reports.slice(0, 200).map((item) => item.id), [reports])
  const { data: deliverableLinks = [] } = useQuery({
    queryKey: ['deliverable-report-links', reportIds.join(',')],
    queryFn: () => fetchDeliverableReportLinks(reportIds),
    enabled: reportIds.length > 0,
    staleTime: 60_000,
  })
  const linkMap = useMemo(
    () => new Map(deliverableLinks.map((item) => [item.report_id, item])),
    [deliverableLinks],
  )

  /** 当前生效模型：来自模块配置，新建任务的弹窗里如实提示用哪一档。 */
  const { data: settings = [] } = useQuery({
    queryKey: ['module-settings', 'research', 'report-gen'],
    queryFn: async () => (await getModuleSettings('research')).data ?? [],
    staleTime: 60_000,
  })
  const models = useMemo(() => pickReportGenModels(settings), [settings])

  // 报告预览弹窗
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewJobId, setPreviewJobId] = useState<string | null>(null)
  const [previewTitle, setPreviewTitle] = useState('报告预览')

  const invalidateReports = () => {
    queryClient.invalidateQueries({ queryKey: ['reports', projectId] })
    queryClient.invalidateQueries({ queryKey: ['report-gen-jobs', projectId] })
    // 项目总览的统计也来自这两份数据，一并失效，避免切回全部时看到旧数字
    queryClient.invalidateQueries({ queryKey: ['reports', 'all'] })
    queryClient.invalidateQueries({ queryKey: ['report-gen-jobs', 'all'] })
  }

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
      invalidateReports()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const handleToggleActive = async (id: string, active: boolean) => {
    if (togglingId) return
    setTogglingId(id)
    try {
      await updateReport(id, { status: active ? 'approved' : 'draft' })
      msgApi.success(active ? '已启用' : '已停用')
      invalidateReports()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '操作失败')
    } finally {
      setTogglingId('')
    }
  }

  const openGeneration = (record: RdReport) => {
    const job = jobMap.get(record.id)
    if (!job) {
      msgApi.info('这份报告还没生成过。点「编辑」，在弹窗里选「用 AI 生成文档」即可')
      return
    }
    router.push(withReturnTo(`/research/reports/generation/${job.id}`, currentUrl))
  }

  /** 在线预览生成的 docx 报告：字节由弹层打开后按需拉取，避免列表页预加载 */
  const handlePreview = (record: RdReport) => {
    const job = jobMap.get(record.id)
    if (!job) return
    setPreviewJobId(job.id)
    setPreviewTitle(record.title || '报告预览')
    setPreviewOpen(true)
  }

  const loadPreviewBlob = () => {
    if (!previewJobId) return Promise.reject(new Error('报告尚未生成，暂不能预览'))
    return fetchReportGenDocumentBlob(previewJobId)
  }

  /** 下载生成的 docx 报告 */
  const handleDownload = async (record: RdReport) => {
    const job = jobMap.get(record.id)
    if (!job) return
    try {
      await downloadReportGenFile(job.id, 'document', `${record.title || '报告'}.docx`)
      msgApi.success('下载成功')
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '下载失败')
    }
  }

  const columns = [
    { title: '报告标题', dataIndex: 'title', key: 'title', width: 230, ellipsis: true },
    { title: '报告类型', dataIndex: 'report_type', key: 'report_type', width: 110,
      render: (v: string) => <Tag color={typeColorMap[v] || 'default'}>{REPORT_TYPE_LABELS[v as RdReportType] || v}</Tag> },
    { title: '阶段', dataIndex: 'stage', key: 'stage', width: 90,
      render: (v: string) => v ? (STAGE_LABELS[v as keyof typeof STAGE_LABELS] || v) : '-' },
    { title: '版本', dataIndex: 'version', key: 'version', width: 70 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string) => <Tag color={statusColorMap[v] || 'default'}>{REPORT_STATUS_LABELS[v as RdReportStatus] || v}</Tag> },
    {
      title: '生成进度', key: 'gen_progress', width: 200,
      render: (_: unknown, record: RdReport) => {
        const job = jobMap.get(record.id)
        if (!job) return <span style={{ color: '#bfbfbf' }}>还没生成过</span>
        const meta = statusMeta(job.status)
        // 终态：只显示状态标签与槽位统计
        if (isTerminal(job.status)) {
          return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Tag color={meta.color} style={{ margin: 0 }}>{meta.label}</Tag>
              {job.slot_total > 0 && (
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>
                  已填 {job.slot_filled}/{job.slot_total} 项
                </span>
              )}
            </div>
          )
        }
        // 进行中：进度条 + 状态标签 + 当前步骤
        return (
          <Tooltip title={job.current_step || meta.label}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Progress
                  percent={job.progress ?? 0}
                  size="small"
                  strokeColor={meta.stroke}
                  style={{ flex: 1, marginBottom: 0 }}
                  status="active"
                />
                <Tag color={meta.color} style={{ margin: 0, flexShrink: 0 }}>{meta.label}</Tag>
              </div>
              {job.current_step && (
                <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>{job.current_step}</div>
              )}
            </div>
          </Tooltip>
        )
      },
    },
    {
      title: '来源交付文档', key: 'source_deliverable', width: 170,
      render: (_: unknown, record: RdReport) => {
        const link = linkMap.get(record.id)
        if (!link) return <span style={{ color: '#bfbfbf' }}>在报告里新建</span>
        return (
          <Tooltip title="这份报告是在项目阶段交付文档里发起的，点回项目查看那条交付文档">
            <a href={withReturnTo(`/research/projects/${link.project_id}?tab=deliverables`, currentUrl)}>
              {link.stage_label} · {link.deliverable_type_label}
            </a>
          </Tooltip>
        )
      },
    },
    { title: '摘要', dataIndex: 'summary', key: 'summary', width: 180, ellipsis: true, render: (v: string) => v || '-' },
    {
      title: '操作', key: 'action', width: 300, fixed: 'right' as const,
      render: (_: unknown, record: RdReport) => {
        const job = jobMap.get(record.id)
        const docReady = !!job && job.status === 'completed' && job.has_document
        return (
          <Space size="small" wrap>
            <PermissionGate code={PERM.researchReportRead}>
              <Tooltip title={job ? '看这次生成每一步做了什么、每个填充项填了什么' : '还没生成过，先点「编辑」用 AI 生成'}>
                <span>
                  <Button
                    type="link"
                    size="small"
                    icon={<HistoryOutlined />}
                    disabled={!job}
                    onClick={() => openGeneration(record)}
                  >
                    生成详情
                  </Button>
                </span>
              </Tooltip>
            </PermissionGate>
            <PermissionGate code={PERM.researchReportUpdate}>
              <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
            </PermissionGate>
            {docReady && (
              <>
                <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record)}>预览</Button>
                <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => handleDownload(record)}>下载</Button>
              </>
            )}
            <PermissionGate code={PERM.researchReportDelete}>
              <Popconfirm
                title={REPORT_COPY.deleteTitle}
                description={REPORT_COPY.deleteDescription}
                onConfirm={() => handleDelete(record.id)}
                okText="删除"
                okButtonProps={{ danger: true }}
                cancelText="取消"
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
              </Popconfirm>
            </PermissionGate>
            <PermissionGate code={PERM.researchReportUpdate}>
              <Tooltip title="打开=这份报告常用，会出现在建议列表里；与审批状态无关">
                <Switch
                  size="small"
                  checkedChildren="常用"
                  unCheckedChildren="不常用"
                  defaultChecked={record.status === 'approved'}
                  disabled={togglingId === record.id}
                  onChange={(checked) => handleToggleActive(record.id, checked)}
                />
              </Tooltip>
            </PermissionGate>
          </Space>
        )
      },
    },
  ]

  return (
    <div>
      <Card
        title={
          <Space size={8} wrap>
            <span>报告列表</span>
            <Tag color="blue" style={{ margin: 0 }}>当前模型：{modelLabel(models.main)}</Tag>
            <span style={{ fontSize: 13, color: '#8c8c8c', fontWeight: 400 }}>
              共 {reports.length} 份
            </span>
          </Space>
        }
        extra={
          <Space size={8}>
            <PermissionGate code={PERM.moduleSettingRead}>
              <Button onClick={() => router.push(withReturnTo('/research/reports/settings', currentUrl))}>生成设置</Button>
            </PermissionGate>
            <PermissionGate code={PERM.researchReportCreate}>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                新建报告
              </Button>
            </PermissionGate>
          </Space>
        }
      >
        <Table
          dataSource={reports}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* 新建/编辑报告：表单 + AI 生成（提交后异步执行） */}
      <CreateReportModal
        open={createModalOpen}
        projectId={projectId}
        onCancel={() => { setCreateModalOpen(false); setEditingRecord(null) }}
        onCreated={() => { invalidateReports(); setEditingRecord(null) }}
        editingReport={editingRecord}
        modelLabel={modelLabel(models.main)}
      />

      {/* 报告文档预览弹窗 */}
      <DocxPreviewModal
        open={previewOpen}
        title={previewTitle}
        loadBlob={loadPreviewBlob}
        onClose={() => { setPreviewOpen(false); setPreviewJobId(null) }}
        onDownload={async () => {
          if (!previewJobId) return
          try {
            await downloadReportGenFile(previewJobId, 'document', `${previewTitle}.docx`)
            msgApi.success('下载成功')
          } catch (e: unknown) {
            msgApi.error(e instanceof Error ? e.message : '下载失败')
          }
        }}
      />
    </div>
  )
}