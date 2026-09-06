'use client'
import { Upload } from "antd"
import { UploadOutlined } from "@ant-design/icons"
import { Select } from "antd"

import { useState, useEffect, useMemo } from 'react'
import { Button, message, Tabs } from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Employee, Department } from '@/types/hr'
import { fetchEmployeesAction, uploadEmployeesAction } from '@/actions/hr'
import { fetchNewEmployees, fetchNewDepartments } from '@/lib/api/client/hr'
import { fetchDepartments } from '@/lib/api/client/hr'
import { useHrStore } from '@/stores/hr'
import EmployeeTable from './EmployeeTable'
import EmployeeForm from './EmployeeForm'
import TurnoverAnalysisPanel from './TurnoverAnalysisPanel'

interface EmployeeProfileClientProps {
  initialEmployees: Employee[]
  initialTotal: number
  initialDepartment?: string
  factory?: 'new'
}

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debouncedValue
}

export default function EmployeeProfileClient({
  initialEmployees,
  initialDepartment,
  initialTotal,
  factory,
}: EmployeeProfileClientProps) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [formOpen, setFormOpen] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null)
  const [activeTab, setActiveTab] = useState('all')
  const queryClient = useQueryClient()

  const { searchKeyword, filterStatus } = useHrStore()
  const debouncedSearchKeyword = useDebounce(searchKeyword, 300)

  const doFetch = factory === 'new' ? fetchNewEmployees : fetchEmployeesAction

  const { data: departments = [] } = useQuery<Department[]>({
    queryKey: ['hr-departments-list', { factory }],
    queryFn: async () => {
      const doFetchDepartments = factory === 'new' ? fetchNewDepartments : fetchDepartments
      const res = await doFetchDepartments({ page_size: 100 })
      return res.data
    },
  })

  const activeDepartment =
    activeTab === 'all'
      ? ''
      : departments.find((d) => d.id === activeTab)?.name || ''

  const { data, isLoading: loading } = useQuery({
    queryKey: ['hr-employees', { factory, debouncedSearchKeyword, activeDepartment, filterStatus, page, pageSize }],
    queryFn: async () => {
      const res = await doFetch({
        keyword: debouncedSearchKeyword || undefined,
        department: activeDepartment || undefined,
        status: filterStatus || undefined,
        page,
        page_size: pageSize,
      })
      return { employees: res.data, total: res.meta?.total || 0 }
    },
  })

  const employees = data?.employees || initialEmployees
  const total = data?.total || initialTotal

  // When initialDepartment is provided, select that department tab (adjusting state during render)
  const [prevInitialDept, setPrevInitialDept] = useState<string | undefined>(undefined)
  if (initialDepartment !== prevInitialDept && initialDepartment && departments.length > 0) {
    setPrevInitialDept(initialDepartment)
    const dept = departments.find((d) => d.name === initialDepartment)
    if (dept) setActiveTab(dept.id)
  }

  const handlePageChange = (newPage: number, newPageSize: number) => {
    setPage(newPage)
    setPageSize(newPageSize)
  }

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['hr-employees'] })
    queryClient.invalidateQueries({ queryKey: ['hr-departments-list'] })
  }

  const handleEdit = (employee: Employee) => {
    setEditingEmployee(employee)
    setFormOpen(true)
  }

  const handleFormSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['hr-employees'] })
  }

  const handleTabChange = (key: string) => {
    setActiveTab(key)
    setPage(1)
  }

  const tabItems = useMemo(
    () => [
      { key: 'all', label: '全部', value: '' },
      ...departments.map((d) => ({ key: d.id, label: d.name, value: d.name })),
    ],
    [departments]
  )

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">
          {factory === 'new' ? '新厂员工档案' : '老厂员工档案'}
        </h1>
        <Upload accept=".xlsx,.xls" showUploadList={false} customRequest={async ({file}) => {
          try {
            const fd = new FormData()
            fd.append('file', file as File)
            const d = await uploadEmployeesAction(fd)
            if (d.code === 0) message.success(`上传完成：新增${d.data.created}，更新${d.data.updated}`)
            else message.error(d.message || '上传失败')
            handleRefresh()
          } catch { message.error('上传失败') }
        }}>
          <Button icon={<UploadOutlined />}>上传人员名单</Button>
        </Upload>
        <Select placeholder="选择部门下载花名册" allowClear style={{ width: 220 }}
          options={departments.map((d: { name: string }) => ({value: d.name, label: d.name}))}
          onChange={async (dept) => {
            if (!dept) return
            
            const deptEncoded = encodeURIComponent(dept)
            window.open(`/api/v1/hr/roster?department=${deptEncoded}`)
          }} />
      </div>

      <TurnoverAnalysisPanel />

      <Tabs activeKey={activeTab} onChange={handleTabChange} type="card">
        {tabItems.map((dept) => (
          <Tabs.TabPane key={dept.key} tab={dept.label}>
            {activeTab === dept.key && (
              <EmployeeTable
                employees={employees}
                total={total}
                page={page}
                pageSize={pageSize}
                onPageChange={handlePageChange}
                onRefresh={handleRefresh}
                onEdit={handleEdit}
              />
            )}
          </Tabs.TabPane>
        ))}
      </Tabs>

      <EmployeeForm
        open={formOpen}
        employee={editingEmployee}
        onClose={() => setFormOpen(false)}
        onSuccess={handleFormSuccess}
      />

    </div>
  )
}
