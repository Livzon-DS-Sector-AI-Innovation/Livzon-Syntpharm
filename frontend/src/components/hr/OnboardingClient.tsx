'use client'

import { useMemo, useState } from 'react'
import { Button } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { EyeOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchOnboardingRecords } from '@/lib/api/client/hr'
import type { OnboardingRecord, OnboardingRecordListResponse } from '@/types/hr'
import OnboardingRecordDetailDrawer from './OnboardingRecordDetailDrawer'
import OnboardingRecordFormDrawer from './OnboardingRecordFormDrawer'
import LedgerTableShell from './LedgerTableShell'

interface OnboardingClientProps {
  initialRecords: OnboardingRecord[]
  initialTotal: number
}

const QUERY_KEY = 'hr-onboarding-records'

export default function OnboardingClient({ initialRecords, initialTotal }: OnboardingClientProps) {
  const queryClient = useQueryClient()
  const [keyword, setKeyword] = useState('')
  const [department, setDepartment] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [detailRecord, setDetailRecord] = useState<OnboardingRecord | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<OnboardingRecord | null>(null)

  const initialData = useMemo<OnboardingRecordListResponse | undefined>(() => {
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
      fetchOnboardingRecords({
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

  const openEdit = (record: OnboardingRecord) => {
    setEditingRecord(record)
    setFormOpen(true)
  }

  const columns: ColumnsType<OnboardingRecord> = [
    {
      title: '流水号',
      dataIndex: 'serial_no',
      key: 'serial_no',
      width: 110,
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 140,
      render: (name: string) => <span className="font-medium">{name}</span>,
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
      title: '入职类别',
      dataIndex: 'join_category',
      key: 'join_category',
      width: 130,
    },
    {
      title: '操作',
      key: 'action',
      width: 130,
      fixed: 'right',
      render: (_: unknown, record: OnboardingRecord) => (
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
    <LedgerTableShell<OnboardingRecord>
      title="入职台账"
      total={total}
      department={department}
      keywordPlaceholder="搜索流水号、姓名、部门、岗位"
      departmentPlaceholder="一级或二级部门筛选"
      onKeywordChange={(value) => {
        setKeyword(value.trim())
        setPage(1)
      }}
      onDepartmentChange={(value) => {
        setDepartment(value)
        setPage(1)
      }}
      columns={columns}
      records={records}
      loading={isFetching}
      page={page}
      pageSize={pageSize}
      onPageChange={(nextPage, nextPageSize) => {
        setPage(nextPage)
        setPageSize(nextPageSize)
      }}
      onCreate={openCreate}
    >
      <OnboardingRecordDetailDrawer
        open={Boolean(detailRecord)}
        record={detailRecord}
        onClose={() => setDetailRecord(null)}
        onEdit={openEdit}
        onDeleted={refresh}
      />

      <OnboardingRecordFormDrawer
        open={formOpen}
        record={editingRecord}
        onClose={() => setFormOpen(false)}
        onSaved={refresh}
      />
    </LedgerTableShell>
  )
}
