'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button, Drawer, Empty, Input, Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { fetchOrgSyncStatus, triggerOrgSync } from '@/actions/hr'
import type { OrgDepartmentNode, OrgSyncStatusData } from '@/types/hr'

interface DepartmentOrgClientProps {
  initialTree: OrgDepartmentNode[]
  initialStatus: OrgSyncStatusData
}

function formatTime(value?: string | null): string {
  if (!value) return '—'
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

function formatCustomField(field: Record<string, unknown>): string {
  const key = typeof field.field_key === 'string' && field.field_key ? field.field_key : '字段'
  const entry = Object.entries(field).find(
    ([name, value]) =>
      name !== 'field_key' &&
      name !== 'field_type' &&
      value !== null &&
      value !== undefined &&
      value !== '',
  )
  if (!entry) return key
  const value = typeof entry[1] === 'string' ? entry[1] : JSON.stringify(entry[1])
  return `${key}：${value}`
}

function filterTree(nodes: OrgDepartmentNode[], keyword: string): OrgDepartmentNode[] {
  const q = keyword.trim()
  if (!q) return nodes
  return nodes.flatMap((node) => {
    const selfMatched = node.name.includes(q)
    const children = (node.children ?? []).filter((child) => child.name.includes(q))
    if (selfMatched) return [node]
    if (children.length === 0) return []
    return [{ ...node, children }]
  })
}

function searchExpandedKeys(nodes: OrgDepartmentNode[]): string[] {
  return nodes
    .filter((node) => (node.children ?? []).length > 0)
    .map((node) => node.id)
}

function SyncLine({
  status,
  syncing,
  onSync,
}: {
  status: OrgSyncStatusData
  syncing: boolean
  onSync: () => void
}) {
  const failed = status.status === 'failed'
  const running = status.status === 'running'
  const never = status.status === 'never'
  const label = never
    ? '尚未同步'
    : running
      ? '同步中'
      : failed
        ? '失败'
        : '成功'
  const dotColor = never ? '#a4a097' : failed ? '#e03131' : running ? '#dd5b00' : '#1aae39'
  const labelColor = failed ? '#c62828' : running ? '#a34700' : '#1a7f37'

  return (
    <div className="flex items-start gap-3">
      <div className="text-right">
        <div className="text-xs text-[#787671]">上次同步 {formatTime(status.last_synced_at)}</div>
        <div className="mt-0.5 text-xs">
          <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: dotColor }} />
          <span style={{ color: labelColor }}>{label}</span>
          {!never && (
            <span className="ml-1 text-[#a4a097]">
              · 部门 {status.department_count} · 人员 {status.people_count}
            </span>
          )}
        </div>
        {failed && status.error_message && (
          <div className="mt-0.5 max-w-[360px] truncate text-xs text-[#c62828]" title={status.error_message}>
            {status.error_message}
          </div>
        )}
      </div>
      <Button size="small" icon={<ReloadOutlined />} loading={syncing} onClick={onSync}>
        立即同步
      </Button>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-3 border-b border-[#f0eeec] py-2.5 text-[13px]">
      <span className="w-[110px] shrink-0 text-[#a4a097]">{label}</span>
      <span className="min-w-0 flex-1 text-[#37352f]">{value}</span>
    </div>
  )
}

