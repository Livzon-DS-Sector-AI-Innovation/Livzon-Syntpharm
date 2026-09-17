'use client'

import { useCallback, useEffect } from 'react'
import { App, Table, Tag, Space, Button, Input, Modal, Form, Select } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { DepartmentContact } from '@/types/quality'
import { useDepartmentContactStore } from '@/stores/quality'
import { fetchDepartmentContacts } from '@/lib/api/client/quality'
import { createDepartmentContact, updateDepartmentContact, deleteDepartmentContact } from '@/actions/quality'
import { useState } from 'react'

export function DepartmentContactPage() {
  const { message, modal } = App.useApp()
  const {
    contacts,
    total,
    loading,
    page,
    pageSize,
    setContacts,
    setTotal,
    setLoading,
    setPage,
    setPageSize,
  } = useDepartmentContactStore()

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingContact, setEditingContact] = useState<DepartmentContact | null>(null)
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await fetchDepartmentContacts(page, pageSize)
      setContacts(result.items)
      setTotal(result.total)
    } catch (error) {
      console.warn('加载部门联系人数据失败:', error)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, setContacts, setTotal, setLoading])

  useEffect(() => {
    loadData()
  }, [loadData])

  const openDrawer = (contact?: DepartmentContact) => {
    if (contact) {
      setEditingContact(contact)
      form.setFieldsValue({
        department: contact.department,
        dept_head_id: contact.dept_head_id || undefined,
        qa_staff_ids: contact.qa_staff_ids || [],
        gmp_staff_ids: contact.gmp_staff_ids || [],
        production_head_id: contact.production_head_id || undefined,
        quality_head_id: contact.quality_head_id || undefined,
        additional_contacts: contact.additional_contacts || [],
      })
    } else {
      setEditingContact(null)
      form.resetFields()
    }
    setDrawerOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)
      if (editingContact) {
        await updateDepartmentContact(editingContact.id, values)
        message.success('更新成功')
      } else {
        await createDepartmentContact(values)
        message.success('创建成功')
      }
      setDrawerOpen(false)
      loadData()
    } catch (error: any) {
      if (error?.message) message.error(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = (record: DepartmentContact) => {
    modal.confirm({
      title: '确认删除',
      content: `确定要删除部门 "${record.department}" 的联系人配置吗？`,
      okText: '确认',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteDepartmentContact(record.id)
          message.success('删除成功')
          loadData()
        } catch (error: any) {
          message.error(error?.message || '删除失败')
        }
      },
    })
  }

  const columns = [
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      width: 150,
    },
    {
      title: '部门负责人',
      dataIndex: 'dept_head_id',
      key: 'dept_head_id',
      width: 120,
      render: (v: string | null) => v ? <Tag>{v.slice(0, 8)}...</Tag> : '-',
    },
    {
      title: '生产负责人',
      dataIndex: 'production_head_id',
      key: 'production_head_id',
      width: 120,
      render: (v: string | null) => v ? <Tag>{v.slice(0, 8)}...</Tag> : '-',
    },
    {
      title: '质量负责人',
      dataIndex: 'quality_head_id',
      key: 'quality_head_id',
      width: 120,
      render: (v: string | null) => v ? <Tag>{v.slice(0, 8)}...</Tag> : '-',
    },
    {
      title: 'QA人员',
      dataIndex: 'qa_staff_ids',
      key: 'qa_staff_ids',
      width: 150,
      render: (ids: string[] | null) => ids && ids.length > 0 ? `${ids.length}人` : '-',
    },
    {
      title: 'GMP人员',
      dataIndex: 'gmp_staff_ids',
      key: 'gmp_staff_ids',
      width: 150,
      render: (ids: string[] | null) => ids && ids.length > 0 ? `${ids.length}人` : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: unknown, record: DepartmentContact) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openDrawer(record)} style={{ padding: 0 }}>
            编辑
          </Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)} style={{ padding: 0 }}>
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>部门联系人配置</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openDrawer()}>
          添加部门
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={contacts}
        rowKey="id"
        size="small"
        loading={loading}
        scroll={{ x: 'max-content' }}
        pagination={{
          current: page,
          pageSize: pageSize,
          total: total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (newPage, newPageSize) => {
            setPage(newPage)
            setPageSize(newPageSize)
          },
        }}
      />
      <Modal
        title={editingContact ? '编辑部门联系人' : '添加部门联系人'}
        open={drawerOpen}
        onOk={handleSubmit}
        onCancel={() => setDrawerOpen(false)}
        confirmLoading={submitting}
        width={600}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="department" label="部门名称" rules={[{ required: true, message: '请输入部门名称' }]}>
            <Input disabled={!!editingContact} placeholder="请输入部门名称" />
          </Form.Item>
          <Form.Item name="dept_head_id" label="部门负责人ID">
            <Input placeholder="请输入用户ID" />
          </Form.Item>
          <Form.Item name="production_head_id" label="生产负责人ID">
            <Input placeholder="请输入用户ID" />
          </Form.Item>
          <Form.Item name="quality_head_id" label="质量负责人ID">
            <Input placeholder="请输入用户ID" />
          </Form.Item>
          <Form.Item name="qa_staff_ids" label="QA人员ID列表">
            <Select mode="tags" placeholder="输入用户ID后按回车添加" />
          </Form.Item>
          <Form.Item name="gmp_staff_ids" label="GMP人员ID列表">
            <Select mode="tags" placeholder="输入用户ID后按回车添加" />
          </Form.Item>
          <Form.Item name="additional_contacts" label="其他联系人ID列表">
            <Select mode="tags" placeholder="输入用户ID后按回车添加" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
