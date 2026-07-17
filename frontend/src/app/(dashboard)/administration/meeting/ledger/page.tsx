'use client'

import { useState, useEffect } from 'react'
import { Table, Button, Input, Tag, Space, Modal, Form, message, Popconfirm, Select } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import { fetchGiftInventories, createGiftInventory, updateGiftInventory, deleteGiftInventory } from '@/lib/api/client/administration/gift-inventory'

const STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '可用', value: '可用' },
  { label: '库存不足', value: '库存不足' },
  { label: '停用', value: '停用' },
]

const STATUS_COLORS: Record<string, string> = {
  '可用': 'success',
  '库存不足': 'warning',
  '停用': 'error',
}

export default function ItemLedgerPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })

  const load = async (page = 1) => {
    setLoading(true)
    try {
      const res = await fetchGiftInventories({
        keyword,
        status: statusFilter || undefined,
        page,
        page_size: pagination.pageSize,
      })
      setData(res.data || [])
      setPagination({ ...pagination, current: page, total: res.meta?.total || 0 })
    } catch (err: any) {
      message.error(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(1) }, [keyword, statusFilter])

  const handleSave = async (values: any) => {
    try {
      if (editing) {
        await updateGiftInventory(editing.id, values)
        message.success('更新成功')
      } else {
        await createGiftInventory(values)
        message.success('创建成功')
      }
      setModalOpen(false)
      form.resetFields()
      setEditing(null)
      load(pagination.current)
    } catch (err: any) {
      message.error(err.message || '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteGiftInventory(id)
      message.success('删除成功')
      load(pagination.current)
    } catch (err: any) {
      message.error(err.message || '删除失败')
    }
  }

  const columns = [
    { title: '物品名称', dataIndex: 'name', key: 'name' },
    { title: '规格', dataIndex: 'specification', key: 'specification' },
    { title: '计量单位', dataIndex: 'unit', key: 'unit', width: 100 },
    { title: '月初库存', dataIndex: 'opening_stock', key: 'opening_stock', width: 100 },
    { title: '本期入库/领用', dataIndex: 'incoming_qty', key: 'incoming_qty', width: 120 },
    { title: '月底库存', dataIndex: 'closing_stock', key: 'closing_stock', width: 100 },
    { title: '单价', dataIndex: 'unit_price', key: 'unit_price', width: 100, render: (v: number) => v?.toFixed(2) },
    { title: '金额', dataIndex: 'total_amount', key: 'total_amount', width: 100, render: (v: number) => v?.toFixed(2) },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => <Tag color={STATUS_COLORS[status] || 'default'}>{status}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: any, record: any) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => {
              setEditing(record)
              form.setFieldsValue(record)
              setModalOpen(true)
            }}
          >
            编辑
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button icon={<DeleteOutlined />} size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold mb-4">物品台账</h1>
      <div className="flex flex-wrap gap-2 mb-4">
        <Input
          placeholder="搜索物品名称"
          prefix={<SearchOutlined />}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => load(1)}
          style={{ width: 280 }}
        />
        <Select
          placeholder="选择状态"
          options={STATUS_OPTIONS}
          value={statusFilter}
          onChange={(value) => setStatusFilter(value)}
          style={{ width: 140 }}
          allowClear
        />
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditing(null)
            form.resetFields()
            setModalOpen(true)
          }}
        >
          新增物品
        </Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{
          ...pagination,
          onChange: (page) => load(page),
        }}
      />
      <Modal
        open={modalOpen}
        title={editing ? '编辑物品' : '新增物品'}
        onCancel={() => {
          setModalOpen(false)
          setEditing(null)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="name" label="物品名称" rules={[{ required: true, message: '请输入物品名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="specification" label="规格">
            <Input />
          </Form.Item>
          <Form.Item name="unit" label="计量单位">
            <Input placeholder="如：支、瓶、箱" />
          </Form.Item>
          <Form.Item name="opening_stock" label="月初库存" rules={[{ required: true, message: '请输入月初库存' }]}>
            <Input type="number" min={0} />
          </Form.Item>
          <Form.Item name="incoming_qty" label="本期入库/领用数量">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="closing_stock" label="月底库存" rules={[{ required: true, message: '请输入月底库存' }]}>
            <Input type="number" min={0} />
          </Form.Item>
          <Form.Item name="unit_price" label="单价">
            <Input type="number" min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="total_amount" label="金额">
            <Input type="number" min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="可用">
            <Input placeholder="可用 / 库存不足 / 停用" />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
