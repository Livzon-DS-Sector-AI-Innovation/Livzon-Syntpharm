'use client'
import { uploadSopCatalog } from '@/actions/hr'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Table, Input, Select, Card, Space, Upload, Button, App } from 'antd'
import { SearchOutlined, UploadOutlined } from '@ant-design/icons'
import { fetchSopCatalog } from '@/lib/api/client/hr'
import { apiGet } from '@/lib/api/client'

interface SopCatalogItem {
  id: string
  file_name: string
  sop_number: string
  category: string
  department: string
}

export default function SopCatalogPage() {
  const { message } = App.useApp()
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [dept, setDept] = useState<string | undefined>()
  const [cat, setCat] = useState<string | undefined>()

  const { data: deptsData } = useQuery({
    queryKey: ['hr-sop-departments'],
    queryFn: async () => {
      const data = await apiGet<string[]>('/api/v1/hr/sop-catalog/departments')
      return (data || []).map((d: string) => ({ value: d, label: d }))
    },
  })

  const departments = deptsData || []

  // 分类列表（按部门筛选，级联）
  const { data: catsData } = useQuery({
    queryKey: ['hr-sop-categories', dept],
    queryFn: async () => {
      const url = dept
        ? `/api/v1/hr/sop-catalog/categories?department=${encodeURIComponent(dept)}`
        : '/api/v1/hr/sop-catalog/categories'
      const data = await apiGet<string[]>(url)
      return (data || []).map((c: string) => ({ value: c, label: c }))
    },
  })

  const categories = catsData || []

  const { data: catalogData, isLoading, refetch } = useQuery({
    queryKey: ['hr-sop-catalog', { page, keyword, dept, cat }],
    queryFn: async () => {
      const res = await fetchSopCatalog({ page, page_size: 50, keyword: keyword || undefined, department: dept, category: cat })
      return { data: res.data || [], total: res.meta?.total || 0 }
    },
  })

  const data = catalogData?.data || []
  const total = catalogData?.total || 0

  const load = (p = 1) => {
    setPage(p)
    refetch()
  }

  const columns = [
    { title: '文件名称', dataIndex: 'file_name', width: 350, fixed: 'left' as const, ellipsis: true },
    { title: 'SOP编号', dataIndex: 'sop_number', width: 150 },
    { title: '培训类别', dataIndex: 'category', width: 200 },
    { title: '所属部门', dataIndex: 'department', width: 180 },
  ]

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-[22px] font-semibold">SOP 目录</h1>
        <Upload accept=".xlsx,.xls" showUploadList={false} customRequest={async ({ file }) => {
          try {
            const d = await uploadSopCatalog(file as File)
            message.success(`上传完成：新增${d.data.created}，更新${d.data.updated}`)
            load(1)
          } catch { message.error('上传失败') }
        }}>
          <Button icon={<UploadOutlined />}>上传SOP目录</Button>
        </Upload>
      </div>
      <Card>
        <Space className="mb-4" wrap>
          <Input prefix={<SearchOutlined />} placeholder="搜索文件名称" value={keyword}
            onChange={e => setKeyword(e.target.value)} onPressEnter={() => load(1)} style={{ width: 260 }} />
          <Select placeholder="筛选部门" allowClear value={dept} onChange={v => { setDept(v); setCat(undefined); setPage(1) }}
            options={departments} style={{ width: 200 }} />
          <Select placeholder="筛选类别" allowClear value={cat} onChange={v => { setCat(v); setPage(1) }}
            options={categories} style={{ width: 240 }} />
        </Space>
        <Table columns={columns} dataSource={data} rowKey="id" loading={isLoading} scroll={{ x: 900 }}
          pagination={{ current: page, pageSize: 50, total, onChange: (p) => setPage(p), showSizeChanger: false }} />
      </Card>
    </div>
  )
}
