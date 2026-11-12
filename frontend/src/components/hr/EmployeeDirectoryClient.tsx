'use client'

import { useDeferredValue, useMemo, useState } from 'react'
import { Avatar, Drawer, Empty, Input, Select, Spin, Table, Tag, Tree } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { DataNode } from 'antd/es/tree'
import { SearchOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'

import { fetchEmployeeProfileDetail, fetchEmployeeProfiles } from '@/lib/api/client/hr'
import type { EmployeeProfileDetail, EmployeeProfileListItem, OrgDepartmentNode } from '@/types/hr'

const COMPANY_NAME = '珠海保税区丽珠合成制药有限公司'

interface EmployeeDirectoryClientProps {
  initialTree: OrgDepartmentNode[]
  initialPeople: EmployeeProfileListItem[]
  initialTotal: number
  initialLastSyncedAt: string | null
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
      <div className="mb-2 text-[12px] font-semibold tracking-wide text-[#a4a097]">{title}</div>
      <div className="divide-y divide-[#f0eeec] rounded-lg border border-[#e5e3df] px-3">
        {rows.map((row) => (
          <div key={row.label} className="flex gap-3 py-2 text-[13px]">
            <span className="w-[120px] shrink-0 text-[#a4a097]">{row.label}</span>
            <span className={`min-w-0 flex-1 ${row.value === '—' ? 'text-[#c8c4be]' : 'text-[#37352f]'}`}>
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
              { label: '性别', value: display(data.gender_label) },
              { label: '手机号', value: display(data.mobile) },
              { label: '邮箱', value: display(data.email) },
              { label: '企业邮箱', value: display(data.enterprise_email) },
              { label: '企业邮箱别名', value: displayList(data.email_aliases) },
              { label: '个性签名', value: display(data.description) },
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
              { label: '职务', value: display(data.job_title_name) },
              { label: '入职日期', value: displayDate(data.hire_date) },
              { label: '员工类型', value: display(data.employment_type) },
              { label: '人事状态', value: display(data.staff_status_label) },
              { label: '工作国家/地区', value: display(data.work_country_or_region) },
              { label: '工作地点', value: display(data.work_place_name) },
              { label: '工位', value: display(data.work_station) },
              { label: '分机号', value: display(data.extension_number) },
              { label: '虚线上级', value: displayList(data.dotted_line_leader_ids) },
              { label: '职位', value: displayPositions(data.positions) },
              { label: '职级', value: display(data.job_level_name) },
              { label: '序列（职族）', value: display(data.job_family_name) },
            ]}
          />
          <Section
            title="离职信息"
            rows={[
              { label: '离职日期', value: displayDate(data.resign_date) },
              { label: '离职类型', value: display(data.resign_type) },
              { label: '离职原因', value: display(data.resign_reason) },
              { label: '离职备注', value: display(data.resign_remark) },
            ]}
          />
        </>
      ) : (
        <Empty description="员工详情暂时不可用" />
      )}
    </Drawer>
  )
}

export default function EmployeeDirectoryClient({
  initialTree,
  initialPeople,
  initialTotal,
  initialLastSyncedAt,
}: EmployeeDirectoryClientProps) {
  const [selectedDepartment, setSelectedDepartment] = useState<string | null>(null)
  const [keyword, setKeyword] = useState('')
  const deferredKeyword = useDeferredValue(keyword)
  const [status, setStatus] = useState<string>('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [selectedPerson, setSelectedPerson] = useState<string | null>(null)

  const treeData: DataNode[] = useMemo(
    () => [
      {
        key: 'all',
        title: COMPANY_NAME,
        children: initialTree.map((node) => ({
          key: node.id,
          title: node.name,
          children: (node.children ?? []).map((child) => ({ key: child.id, title: child.name })),
        })),
      },
    ],
    [initialTree]
  )

  const isInitialQuery =
    selectedDepartment === null && status === '' && deferredKeyword === '' && page === 1 && pageSize === 20

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
  const lastSyncedAt = data?.last_synced_at ?? initialLastSyncedAt

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
    setSelectedDepartment(!key || key === 'all' ? null : String(key))
    setPage(1)
  }

  return (
    <div className="flex gap-5">
      <div className="w-[260px] shrink-0 rounded-[10px] border border-[#e5e3df] bg-white p-3">
        <div className="mb-2 text-[12px] font-semibold tracking-wide text-[#a4a097]">组织架构</div>
        <Tree
          blockNode
          defaultExpandAll
          treeData={treeData}
          selectedKeys={[selectedDepartment ?? 'all']}
          onSelect={handleDepartmentSelect}
        />
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="m-0 text-[22px] font-semibold text-[#37352f]">员工档案</h1>
              <Tag color="default" variant="filled">
                只读
              </Tag>
            </div>
            <div className="mt-1 text-[12.5px] text-[#a4a097]">
              来自飞书通讯录 · 共 {total} 人 · 上次同步 {lastSyncedAt ? dayjs(lastSyncedAt).format('YYYY-MM-DD HH:mm') : '—'}
            </div>
          </div>
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

        <div className="overflow-hidden rounded-[10px] border border-[#e5e3df] bg-white">
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
