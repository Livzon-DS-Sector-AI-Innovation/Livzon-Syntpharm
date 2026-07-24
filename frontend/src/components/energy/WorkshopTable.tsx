'use client'

import { useCallback, useEffect, useState } from 'react'
import { App, Table, Button, Space, Select } from 'antd'
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import type { TableColumnsType } from 'antd'
import type { EnergyWorkshop, WorkshopCategory } from '@/types/energy'
import { getWorkshops, deleteWorkshopAction } from '@/actions/energy'
import { WorkshopDrawer } from './WorkshopDrawer'

const luxuryPill = (color: string, bg: string) =>
  ({
    display: 'inline-flex',
    alignItems: 'center',
    padding: '2px 12px',
    borderRadius: 9999,
    fontSize: 12,
    fontWeight: 500,
    lineHeight: '20px',
    color,
    background: bg,
  } as const)

const categoryConfig: Record<WorkshopCategory, { label: string; pill: ReturnType<typeof luxuryPill> }> = {
  workshop: { label: '生产车间', pill: luxuryPill('#0075de', '#dcecfa') },
  position: { label: '岗位', pill: luxuryPill('#dd5b00', '#ffe8d4') },
  support: { label: '辅助部门', pill: luxuryPill('#787671', '#f0eeec') },
  utility: { label: '动力设施', pill: luxuryPill('#1aae39', '#d9f3e1') },
}

const activePill = luxuryPill('#1aae39', '#d9f3e1')
const inactivePill = luxuryPill('#787671', '#f0eeec')

const tableStyles = `
.luxury-workshop-table .ant-table-thead > tr > th {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #a4a097;
  background: #fafaf9;
  border-bottom: 1px solid #ede9e4;
  padding: 10px 16px;
  font-weight: 600;
}
.luxury-workshop-table .ant-table-thead > tr > th::before {
  display: none;
}
.luxury-workshop-table .ant-table-tbody > tr > td {
  border-bottom: 1px solid #ede9e4;
  border-inline-end: none;
  padding: 12px 16px;
  font-size: 14px;
  color: #37352f;
}
.luxury-workshop-table .ant-table-tbody > tr > td:last-child {
  border-inline-end: none;
}
.luxury-workshop-table .ant-table-tbody > tr:hover > td {
  background: #f6f3ff !important;
}
.luxury-workshop-table .ant-table-tbody > tr:hover > td:first-child {
  box-shadow: inset 2px 0 0 #5645d4;
}
.luxury-workshop-table .ant-table {
  border-inline-start: none !important;
  border-inline-end: none !important;
}
.luxury-workshop-table .ant-table-container {
  border-inline-start: none !important;
  border-inline-end: none !important;
}
`

const actionLink = {
  cursor: 'pointer' as const,
  color: '#5645d4',
  fontSize: 13,
  fontWeight: 500,
  padding: '0 4px',
}

export function WorkshopTable() {
  const { message, modal } = App.useApp()
  const [workshops, setWorkshops] = useState<EnergyWorkshop[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [categoryFilter, setCategoryFilter] = useState<WorkshopCategory | undefined>()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const result: any = await getWorkshops({
        category: categoryFilter,
        page,
        page_size: pageSize,
      })
      setWorkshops(result.items || [])
      setTotal(result.total || 0)
    } catch (error) {
      message.error('加载车间列表失败')
    } finally {
      setLoading(false)
    }
  }, [categoryFilter, page, pageSize, message])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleDelete = (record: EnergyWorkshop) => {
    modal.confirm({
      title: '确认删除',
      content: `确定要删除车间「${record.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteWorkshopAction(record.id)
          message.success('删除成功')
          loadData()
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const handleEdit = (id: string) => {
    setEditingId(id)
    setDrawerOpen(true)
  }

  const handleCreate = () => {
    setEditingId(null)
    setDrawerOpen(true)
  }

  const handleDrawerClose = () => {
    setDrawerOpen(false)
    setEditingId(null)
  }

  const columns: TableColumnsType<EnergyWorkshop> = [
    {
      title: '编码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: WorkshopCategory) => {
        const config = categoryConfig[category]
        return <span style={config?.pill}>{config?.label || category}</span>
      },
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean) => (
        <span style={active ? activePill : inactivePill}>
          {active ? '启用' : '停用'}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <span style={actionLink} onClick={() => handleEdit(record.id)}>
            <EditOutlined /> 编辑
          </span>
          <span
            style={{ ...actionLink, color: '#e03131' }}
            onClick={() => handleDelete(record)}
          >
            <DeleteOutlined /> 删除
          </span>
        </Space>
      ),
    },
  ]

  return (
    <>
      <style>{tableStyles}</style>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Select
            placeholder="按分类筛选"
            allowClear
            style={{ width: 150 }}
            value={categoryFilter}
            onChange={(val) => {
              setCategoryFilter(val)
              setPage(1)
            }}
            options={[
              { value: 'workshop', label: '生产车间' },
              { value: 'position', label: '岗位' },
              { value: 'support', label: '辅助部门' },
              { value: 'utility', label: '动力设施' },
            ]}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新增车间
        </Button>
      </div>
      <Table
        className="luxury-workshop-table"
        columns={columns}
        dataSource={workshops}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
      />
      <WorkshopDrawer
        open={drawerOpen}
        workshopId={editingId}
        onClose={handleDrawerClose}
        onSuccess={() => {
          handleDrawerClose()
          loadData()
        }}
      />
    </>
  )
}
