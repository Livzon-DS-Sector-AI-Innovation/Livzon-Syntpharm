'use client'

import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { Avatar, Drawer, Empty, Input, Select, Spin, Table, Tag, Tree, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { DataNode } from 'antd/es/tree'
import { SearchOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import dayjs from 'dayjs'

import { fetchEmployeeProfileDetail, fetchEmployeeProfiles } from '@/lib/api/client/hr'
import { fetchOrgSyncStatus, triggerOrgSync } from '@/actions/hr'
import { OrgSyncLine } from './OrgSyncLine'
import type { EmployeeProfileDetail, EmployeeProfileListItem, OrgDepartmentNode, OrgSyncStatusData } from '@/types/hr'

interface EmployeeDirectoryClientProps {
  initialTree: OrgDepartmentNode[]
  initialPeople: EmployeeProfileListItem[]
  initialTotal: number
  initialLastSyncedAt: string | null
  initialCompanyName: string
  initialStatus: OrgSyncStatusData
}

function display(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

function displayList(value: string[] | null | undefined): string {
  return value && value.length > 0 ? value.join('、') : '—'
}

function displayPositions(value: { id?: string; name?: string }[] | null | undefined): string {
  const names = (value ?? []).map((position) => position.name).filter((name): name is string => Boolean(name))
  return names.length > 0 ? names.join('、') : '—'
}

function displayDate(value: string | null | undefined): string {
  return value ? dayjs(value).format('YYYY-MM-DD') : '—'
}

function displayBoolean(value: boolean): string {
  return value ? '是' : '否'
}

function Section({ title, rows }: { title: string; rows: { label: string; value: string }[] }) {
  return (
    <div className="mb-5">
      <div className="mb-2 text-[12px] font-semibold tracking-wide text-[var(--color-stone)]">{title}</div>
      <div className="divide-y divide-[var(--color-hairline-soft)] rounded-lg border border-[var(--color-hairline)] px-3">
        {rows.map((row) => (
          <div key={row.label} className="flex gap-3 py-2 text-[13px]">
            <span className="w-[120px] shrink-0 text-[var(--color-stone)]">{row.label}</span>
            <span className={`min-w-0 flex-1 ${row.value === '—' ? 'text-[var(--color-hairline-strong)]' : 'text-[var(--color-charcoal)]'}`}>
              {row.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function PersonDrawer({
  identifier,
  onClose,
}: {
  identifier: string | null
  onClose: () => void
}) {
  const { data, isFetching } = useQuery<EmployeeProfileDetail>({
    queryKey: ['hr-person', identifier],
    queryFn: () => fetchEmployeeProfileDetail(identifier as string),
    enabled: Boolean(identifier),
  })

  return (
    <Drawer
      open={Boolean(identifier)}
      onClose={onClose}
      width={480}
      title={data ? `${data.name} · 员工详情` : '员工详情'}
    >
      {isFetching && !data ? (
        <div className="flex justify-center py-10">
          <Spin />
        </div>
      ) : data ? (
        <>
          <Section
            title="基本信息"
            rows={[
              { label: '姓名', value: display(data.name) },
              { label: 'open_id', value: display(data.open_id) },
              { label: '性别', value: display(data.gender_label) },
              { label: '年龄', value: display(data.age) },
              { label: '学历', value: display(data.education) },
              { label: '手机号', value: display(data.mobile) },
              { label: '邮箱', value: display(data.email) },
              { label: '企业邮箱', value: display(data.enterprise_email) },
              { label: '企业邮箱别名', value: displayList(data.email_aliases) },
              { label: '个性签名', value: display(data.description) },
              { label: '头像', value: display(data.avatar_url) },
              { label: '背景图', value: display(data.background_image) },
              { label: '地理名称', value: display(data.geo_name) },
            ]}
          />
          <Section
            title="状态"
            rows={[
              { label: '账号状态', value: display(data.active_status_label) },
              { label: '是否离职', value: displayBoolean(data.is_resigned) },
              { label: '离职时间', value: display(data.resign_time) },
              { label: '普通管理员', value: displayBoolean(data.is_admin) },
              { label: '超级管理员', value: displayBoolean(data.is_primary_admin) },
              { label: '数据来源', value: display(data.data_source_label) },
            ]}
          />
          <Section
            title="工作信息"
            rows={[
              { label: '工号', value: display(data.employee_no) },
              { label: '一级部门', value: display(data.department_level1_name) },
              { label: '二级部门', value: display(data.department_level2_name) },
              { label: '部门 ID', value: displayList(data.department_ids) },
              { label: '部门名称', value: displayList(data.department_names) },
              {
                label: '部门路径',
                value:
                  data.department_path && data.department_path.length > 0
                    ? data.department_path.map((entry) => entry.name).join(' / ')
                    : '—',
              },
              { label: '职务', value: display(data.job_title_name) },
              { label: '职务 ID', value: display(data.job_title_id) },
              { label: '入职日期', value: displayDate(data.hire_date) },
              { label: '员工类型', value: display(data.employment_type) },
              { label: '人事状态', value: display(data.staff_status_label) },
              { label: '工作国家/地区', value: display(data.work_country_or_region) },
              { label: '工作地点', value: display(data.work_place_name) },
              { label: '工作地点 ID', value: display(data.work_place_id) },
              { label: '工位', value: display(data.work_station) },
              { label: '分机号', value: display(data.extension_number) },
              { label: '虚线上级', value: displayList(data.dotted_line_leader_ids) },
              { label: '职位', value: displayPositions(data.positions) },
              { label: '职级', value: display(data.job_level_name) },
              { label: '职级 ID', value: display(data.job_level_id) },
              { label: '序列（职族）', value: display(data.job_family_name) },
              { label: '序列 ID', value: display(data.job_family_id) },
            ]}
          />
          <Section
            title="离职信息"
            rows={[
              { label: '离职日期', value: displayDate(data.resign_date) },
              { label: '离职类型', value: display(data.resign_type) },
              { label: '离职原因', value: display(data.resign_reason) },
              { label: '离职备注', value: display(data.resign_remark) },
              { label: '上次同步', value: data.last_synced_at ? dayjs(data.last_synced_at).format('YYYY-MM-DD HH:mm') : '—' },
            ]}
          />
        </>
      ) : (
        <Empty description="员工详情暂时不可用" />
      )}
    </Drawer>
  )
}

function toTreeNode(node: OrgDepartmentNode): DataNode {
  return {
    key: node.id,
    title: node.name,
    children: (node.children ?? []).map(toTreeNode),
  }
}

export default function EmployeeDirectoryClient({
  initialTree,
  initialPeople,
  initialTotal,
  initialLastSyncedAt,
  initialCompanyName,
  initialStatus,
}: EmployeeDirectoryClientProps) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [selectedDepartment, setSelectedDepartment] = useState<string | null>(null)
  const [keyword, setKeyword] = useState('')
  const deferredKeyword = useDeferredValue(keyword)
  const [status, setStatus] = useState<string>('1')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [selectedPerson, setSelectedPerson] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const statusQuery = useQuery({
    queryKey: ['hr-org-sync-status'],
    queryFn: fetchOrgSyncStatus,
    initialData: { code: 200, message: 'success', data: initialStatus, meta: null },
    refetchInterval: (query) => (query.state.data?.data.status === 'running' ? 2000 : false),
  })
  const syncStatus = statusQuery.data.data
  const running = syncStatus.status === 'running'
  const syncing = submitting || running
  const wasRunning = useRef(running)

  useEffect(() => {
    if (wasRunning.current && !running) router.refresh()
    wasRunning.current = running
  }, [running, router])

  const handleSync = async () => {
    if (running) return
    setSubmitting(true)
    try {
      const result = await triggerOrgSync()
      queryClient.setQueryData(['hr-org-sync-status'], result)
      message.success(result.data.status === 'running' ? '组织架构同步已开始' : '组织架构同步完成')
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : '组织架构同步失败')
      await queryClient.invalidateQueries({ queryKey: ['hr-org-sync-status'] })
    } finally {
      setSubmitting(false)
    }
  }

  const companyNode = initialTree.find((node) => node.level === 0)
  const companyKey = companyNode?.id ?? 'all'
  const treeData: DataNode[] = useMemo(() => {
    if (companyNode) return [toTreeNode(companyNode)]
    return [
      {
        key: 'all',
        title: initialCompanyName || '公司',
        children: initialTree.map(toTreeNode),
      },
    ]
  }, [companyNode, initialTree, initialCompanyName])

  const isInitialQuery =
    selectedDepartment === null && status === '1' && deferredKeyword === '' && page === 1 && pageSize === 20

  const { data, isFetching } = useQuery({
    queryKey: ['hr-people', selectedDepartment, status, deferredKeyword, page, pageSize],
    queryFn: () =>
      fetchEmployeeProfiles({
        department_id: selectedDepartment ?? undefined,
        status: status || undefined,
        keyword: deferredKeyword || undefined,
        page,
        page_size: pageSize,
      }),
    initialData: isInitialQuery
      ? {
          items: initialPeople,
          total: initialTotal,
          page: 1,
          page_size: 20,
          last_synced_at: initialLastSyncedAt,
        }
      : undefined,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0

  const columns: ColumnsType<EmployeeProfileListItem> = [
    {
      title: '姓名',
      dataIndex: 'name',
      width: 160,
      render: (_value: string, record) => (
        <span className="flex items-center gap-2">
          <Avatar size={28} src={record.avatar_url || undefined} style={{ fontSize: 12 }}>
            {record.name.slice(0, 1)}
          </Avatar>
          <span className="font-medium">{record.name}</span>
        </span>
      ),
    },
    { title: '一级部门', dataIndex: 'department_level1_name', width: 170, render: (v: string) => display(v) },
    { title: '二级部门', dataIndex: 'department_level2_name', width: 160, render: (v: string) => display(v) },
    { title: '职务', dataIndex: 'job_title_name', width: 150, render: (v: string) => display(v) },
    {
      title: '人事状态',
      dataIndex: 'staff_status_label',
      width: 110,
      render: (_value: string, record) =>
        record.is_resigned ? (
          <Tag color="default">离职</Tag>
        ) : (
          <Tag color={record.staff_status === 1 ? 'blue' : 'default'}>{record.staff_status_label}</Tag>
        ),
    },
    {
      title: '查看',
      width: 80,
      render: (_value: unknown, record) => (
        <button
          type="button"
          className="cursor-pointer border-0 bg-transparent p-0 text-[13px] text-[var(--color-primary)]"
          onClick={() => setSelectedPerson(record.id)}
        >
          查看
        </button>
      ),
    },
  ]

  const handleDepartmentSelect = (keys: React.Key[]) => {
    const key = keys[0]
    setSelectedDepartment(!key || key === 'all' || key === companyKey ? null : String(key))
    setPage(1)
  }

  return (
    <div className="flex gap-5">
      <div className="w-[260px] shrink-0 rounded-[10px] border border-[var(--color-hairline)] bg-white p-3">
        <div className="mb-2 text-[12px] font-semibold tracking-wide text-[var(--color-stone)]">组织架构</div>
        <Tree
          blockNode
          defaultExpandAll
          treeData={treeData}
          selectedKeys={[selectedDepartment ?? companyKey]}
          onSelect={handleDepartmentSelect}
        />
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <h1 className="m-0 text-[22px] font-semibold text-[var(--color-charcoal)]">员工档案</h1>
          <OrgSyncLine status={syncStatus} syncing={syncing} onSync={handleSync} />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索姓名、工号、职务、部门"
            allowClear
            value={keyword}
            onChange={(event) => {
              setKeyword(event.target.value)
              setPage(1)
            }}
            className="w-72"
          />
          <Select
            allowClear
            placeholder="人事状态"
            className="w-36"
            value={status || undefined}
            options={[
              { value: '1', label: '在职' },
              { value: '2', label: '离职' },
            ]}
            onChange={(value) => {
              setStatus(value ?? '')
              setPage(1)
            }}
          />
        </div>

        <div className="overflow-hidden rounded-[10px] border border-[var(--color-hairline)] bg-white">
          <Table<EmployeeProfileListItem>
            columns={columns}
            dataSource={items}
            rowKey="id"
            size="middle"
            loading={isFetching}
            pagination={{
              current: page,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (count) => `共 ${count} 人`,
              onChange: (nextPage, nextPageSize) => {
                setPage(nextPageSize !== pageSize ? 1 : nextPage)
                setPageSize(nextPageSize)
              },
            }}
          />
          {items.length === 0 && !isFetching && (
            <Empty className="py-10" description="没有匹配的员工" />
          )}
        </div>
      </div>

      <PersonDrawer identifier={selectedPerson} onClose={() => setSelectedPerson(null)} />
    </div>
  )
}
