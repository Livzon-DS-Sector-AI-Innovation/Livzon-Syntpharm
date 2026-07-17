'use client'

import { useState, useEffect } from 'react'
import { Table, Button, Input, Space, Modal, Form, message, Popconfirm } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import { fetchGiftRequisitions, createGiftRequisition, updateGiftRequisition, deleteGiftRequisition } from '@/lib/api/client/administration/gift-requisition'

export default function RequisitionPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [department, setDepartment] = useState('')
  const [itemName, setItemName] = useState('')
  const [recipient, setRecipient] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })

  const load = async (page = 1) => {
    setLoading(true)
    try {
      const res = await fetchGiftRequisitions({
        department: department || undefined,
        item_name: itemName || undefined,
        recipient: recipient || undefined,
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

  useEffect(() => { load(1) }, [])

  const handleSearch = () => {
    load(1)
  }

  const handleSave = async (values: any) => {
    try {
      if (editing) {
        await updateGiftRequisition(editing.id, values)
        message.success('更新成功')
      } else {
        await createGiftRequisition(values)
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
      await deleteGiftRequisition(id)
      message.success('删除成功')
      load(pagination.current)
    } catch (err: any) {
      message.error(err.message || '删除失败')
    }
  }

  const columns = [
    { title: '序号', dataIndex: 'seq_no', key: 'seq_no', width: 80 },
    { title: '费用所属部门', dataIndex: 'department', key: 'department', width: 140 },
    { title: '领用名称', dataIndex: 'item_name', key: 'item_name' },
    { title: '领用单价', dataIndex: 'unit_price', key: 'unit_price', width: 100, render: (v: number) => v?.toFixed(2) },
    { title: '领用数量', dataIndex: 'quantity', key: 'quantity', width: 100 },
    { title: '合计价格', dataIndex: 'total_amount', key: 'total_amount', width: 100, render: (v: number) => v?.toFixed(2) },
    { title: '领用人', dataIndex: 'recipient', key: 'recipient', width: 100 },
    { title: '领用日期', dataIndex: 'requisition_date', key: 'requisition_date', width: 120 },
    { title: '备注', dataIndex: 'remarks', key: 'remarks' },
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
      <h1 className="text-xl font-bold mb-4">领用记录</h1>
      <div className="flex flex-wrap gap-2 mb-4">
        <Input
          placeholder="费用所属部门"
          prefix={<SearchOutlined />}
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 180 }}
        />
        <Input
          placeholder="领用物品名称"
          prefix={<SearchOutlined />}
          value={itemName}
          onChange={(e) => setItemName(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 180 }}
        />
        <Input
          placeholder="领用人"
          prefix={<SearchOutlined />}
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 140 }}
        />
        <Button type="primary" onClick={handleSearch}>
          查询
        </Button>
        <Button onClick={() => { setDepartment(''); setItemName(''); setRecipient(''); load(1); }}>
          重置
        </Button>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditing(null)
            form.resetFields()
            setModalOpen(true)
          }}
        >
          新增领用
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
        title={editing ? '编辑领用记录' : '新增领用记录'}
        onCancel={() => {
          setModalOpen(false)
          setEditing(null)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="seq_no" label="序号">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="department" label="费用所属部门">
            <Input />
          </Form.Item>
          <Form.Item name="item_name" label="领用名称" rules={[{ required: true, message: '请输入领用名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="unit_price" label="领用单价">
            <Input type="number" min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="quantity" label="领用数量">
            <Input type="number" min={0} />
          </Form.Item>
          <Form.Item name="total_amount" label="合计价格">
            <Input type="number" min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="recipient" label="领用人">
            <Input />
          </Form.Item>
          <Form.Item name="requisition_date" label="领用日期">
            <Input placeholder="如：2026.3.1" />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
