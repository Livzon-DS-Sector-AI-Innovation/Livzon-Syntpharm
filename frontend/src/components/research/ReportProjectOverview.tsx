'use client'

/**
 * 全部项目的研发报告总览。
 *
 * 未选项目时替代 ReportPage 的报告表格：一行一个项目，点行才看该项目名下的报告，
 * 与 KnowledgeBaseOverview 保持同一形态。数据由已拉回的全量报告与生成任务在前端聚合，
 * 不额外增加后端接口。
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Card, Empty, Space, Table, Tag } from 'antd'
import dayjs from 'dayjs'
import { fetchReports } from '@/lib/api/client/research/rd-project'
import { fetchReportGenJobs } from '@/lib/api/client/research/report-gen'
import type { RdReport } from '@/types/research/rd-project'
import { hasActiveJob, isTerminal, statusMeta, type ReportGenJob } from '@/types/research/report-gen'

interface Props {
  /** 切到某个项目的报告列表 */
  onSelectProject: (projectId: string) => void
}

/** 一行项目：报告数、最近更新与最近一次生成任务都由明细聚合而来 */
interface ProjectSummary {
  projectId: string
  projectName: string
  reportCount: number
  lastReportAt: string
  latestJob: ReportGenJob | null
  activeJobs: number
}

/** 全量报告的条数上限（后端默认 200），用于提示计数口径 */
const FULL_LIST_LIMIT = 200

function summarize(reports: RdReport[], jobs: ReportGenJob[]): ProjectSummary[] {
  const map = new Map<string, ProjectSummary>()

  for (const report of reports) {
    const at = report.updated_at || report.created_at
    const current = map.get(report.project_id)
    if (!current) {
      map.set(report.project_id, {
        projectId: report.project_id,
        projectName: report.project_name || '',
        reportCount: 1,
        lastReportAt: at,
        latestJob: null,
        activeJobs: 0,
      })
      continue
    }
    current.reportCount += 1
    if (new Date(at).getTime() > new Date(current.lastReportAt).getTime()) current.lastReportAt = at
    // 同一项目的报告都带同一个项目名，补空即可
    if (!current.projectName && report.project_name) current.projectName = report.project_name
  }

  // 任务列表按 created_at 倒序返回，每个项目首条即最近一次
  for (const job of jobs) {
    const current = map.get(job.project_id)
    // 报告已删或项目无报告时不单独成行，避免出现「0 份报告」的行
    if (!current) continue
    if (!current.latestJob) current.latestJob = job
    if (!isTerminal(job.status)) current.activeJobs += 1
  }

  return [...map.values()].sort(
    (a, b) => new Date(b.lastReportAt).getTime() - new Date(a.lastReportAt).getTime(),
  )
}

export function ReportProjectOverview({ onSelectProject }: Props) {
  const { data: reports = [], isLoading: reportsLoading } = useQuery({
    queryKey: ['reports', 'all'],
    queryFn: async () => (await fetchReports()) || [],
  })

  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['report-gen-jobs', 'all'],
    // 跨项目取任务：显式抬到上限，否则老任务会被截断成「未生成」
    queryFn: () => fetchReportGenJobs({ limit: FULL_LIST_LIMIT }),
    // 有任务在跑才轮询，全部终态就停下来
    refetchInterval: (query) => (hasActiveJob(query.state.data?.items ?? []) ? 3000 : false),
  })

  const rows = useMemo(() => summarize(reports, jobsData?.items ?? []), [reports, jobsData])

  const totalReports = useMemo(() => rows.reduce((sum, row) => sum + row.reportCount, 0), [rows])
  const truncated = reports.length >= FULL_LIST_LIMIT

  const columns = [
    {
      title: '项目',
      dataIndex: 'projectName',
      key: 'projectName',
      width: 260,
      ellipsis: true,
      render: (v: string, record: ProjectSummary) => v || record.projectId,
    },
    {
      title: '报告数',
      dataIndex: 'reportCount',
      key: 'reportCount',
      width: 100,
      render: (v: number) => `${v} 份`,
    },
    {
      title: '最近更新',
      dataIndex: 'lastReportAt',
      key: 'lastReportAt',
      width: 170,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '最近生成状态',
      key: 'gen_status',
      width: 220,
      render: (_: unknown, record: ProjectSummary) => {
        if (record.activeJobs > 0) {
          return (
            <Space size={6}>
              <Tag color="processing" style={{ margin: 0 }}>
                生成中 {record.activeJobs}
              </Tag>
              {record.latestJob?.current_step && (
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>{record.latestJob.current_step}</span>
              )}
            </Space>
          )
        }
        if (!record.latestJob) return <span style={{ color: '#bfbfbf' }}>未生成</span>
        const meta = statusMeta(record.latestJob.status)
        return (
          <Space size={6}>
            <Tag color={meta.color} style={{ margin: 0 }}>{meta.label}</Tag>
            <span style={{ fontSize: 12, color: '#8c8c8c' }}>
              {dayjs(record.latestJob.created_at).format('YYYY-MM-DD HH:mm')}
            </span>
          </Space>
        )
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: unknown, record: ProjectSummary) => (
        <Button
          type="link"
          size="small"
          onClick={(e) => {
            // 整行也可点，避免按钮再冒泡触发一次
            e.stopPropagation()
            onSelectProject(record.projectId)
          }}
        >
          查看
        </Button>
      ),
    },
  ]

  return (
    <Card
      title={
        <span>
          项目报告总览
          <span style={{ fontSize: 13, color: '#8c8c8c', fontWeight: 400, marginLeft: 8 }}>
            共 {rows.length} 个项目 · {totalReports} 份报告
            {truncated ? '（按最近 200 份统计）' : ''}
          </span>
        </span>
      }
    >
      <Table
        dataSource={rows}
        columns={columns}
        rowKey="projectId"
        loading={reportsLoading || jobsLoading}
        size="small"
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        scroll={{ x: 850 }}
        locale={{
          emptyText: <Empty description="还没有任何项目报告：在上方选择一个项目，即可为它新建报告" />,
        }}
        onRow={(record) => ({
          onClick: () => onSelectProject(record.projectId),
          style: { cursor: 'pointer' },
        })}
      />
    </Card>
  )
}