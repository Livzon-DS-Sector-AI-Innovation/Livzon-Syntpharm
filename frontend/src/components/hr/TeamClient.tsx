'use client'

import { useState } from 'react'
import { App, Button, Table, Space, Popconfirm, Input } from 'antd'
import { PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Team } from '@/types/hr'
import { fetchTeamsAction, deleteTeam } from '@/actions/hr'
import TeamForm from './TeamForm'

interface TeamClientProps {
  departmentId: string
  departmentName: string
}

export default function TeamClient({ departmentId, departmentName }: TeamClientProps) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [formOpen, setFormOpen] = useState(false)
  const [editingTeam, setEditingTeam] = useState<Team | null>(null)
  const [searchKeyword, setSearchKeyword] = useState('')

  const { data, isLoading: loading } = useQuery({
    queryKey: ['hr-teams', { departmentId, searchKeyword, page, pageSize }],
    queryFn: async () => {
      const res = await fetchTeamsAction({
        department_id: departmentId,
        keyword: searchKeyword || undefined,
        page,
        page_size: pageSize })
      return { teams: res.data, total: res.meta?.total || 0 }
    },
  })

  const teams = data?.teams || []
  const total = data?.total || 0

  const handlePageChange = (newPage: number, newPageSize: number) => {
    setPage(newPage)
    setPageSize(newPageSize)
  }

  const handleEdit = (team: Team) => {
    setEditingTeam(team)
    setFormOpen(true)
  }

  const handleAdd = () => {
    setEditingTeam(null)
    setFormOpen(true)
  }

  const handleFormSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['hr-teams'] })
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteTeam(id)
      message.success('删除成功')
      queryClient.invalidateQueries({ queryKey: ['hr-teams'] })
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const columns = [
    {
      title: '班组名称',
      dataIndex: 'name',
      key: 'name',
      width: 160 },
    {
      title: '班组编码',
      dataIndex: 'code',
      key: 'code',
      width: 120 },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: unknown, record: Team) => (
        <Space size="small">
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
            description={`确定要删除班组 ${record.name} 吗？`}
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
      ) },
  ]

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-[var(--color-charcoal)]">
          {departmentName} — 班组管理
        </h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增班组
        </Button>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <Input
          placeholder="搜索班组名称或编码"
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          prefix={<SearchOutlined />}
          className="w-64"
          allowClear
        />
      </div>

      <Table
        columns={columns}
        dataSource={teams}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: handlePageChange }}
      />

      <TeamForm
        open={formOpen}
        team={editingTeam}
        departmentId={departmentId}
        onClose={() => setFormOpen(false)}
        onSuccess={handleFormSuccess}
      />
    </div>
  )
}
