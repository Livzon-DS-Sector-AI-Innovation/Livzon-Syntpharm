'use client'

import { useMemo, useState } from 'react'
import { Avatar, Button, Input, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchDepartureRecords } from '@/lib/api/client/hr'
import type { DepartureRecord, DepartureRecordListResponse } from '@/types/hr'
import DepartureRecordDetailDrawer from './DepartureRecordDetailDrawer'
import DepartureRecordFormDrawer from './DepartureRecordFormDrawer'
import { avatarColor } from './onboardingOptions'

interface DepartureClientProps {
  initialRecords: DepartureRecord[]
  initialTotal: number
}

const QUERY_KEY = 'hr-departure-records'

export default function DepartureClient({ initialRecords, initialTotal }: DepartureClientProps) {
  const queryClient = useQueryClient()
  const [keyword, setKeyword] = useState('')
  const [department, setDepartment] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [detailRecord, setDetailRecord] = useState<DepartureRecord | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<DepartureRecord | null>(null)

  const initialData = useMemo<DepartureRecordListResponse | undefined>(() => {
    if (keyword || department || page !== 1 || pageSize !== 20) return undefined
    return {
      code: 200,
      message: 'success',
      data: initialRecords,
      meta: { page: 1, page_size: 20, total: initialTotal },
    }
  }, [keyword, department, page, pageSize, initialRecords, initialTotal])

  const { data, isFetching } = useQuery({
    queryKey: [QUERY_KEY, { keyword, department, page, pageSize }],
    queryFn: () =>
      fetchDepartureRecords({
        keyword: keyword || undefined,
        department: department || undefined,
        page,
        page_size: pageSize,
      }),
    initialData,
    staleTime: 0,
  })

  const records = data?.data ?? []
  const total = typeof data?.meta?.total === 'number' ? data.meta.total : 0

  const refresh = () => queryClient.invalidateQueries({ queryKey: [QUERY_KEY] })

  const openCreate = () => {
    setEditingRecord(null)
    setFormOpen(true)
  }

  const openEdit = (record: DepartureRecord) => {
    setEditingRecord(record)
    setFormOpen(true)
  }

  const columns: ColumnsType<DepartureRecord> = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string) => (
        <span className="flex items-center gap-2">
          <Avatar size={28} style={{ backgroundColor: avatarColor(name), fontSize: 12 }}>
            {name.slice(0, 1)}
          </Avatar>
          <span className="font-medium">{name}</span>
        </span>
      ),
    },
    {
      title: '一级部门',
      dataIndex: 'department_level1',
      key: 'department_level1',
      width: 170,
    },
    {
      title: '二级部门',
      dataIndex: 'department_level2',
      key: 'department_level2',
      width: 150,
    },
    {
      title: '岗位',
      dataIndex: 'position',
      key: 'position',
      width: 140,
    },
    {
      title: '入职日期',
      dataIndex: 'hire_date',
      key: 'hire_date',
      width: 120,
    },
    {
      title: '离职日期',
      dataIndex: 'leave_date',
      key: 'leave_date',
      width: 120,
    },
    {
      title: '司龄',
      dataIndex: 'tenure_years',
      key: 'tenure_years',
      width: 100,
      render: (value: number) => `${Number(value).toFixed(1)} 年`,
    },
    {
      title: '操作',
      key: 'action',
      width: 130,
      fixed: 'right',
      render: (_: unknown, record: DepartureRecord) => (
        <div className="flex gap-1">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => setDetailRecord(record)}>
            查看
          </Button>
          <Button type="link" size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="m-0 text-[22px] font-semibold text-[#37352f]">离职台账</h1>
          <div className="mt-1 text-[12.5px] text-[#a4a097]">共 {total} 条</div>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Input.Search
          placeholder="搜索姓名、部门、岗位"
          allowClear
          onSearch={(value) => {
            setKeyword(value.trim())
            setPage(1)
          }}
          onChange={(event) => {
            if (!event.target.value) {
              setKeyword('')
              setPage(1)
            }
          }}
          className="w-72"
        />
        <Input
          placeholder="一级或二级部门筛选"
          allowClear
          prefix={<SearchOutlined />}
          value={department}
          onChange={(event) => {
            setDepartment(event.target.value)
            setPage(1)
          }}
          className="w-56"
        />
      </div>

      <div className="overflow-hidden rounded-[10px] border border-[#e5e3df] bg-white">
        <Table<DepartureRecord>
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={isFetching}
          size="middle"
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (count) => `共 ${count} 条`,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage)
              setPageSize(nextPageSize)
            },
          }}
          scroll={{ x: 1150 }}
        />
      </div>

      <DepartureRecordDetailDrawer
        open={Boolean(detailRecord)}
        record={detailRecord}
        onClose={() => setDetailRecord(null)}
        onEdit={openEdit}
        onDeleted={refresh}
      />

      <DepartureRecordFormDrawer
        open={formOpen}
        record={editingRecord}
        onClose={() => setFormOpen(false)}
        onSaved={refresh}
      />
    </div>
  )
}
