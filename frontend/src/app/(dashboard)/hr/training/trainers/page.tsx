'use client'
import { uploadTrainers } from '@/actions/hr'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { App, Button, Card, Table, Input, Select, Space, Tag, Upload } from 'antd'
import { SearchOutlined, UploadOutlined } from '@ant-design/icons'
import { apiGet, fetchApi } from '@/lib/api/client'

interface Trainer {
  id: string
  name: string
  department: string
  trainable_departments: string[]
  qualification_scope: string
  admin: string
  is_level1: boolean
}

export default function TrainersPage() {
  const { message } = App.useApp()
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [dept, setDept] = useState<string | undefined>()

  const { data: deptsData } = useQuery({
    queryKey: ['hr-departments'],
    queryFn: async () => {
      const data = await apiGet<string[]>('/api/v1/hr/sop-catalog/departments')
      return (data || []).map((d: string) => ({ value: d, label: d }))
    },
  })

  const depts = deptsData || []

  const { data: trainersData, isLoading, refetch } = useQuery({
    queryKey: ['hr-trainers', { page, keyword, dept }],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: '50' })
      if (keyword) params.set('keyword', keyword)
      if (dept) params.set('department', dept)
      const d = await fetchApi<{ data: Trainer[]; meta?: { total?: number; page?: number; page_size?: number } }>(`/api/v1/hr/trainers?${params.toString()}`)
      return { data: d.data || [], total: d.meta?.total || 0 }
    },
  })

  const data = trainersData?.data || []
  const total = trainersData?.total || 0

  const load = (p = 1) => {
    setPage(p)
    refetch()
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-[22px] font-semibold">内训师台账</h1>
        <Upload accept=".xlsx,.xls" showUploadList={false} customRequest={async ({ file }) => {
          try {
            const d = await uploadTrainers(file as File)
            message.success(`上传完成：新增${d.data.created}，更新${d.data.updated}`)
            load(1)
          } catch { message.error('上传失败') }
        }}>
          <Button icon={<UploadOutlined />}>上传内训师</Button>
        </Upload>
      </div>
      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input prefix={<SearchOutlined />} placeholder="搜索姓名" value={keyword}
            onChange={e => setKeyword(e.target.value)} onPressEnter={() => load(1)} style={{ width: 200 }} />
          <Select placeholder="部门" allowClear value={dept} onChange={v => { setDept(v); setPage(1) }}
            options={depts} style={{ width: 200 }} />
        </Space>
        <Table dataSource={data} rowKey="id" loading={isLoading}
          pagination={{ current: page, pageSize: 50, total, onChange: p => setPage(p) }}
          columns={[
            { title: '姓名', dataIndex: 'name', width: 100 },
            { title: '部门', dataIndex: 'department', width: 150 },
            { title: '可培训部门', dataIndex: 'trainable_departments', width: 150 },
            { title: '资格范围', dataIndex: 'qualification_scope', width: 250, ellipsis: true },
            { title: '培训管理员', dataIndex: 'admin', width: 100 },
            { title: '一级培训师', dataIndex: 'is_level1', width: 120,
              render: (v: boolean) => v ? <Tag color="blue">一级培训师</Tag> : <Tag>-</Tag> },
          ]} />
      </Card>
    </div>
  )
}
