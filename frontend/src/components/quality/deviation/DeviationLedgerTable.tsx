'use client'

import { useState, useTransition } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Alert, App, AutoComplete, Breadcrumb, Button, Empty, Grid, Popconfirm, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DeleteOutlined, PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { batchUpdateDeviationStatus, deleteDeviationLedger } from '@/actions/quality'
import type {
  DeviationLedgerFilters,
  DeviationLedgerItem,
  DeviationLedgerOption,
} from '@/types/quality'
import {
  DEVIATION_LEDGER_PATH,
  DEVIATION_LEVEL_COLORS,
  DEVIATION_REASON_CATEGORIES,
  DEVIATION_STATUS_COLORS,
  deviationDetailPath,
} from './constants'
import { PeopleInline, PersonInline } from './PersonInline'

/** 批量更新只开放「作废 / 退回待AI分析」两个管理动作，避免绕过审核流 */
const BATCH_TARGET_STATUSES = ['cancelled', 'pending_ai_analysis']

/** 仅这两个状态的偏差允许删除，与后端 _DELETABLE_STATUSES 对齐 */
const DELETABLE_STATUSES = ['pending_ai_analysis', 'cancelled']

/** 列宽单一来源：scroll.x 由列宽求和派生，避免表格宽度与列宽再次漂移 */
const COLUMN_WIDTHS = {
  code: 150,
  title: 260,
  department: 140,
  discoveryDate: 110,
  status: 240,
  level: 90,
  reporter: 130,
  handlers: 170,
  action: 140,
} as const

/** rowSelection 勾选列约 48px */
const SCROLL_X = Object.values(COLUMN_WIDTHS).reduce((sum, width) => sum + width, 48)

interface DeviationLedgerTableProps {
  items: DeviationLedgerItem[]
  total: number
  page: number
  pageSize: number
  /** 当前生效筛选（来自 URL），用于回填控件 */
  filters: DeviationLedgerFilters
  departmentOptions: DeviationLedgerOption[]
  statusOptions: DeviationLedgerOption[]
  /** 后端取数失败时的提示，已渲染为告警条 */
  loadError?: string | null
}

interface FilterDraft {
  reasonCategory?: string
  status?: string
  department?: string
}

function draftFromFilters(filters: DeviationLedgerFilters): FilterDraft {
  return {
    reasonCategory: filters.reason_category,
    status: filters.status,
    department: filters.department,
  }
}

/** 原因分类候选：QA 审核改为自由填写后，这些值只作为筛选输入时的提示 */
const REASON_CATEGORY_OPTIONS = DEVIATION_REASON_CATEGORIES.map((value) => ({ value, label: value }))

