'use client'

import type { CSSProperties } from 'react'
import { Alert, Drawer, Table, Tag, Typography } from 'antd'
import type { TableProps } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { fetchTemplateStructureRuns } from '@/lib/api/client/research/report-gen'
import type { ReportGenStructureRun } from '@/types/research/report-gen'

interface Props {
  open: boolean
  templateId: string | null
  templateName: string
  onClose: () => void
}

const drawerStyles: { wrapper: CSSProperties } = { wrapper: { width: '64vw' } }

/** 一次看最近 10 次够了：留痕是用来看趋势的，不是审计明细 */
const RUN_LIMIT = 10

const seconds = (ms: number) => `${(ms / 1000).toFixed(1)}s`

const keysText = (keys?: string[]) => (keys && keys.length ? keys.slice(0, 5).join('、') : '—')

const columns: TableProps<ReportGenStructureRun>['columns'] = [
  {
    title: '解析时间',
    dataIndex: 'created_at',
    width: 170,
    render: (value: string, row) => (
      <div>
        <div>{new Date(value).toLocaleString()}</div>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          耗时 {seconds(row.duration_ms)}
        </Typography.Text>
      </div>
    ),
  },
  {
    title: '模型 / 提示词指纹',
    dataIndex: 'model_name',
    width: 200,
    render: (_: unknown, row) => (
      <div>
        <div>{row.model_name || '未记录'}</div>
        <Typography.Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {row.prompt_version}
        </Typography.Text>
      </div>
    ),
  },
  {
    title: '候选 → 槽位',
    dataIndex: 'slot_count',
    width: 110,
    render: (_: unknown, row) => `${row.candidate_count} → ${row.slot_count}`,
  },
  {
    title: '人工改动（保留 / 后补 / 否掉）',
    dataIndex: 'missing_count',
    render: (_: unknown, row) => (
      <div>
        <div>
          {row.diff.kept_count} / <Typography.Text type="warning">{row.diff.missing_count}</Typography.Text> /{' '}
          <Typography.Text type="danger">{row.diff.extra_count}</Typography.Text>
        </div>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          后补：{keysText(row.diff.missing_keys)}；否掉：{keysText(row.diff.extra_keys)}
        </Typography.Text>
      </div>
    ),
  },
  {
    title: '状态',
    dataIndex: 'status',
    width: 90,
    render: (value: string, row) =>
      value === 'ok' ? (
        <Tag color="success">成功</Tag>
      ) : (
        <Tag color="error" title={row.error ?? undefined}>
          失败
        </Tag>
      ),
  },
]

/**
 * 母本解析留痕：每次 AI 识别选了多少槽位，人工随后又补了/否掉了多少。
 *
 * 为「重新识别后要不要再人工修一遍」提供依据：同一模板连续几次都大量后补，
 * 说明识别提示词或候选位置规则该调了。
 */
export function TemplateStructureRunsDrawer({ open, templateId, templateName, onClose }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['template-structure-runs', templateId, RUN_LIMIT],
    queryFn: () => fetchTemplateStructureRuns(templateId as string, RUN_LIMIT),
    enabled: open && Boolean(templateId),
    staleTime: 0,
    gcTime: 0,
    retry: false,
  })

  const items = data?.items ?? []

  return (
    <Drawer
      title={`解析历史：${templateName}`}
      open={open}
      onClose={onClose}
      destroyOnHidden
      styles={drawerStyles}
    >
      <Alert
        type="info"
        showIcon
        title="AI 选了什么，人改了什么"
        description="后补 = 当前启用但解析当时没选（人工加的槽位）；否掉 = 解析当时选了、现在被停用。数字是「当前结构」对比「解析当时」，跨多次人工编辑会混在一起，只看趋势。"
        style={{ marginBottom: 12 }}
      />
      <Table<ReportGenStructureRun>
        rowKey="id"
        size="small"
        loading={isLoading}
        columns={columns}
        dataSource={items}
        pagination={false}
        scroll={{ x: 720 }}
        locale={{
          emptyText: error instanceof Error ? error.message : '该模板还没有解析记录',
        }}
      />
    </Drawer>
  )
}