export default function DepartmentOrgClient({ initialTree, initialStatus }: DepartmentOrgClientProps) {
  const router = useRouter()
  const [keyword, setKeyword] = useState('')
  const [expandedKeys, setExpandedKeys] = useState<string[]>([])
  const [selected, setSelected] = useState<OrgDepartmentNode | null>(null)
  const [status, setStatus] = useState<OrgSyncStatusData>(initialStatus)
  const [syncing, setSyncing] = useState(false)

  const filtered = useMemo(() => filterTree(initialTree, keyword), [initialTree, keyword])
  const autoExpanded = useMemo(() => searchExpandedKeys(filtered), [filtered])
  const effectiveExpanded = keyword ? autoExpanded : expandedKeys
  const allParentKeys = useMemo(() => searchExpandedKeys(initialTree), [initialTree])

  const handleSync = async () => {
    setSyncing(true)
    try {
      const result = await triggerOrgSync()
      setStatus(result.data)
      message.success('组织架构同步完成')
      router.refresh()
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : '组织架构同步失败')
      try {
        const latest = await fetchOrgSyncStatus()
        setStatus(latest.data)
      } catch {
        // 状态刷新失败时保留旧状态，页面仍可用
      }
    } finally {
      setSyncing(false)
    }
  }

  const columns: ColumnsType<OrgDepartmentNode> = [
    {
      title: '部门名称',
      dataIndex: 'name',
      render: (value: string, record) => (
        <span className={record.level === 1 ? 'font-medium text-[#1a1a1a]' : 'text-[#37352f]'}>{value}</span>
      ),
    },
    {
      title: '层级',
      width: 90,
      dataIndex: 'level',
      render: (level: number) =>
        level === 1 ? (
          <Tag>一级</Tag>
        ) : (
          <Tag color="blue" variant="filled">
            二级
          </Tag>
        ),
    },
    {
      title: '负责人',
      width: 140,
      dataIndex: 'leader_display',
      render: (value: string) => value || '—',
    },
    {
      title: '查看',
      width: 80,
      render: (_value, record) => (
        <Button
          type="link"
          size="small"
          onClick={(event) => {
            event.stopPropagation()
            setSelected(record)
          }}
        >
          查看
        </Button>
      ),
    },
  ]

  const detailRows: { label: string; value: React.ReactNode }[] = selected
    ? [
        { label: '部门名称', value: selected.name },
        { label: '层级', value: selected.level === 1 ? '一级部门' : '二级部门' },
        { label: '负责人', value: selected.leader_display || '—' },
        { label: '上级部门', value: selected.parent_name || '—' },
        {
          label: '部门路径',
          value:
            selected.department_path && selected.department_path.length > 0
              ? selected.department_path.map((entry) => entry.name).join(' / ')
              : '—',
        },
        { label: '递归成员数', value: `${selected.recursive_members_count} 人` },
        { label: '直属成员数', value: `${selected.direct_members_count} 人` },
        { label: '递归下级部门数', value: `${selected.recursive_departments_count} 个` },
        { label: '直属下级部门数', value: `${selected.direct_departments_count} 个` },
        {
          label: '启用状态',
          value:
            selected.enabled_status === true ? '启用' : selected.enabled_status === false ? '停用' : '—',
        },
        { label: '排序权重', value: selected.order_weight || '—' },
        { label: '数据来源', value: selected.data_source || '—' },
        {
          label: '自定义字段',
          value:
            selected.custom_fields && selected.custom_fields.length > 0
              ? selected.custom_fields.map((field, index) => (
                  <div key={`${selected.id}-field-${index}`}>{formatCustomField(field)}</div>
                ))
              : '—',
        },
      ]
    : []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="m-0 text-[22px] font-semibold text-[#37352f]">部门管理</h1>
            <Tag color="default" variant="filled">
              只读
            </Tag>
          </div>
          <div className="mt-1 text-[12.5px] text-[#a4a097]">
            来自飞书组织架构，两级结构；仅浏览，不可新增或编辑
          </div>
        </div>
        <SyncLine status={status} syncing={syncing} onSync={handleSync} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索部门名称"
          allowClear
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          className="w-72"
        />
        <Button size="small" onClick={() => setExpandedKeys(allParentKeys)} disabled={Boolean(keyword)}>
          全部展开
        </Button>
        <Button size="small" onClick={() => setExpandedKeys([])} disabled={Boolean(keyword)}>
          全部收起
        </Button>
        {keyword && <span className="text-xs text-[#a4a097]">搜索时自动展开命中路径</span>}
      </div>

      <div className="overflow-hidden rounded-[10px] border border-[#e5e3df] bg-white">
        <Table<OrgDepartmentNode>
          rowKey="id"
          columns={columns}
          dataSource={filtered}
          pagination={false}
          size="middle"
          expandable={{
            expandedRowKeys: effectiveExpanded,
            indentSize: 20,
            expandRowByClick: true,
            onExpandedRowsChange: (keys) => {
              if (!keyword) setExpandedKeys(keys as string[])
            },
          }}
          locale={{ emptyText: <Empty className="py-10" description="没有匹配的部门" /> }}
        />
      </div>

      <Drawer
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        width={430}
        title={selected ? `${selected.name} · 部门详情` : '部门详情'}
      >
        {selected && (
          <div>
            {detailRows.map((row) => (
              <DetailRow key={row.label} label={row.label} value={row.value} />
            ))}
          </div>
        )}
      </Drawer>
    </div>
  )
}