export function DeviationLedgerTable({
  items,
  total,
  page,
  pageSize,
  filters,
  departmentOptions,
  statusOptions,
  loadError = null,
}: DeviationLedgerTableProps) {
  const router = useRouter()
  const [isPending, startTransition] = useTransition()
  const [draft, setDraft] = useState<FilterDraft>(() => draftFromFilters(filters))
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])
  const [batchStatus, setBatchStatus] = useState<string | undefined>(undefined)
  const [batchPending, setBatchPending] = useState(false)
  const { message, modal } = App.useApp()

  // 浏览器前进/后退会换掉 URL：把控件回填成当前 URL 的条件
  const filterSignature = JSON.stringify(filters)
  const [syncedSignature, setSyncedSignature] = useState(filterSignature)
  if (syncedSignature !== filterSignature) {
    setSyncedSignature(filterSignature)
    setDraft(draftFromFilters(filters))
  }

  const buildQuery = (patch: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams()
    const merged: Record<string, string | number | undefined> = {
      reason_category: filters.reason_category,
      status: filters.status,
      department: filters.department,
      page: 1,
      page_size: pageSize,
      ...patch,
    }
    Object.entries(merged).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value))
      }
    })
    return `${DEVIATION_LEDGER_PATH}?${params.toString()}`
  }

  const navigate = (url: string) => {
    startTransition(() => {
      router.push(url)
    })
  }

  const handleSearch = () => {
    navigate(
      buildQuery({
        reason_category: draft.reasonCategory,
        status: draft.status,
        department: draft.department,
        page: 1,
      }),
    )
  }

  const handleReset = () => {
    setDraft({})
    navigate(DEVIATION_LEDGER_PATH)
  }

  const statusLabelOf = (value: string): string =>
    statusOptions.find((item) => item.value === value)?.label ?? value

  const submitBatchStatus = async (targetStatus: string) => {
    setBatchPending(true)
    const result = await batchUpdateDeviationStatus({ ids: selectedKeys, status: targetStatus })
    setBatchPending(false)
    if (result.code === 200) {
      message.success(`已更新 ${result.data?.updated ?? selectedKeys.length} 条`)
      setSelectedKeys([])
      setBatchStatus(undefined)
      router.refresh()
    } else {
      message.error(result.message)
    }
  }

  const handleBatchUpdate = () => {
    if (selectedKeys.length === 0) {
      message.warning('请先勾选要更新的偏差')
      return
    }
    if (!batchStatus) {
      message.warning('请选择目标状态')
      return
    }
    modal.confirm({
      title: `确认将 ${selectedKeys.length} 条偏差状态改为「${statusLabelOf(batchStatus)}」？`,
      content: '批量状态更新不经审核流程，请确认所选记录无误。',
      okText: '确认更新',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => submitBatchStatus(batchStatus),
    })
  }

  const handleDelete = async (row: DeviationLedgerItem) => {
    const result = await deleteDeviationLedger(row.id)
    if (result.code === 200) {
      message.success('偏差已删除')
      setSelectedKeys((prev) => prev.filter((key) => key !== row.id))
      router.refresh()
    } else {
      message.error(result.message)
    }
  }

  const screens = Grid.useBreakpoint()

  const columns: ColumnsType<DeviationLedgerItem> = [
    {
      title: '偏差编号',
      dataIndex: 'display_code',
      key: 'display_code',
      width: COLUMN_WIDTHS.code,
      responsive: ['sm'],
      fixed: screens.lg ? 'left' : undefined,
      ellipsis: { showTitle: true },
      render: (value: string) => (
        <span className="whitespace-nowrap font-mono text-[13px]">{value}</span>
      ),
    },
    {
      title: '偏差名称',
      dataIndex: 'title',
      key: 'title',
      width: COLUMN_WIDTHS.title,
      fixed: screens.lg ? 'left' : undefined,
      ellipsis: { showTitle: true },
      render: (value: string, row) => (
        <Link
          href={deviationDetailPath(row.id)}
          className="block truncate text-[13px] leading-5 text-[var(--color-ink)] hover:text-[var(--color-primary)]"
          title={value}
        >
          {value}
        </Link>
      ),
    },
    {
      title: '发生部门',
      dataIndex: 'department',
      key: 'department',
      width: COLUMN_WIDTHS.department,
      responsive: ['lg'],
      ellipsis: { showTitle: true },
    },
    {
      title: '发现日期',
      dataIndex: 'discovery_date',
      key: 'discovery_date',
      width: COLUMN_WIDTHS.discoveryDate,
      responsive: ['lg'],
      render: (value: string | null) => <span className="whitespace-nowrap">{value || '-'}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: COLUMN_WIDTHS.status,
      render: (_: string, row) => (
        <div className="flex flex-col gap-1">
          <span className="flex flex-wrap items-center gap-1">
            <Tag color={DEVIATION_STATUS_COLORS[row.status] ?? 'default'}>{row.status_label}</Tag>
            {row.is_overdue && <Tag color="red">超期 {row.overdue_days} 天</Tag>}
          </span>
          {row.returned_step_label && (
            <span className="line-clamp-1 text-[12px] text-[var(--color-error)]" title={row.returned_step_label}>
              已退回：{row.returned_step_label}
            </span>
          )}
          {row.current_handlers?.length ? (
            <span className="flex min-w-0 flex-wrap items-center gap-1 text-[12px] text-[var(--color-stone)]">
              处理人：
              <PeopleInline people={row.current_handlers} avatarSize={20} gapClassName="gap-x-2" />
            </span>
          ) : (
            <span className="line-clamp-1 text-[12px] text-[var(--color-stone)]">处理人：{row.current_handler || '-'}</span>
          )}
        </div>
      ),
    },
    {
      title: '分级',
      dataIndex: 'deviation_level',
      key: 'deviation_level',
      width: COLUMN_WIDTHS.level,
      responsive: ['lg'],
      render: (_: string | null, row) =>
        row.deviation_level ? (
          <Tag color={DEVIATION_LEVEL_COLORS[row.deviation_level] ?? 'default'}>{row.level_label}</Tag>
        ) : (
          <span className="text-[var(--color-stone)]">-</span>
        ),
    },
    {
      title: '上报人',
      dataIndex: 'reporter_name',
      key: 'reporter_name',
      width: COLUMN_WIDTHS.reporter,
      responsive: ['xl'],
      ellipsis: { showTitle: true },
      render: (_: string | null, row) =>
        row.reporter?.name ? (
          <PersonInline person={row.reporter} avatarSize={22} />
        ) : (
          (row.reporter_name || '-')
        ),
    },
    {
      title: '调查人',
      dataIndex: 'handler_names',
      key: 'handler_names',
      width: COLUMN_WIDTHS.handlers,
      responsive: ['xl'],
      ellipsis: { showTitle: true },
      render: (value: string[], row) =>
        row.handlers?.length ? (
          <PeopleInline people={row.handlers} avatarSize={22} />
        ) : value.length > 0 ? (
          value.join('、')
        ) : (
          '-'
        ),
    },
    {
      title: '操作',
      key: 'action',
      width: COLUMN_WIDTHS.action,
      /* 窄屏不固定操作列：固定列会遮住仅剩的内容列，改为随表格横向滚动 */
      fixed: screens.lg ? 'right' : undefined,
      render: (_: unknown, row) => (
        <Space size={4}>
          <Link href={deviationDetailPath(row.id)}>
            <Button type="link" size="small">
              查看
            </Button>
          </Link>
          {DELETABLE_STATUSES.includes(row.status) && (
            <Popconfirm
              title="删除该偏差？"
              description="删除后不再出现在台账中，且不可恢复。"
              okText="删除"
              okButtonProps={{ danger: true }}
              cancelText="取消"
              onConfirm={() => handleDelete(row)}
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Breadcrumb
            className="mb-1"
            items={[
              { title: <Link href="/quality">质量管理</Link> },
              { title: <Link href="/quality/deviation">偏差管理</Link> },
              { title: '偏差台账' },
            ]}
          />
          <h1 className="text-[22px] font-semibold text-[var(--color-ink)]">偏差台账</h1>
          <p className="mt-1 text-[13px] text-[var(--color-slate)]">
            全部偏差的登记与流转状态，可按原因分类、状态与发生部门筛选
          </p>
        </div>
        <Link href="/quality/deviation/new" className="shrink-0 self-start sm:self-auto">
          <Button type="primary" icon={<PlusOutlined />}>
            新建偏差
          </Button>
        </Link>
      </header>

      {loadError && <Alert type="warning" showIcon title="台账数据加载失败" description={loadError} />}

      <section className="rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* 原因分类已改为自由填写，筛选侧同步允许直接输入（候选项仅作提示） */}
          <AutoComplete
            allowClear
            placeholder="原因分类（可输入）"
            className="w-full sm:w-[180px]"
            value={draft.reasonCategory}
            options={REASON_CATEGORY_OPTIONS}
            onChange={(value) => setDraft((prev) => ({ ...prev, reasonCategory: value || undefined }))}
          />
          <Select
            allowClear
            placeholder="请选择状态"
            className="w-full sm:w-[180px]"
            value={draft.status}
            options={statusOptions.map((item) => ({ value: item.value, label: item.label }))}
            onChange={(value) => setDraft((prev) => ({ ...prev, status: value }))}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="请选择发生部门"
            className="w-full sm:w-[180px]"
            value={draft.department}
            options={departmentOptions.map((item) => ({ value: item.value, label: item.label }))}
            onChange={(value) => setDraft((prev) => ({ ...prev, department: value }))}
          />
          <Space wrap className="w-full sm:w-auto">
            <Button type="primary" icon={<SearchOutlined />} loading={isPending} onClick={handleSearch}>
              查询
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置
            </Button>
          </Space>
        </div>
      </section>

      <section className="rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-4">
        {selectedKeys.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[var(--color-surface-soft)] px-3 py-2">
            <span className="text-[13px] text-[var(--color-slate)]">已选 {selectedKeys.length} 条</span>
            <Space wrap>
              <Select
                placeholder="目标状态"
                className="w-full sm:w-[160px]"
                value={batchStatus}
                options={BATCH_TARGET_STATUSES.map((value) => ({ value, label: statusLabelOf(value) }))}
                onChange={(value) => setBatchStatus(value)}
              />
              <Button danger loading={batchPending} onClick={handleBatchUpdate}>
                批量更新状态
              </Button>
              <Button type="text" onClick={() => setSelectedKeys([])}>
                清空选择
              </Button>
            </Space>
          </div>
        )}
        <Table<DeviationLedgerItem>
          rowKey="id"
          size="middle"
          columns={columns}
          dataSource={items}
          loading={isPending}
          rowSelection={{
            selectedRowKeys: selectedKeys,
            preserveSelectedRowKeys: true,
            onChange: (keys) => setSelectedKeys(keys.map((key) => String(key))),
          }}
          scroll={{ x: SCROLL_X }}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无偏差记录" /> }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (count) => `共 ${count} 条`,
            onChange: (nextPage, nextPageSize) =>
              navigate(buildQuery({ page: nextPage, page_size: nextPageSize })),
          }}
        />
      </section>
    </div>
  )
}