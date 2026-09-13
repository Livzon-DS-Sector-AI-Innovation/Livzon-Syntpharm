'use client'

import { useState } from 'react'
import { useRouter } from "next/navigation"
import { Button, message, Table, Space, Popconfirm, Input, Modal } from 'antd'
import { PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined, TeamOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Department } from '@/types/hr'
import { fetchDepartmentsAction, deleteDepartment } from '@/actions/hr'
import { fetchNewDepartments } from '@/lib/api/client/hr'
import DepartmentForm from './DepartmentForm'
import TeamClient from './TeamClient'

interface DepartmentClientProps {
  initialDepartments: Department[]
  initialTotal: number
  factory?: 'new'
}

export default function DepartmentClient({
  initialDepartments,
  initialTotal,
  factory,
}: DepartmentClientProps) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [formOpen, setFormOpen] = useState(false)
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null)
  const [searchKeyword, setSearchKeyword] = useState('')
  const _router = useRouter()
  const queryClient = useQueryClient()
  const [teamModalOpen, setTeamModalOpen] = useState(false)
  const [selectedDepartment, setSelectedDepartment] = useState<Department | null>(null)

  const doFetch = factory === 'new' ? fetchNewDepartments : fetchDepartmentsAction

  const { data, isLoading: loading } = useQuery({
    queryKey: ['hr-departments', { factory, searchKeyword, page, pageSize }],
    queryFn: async () => {
      const res = await doFetch({
        keyword: searchKeyword || undefined,
        page,
        page_size: pageSize,
      })
      return { departments: res.data, total: res.meta?.total || 0 }
    },
  })

  const departments = data?.departments || initialDepartments
  const total = data?.total || initialTotal

  const handlePageChange = (newPage: number, newPageSize: number) => {
    setPage(newPage)
    setPageSize(newPageSize)
  }

  const handleEdit = (department: Department) => {
    setEditingDepartment(department)
    setFormOpen(true)
  }

  const handleAdd = () => {
    setEditingDepartment(null)
    setFormOpen(true)
  }

  const handleFormSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['hr-departments'] })
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteDepartment(id)
      message.success('删除成功')
      queryClient.invalidateQueries({ queryKey: ['hr-departments'] })
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleOpenTeams = (department: Department) => {
    setSelectedDepartment(department)
    setTeamModalOpen(true)
  }

  const columns = [
    {
      title: '部门编码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: '部门名称',
      dataIndex: 'name',
      key: 'name',
      width: 160,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: unknown, record: Department) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<TeamOutlined />}
            onClick={() => handleOpenTeams(record)}
          >
            班组
          </Button>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除部门 ${record.name} 吗？`}
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">
          {factory === 'new' ? '新厂部门管理' : '老厂部门管理'}
        </h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增部门
        </Button>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <Input
          placeholder="搜索部门名称或编码"
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          prefix={<SearchOutlined />}
          className="w-64"
          allowClear
        />
      </div>

      <Table
        columns={columns}
        dataSource={departments}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: handlePageChange,
        }}
      />

      <DepartmentForm
        open={formOpen}
        department={editingDepartment}
        onClose={() => setFormOpen(false)}
        onSuccess={handleFormSuccess}
      />

      <Modal
        open={teamModalOpen}
        onCancel={() => setTeamModalOpen(false)}
        footer={null}
        width={800}
        destroyOnClose
      >
        {selectedDepartment && (
          <TeamClient
            departmentId={selectedDepartment.id}
            departmentName={selectedDepartment.name}
          />
        )}
      </Modal>

    </div>
  )
}
