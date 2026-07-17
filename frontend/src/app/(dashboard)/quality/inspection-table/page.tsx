'use client'

import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Tag,
  message,
  Modal,
  Form,
  Popconfirm,
  Spin,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  TableOutlined,
} from '@ant-design/icons'
import Link from 'next/link'
import dayjs from 'dayjs'
import {
  getInspectionTables,
  createInspectionTable,
  deleteInspectionTable,
  updateInspectionTable,
} from '@/actions/inspection-table'
import type { TableListItem, ColumnConfig } from '@/types/inspection-table'

export default function InspectionTableListPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<TableListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [selectedTable, setSelectedTable] = useState<TableListItem | null>(null)
  const [columnsModalVisible, setColumnsModalVisible] = useState(false)
  const [columns, setColumns] = useState<ColumnConfig[]>([])
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const result = await getInspectionTables({
        keyword: keyword || undefined,
        page,
        page_size: pageSize,
      })
      setData(result.data?.items || [])
      setTotal(result.data?.total || 0)
    } catch (error) {
      message.error('获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [page, pageSize, keyword])

  // 创建数据表
  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      await createInspectionTable({
        table_name: values.table_name,
        table_description: values.table_description,
        columns_config: columns,
      })

      message.success('创建成功')
      setCreateModalVisible(false)
      form.resetFields()
      setColumns([])
      fetchData()
    } catch (error: any) {
      message.error(error.message || '创建失败')
    } finally {
      setSaving(false)
    }
  }

  // 编辑数据表
  const handleEdit = (record: TableListItem) => {
    setSelectedTable(record)
    editForm.setFieldsValue({
      table_name: record.table_name,
      table_description: record.table_description,
    })
    setEditModalVisible(true)
  }

  const handleUpdate = async () => {
    try {
      const values = await editForm.validateFields()
      if (!selectedTable) return

      setSaving(true)
      await updateInspectionTable(selectedTable.id, {
        table_name: values.table_name,
        table_description: values.table_description,
      })

      message.success('更新成功')
      setEditModalVisible(false)
      fetchData()
    } catch (error: any) {
      message.error(error.message || '更新失败')
    } finally {
      setSaving(false)
    }
  }

  // 删除数据表
  const handleDelete = async (id: string) => {
    try {
      await deleteInspectionTable(id)
      message.success('删除成功')
      fetchData()
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  // 添加列
  const handleAddColumn = () => {
    const newColumn: ColumnConfig = {
      key: `col_${Date.now()}`,
      label: `列${columns.length + 1}`,
      type: 'text',
    }
    setColumns([...columns, newColumn])
  }

  // 更新列配置
  const handleUpdateColumn = (index: number, field: string, value: any) => {
    const newColumns = [...columns]
    newColumns[index] = { ...newColumns[index], [field]: value }
    setColumns(newColumns)
  }

  // 删除列
  const handleDeleteColumn = (index: number) => {
    setColumns(columns.filter((_, i) => i !== index))
  }

  const columns_list: ColumnsType<TableListItem> = [
    {
      title: '数据表名称',
      dataIndex: 'table_name',
      key: 'table_name',
    },
    {
      title: '描述',
      dataIndex: 'table_description',
      key: 'table_description',
      ellipsis: true,
    },
    {
      title: '数据行数',
      dataIndex: 'row_count',
      key: 'row_count',
      width: 100,
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (is_active: boolean) => (
        <Tag color={is_active ? 'green' : 'default'}>
          {is_active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space>
          <Link href={`/quality/inspection-table/${record.id}`}>
            <Button type="link" size="small" icon={<EyeOutlined />}>
              查看
            </Button>
          </Link>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除该数据表吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="原料检验数据表"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            新建数据表
          </Button>
        }
      >
        {/* 搜索 */}
        <div style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜索数据表名称"
            style={{ width: 300 }}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            allowClear
          />
        </div>

        {/* 表格 */}
        <Table
          columns={columns_list}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            total,
            current: page,
            pageSize,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
          }}
        />
      </Card>

      {/* 创建数据表弹窗 */}
      <Modal
        title="新建数据表"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          form.resetFields()
          setColumns([])
        }}
        onOk={handleCreate}
        confirmLoading={saving}
        okText="创建"
        cancelText="取消"
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="table_name"
            label="数据表名称"
            rules={[{ required: true, message: '请输入数据表名称' }]}
          >
            <Input placeholder="请输入数据表名称" />
          </Form.Item>
          <Form.Item name="table_description" label="描述">
            <Input.TextArea placeholder="请输入描述（可选）" rows={2} />
          </Form.Item>
        </Form>

        {/* 列配置 */}
        <div style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontWeight: 500 }}>表头配置</span>
            <Button size="small" onClick={handleAddColumn}>
              添加列
            </Button>
          </div>

          {columns.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#999', padding: 20 }}>
              暂无列配置，点击上方按钮添加
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ border: '1px solid #d9d9d9', padding: 8 }}>列名</th>
                  <th style={{ border: '1px solid #d9d9d9', padding: 8 }}>类型</th>
                  <th style={{ border: '1px solid #d9d9d9', padding: 8 }}>必填</th>
                  <th style={{ border: '1px solid #d9d9d9', padding: 8, width: 80 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((col, index) => (
                  <tr key={col.key}>
                    <td style={{ border: '1px solid #d9d9d9', padding: 4 }}>
                      <Input
                        value={col.label}
                        onChange={(e) => handleUpdateColumn(index, 'label', e.target.value)}
                        size="small"
                      />
                    </td>
                    <td style={{ border: '1px solid #d9d9d9', padding: 4 }}>
                      <select
                        value={col.type}
                        onChange={(e) => handleUpdateColumn(index, 'type', e.target.value)}
                        style={{ width: '100%' }}
                      >
                        <option value="text">文本</option>
                        <option value="number">数字</option>
                        <option value="date">日期</option>
                        <option value="select">下拉选择</option>
                      </select>
                    </td>
                    <td style={{ border: '1px solid #d9d9d9', padding: 4, textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={col.required || false}
                        onChange={(e) => handleUpdateColumn(index, 'required', e.target.checked)}
                      />
                    </td>
                    <td style={{ border: '1px solid #d9d9d9', padding: 4, textAlign: 'center' }}>
                      <Button size="small" danger onClick={() => handleDeleteColumn(index)}>
                        删除
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Modal>

      {/* 编辑数据表弹窗 */}
      <Modal
        title="编辑数据表"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false)
          editForm.resetFields()
        }}
        onOk={handleUpdate}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="table_name"
            label="数据表名称"
            rules={[{ required: true, message: '请输入数据表名称' }]}
          >
            <Input placeholder="请输入数据表名称" />
          </Form.Item>
          <Form.Item name="table_description" label="描述">
            <Input.TextArea placeholder="请输入描述（可选）" rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
