'use client'
import {createDeviationTemplate, deleteDeviationTemplate, updateDeviationTemplateStatus, uploadDeviationTemplate} from '@/actions/quality'

import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Form,
  Input,
  Tag,
  Modal,
  message,
  Popconfirm,
  Upload,
  Switch,
  Alert,
} from 'antd'
import {
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UploadOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd/es/upload/interface'

const API_BASE = '/api/v1'

interface Template {
  id: number
  name: string
  description: string | null
  file_path: string | null
  is_active: boolean
  create_time: string
}

interface TemplateFormData {
  name: string
  description: string
  is_active: boolean
}

export default function TemplateManagementPage() {
  const [form] = Form.useForm()
  const [modalForm] = Form.useForm()
  const [data, setData] = useState<Template[]>([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  })
  const [modalVisible, setModalVisible] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [uploadingTemplateId, setUploadingTemplateId] = useState<number | null>(null)
  const [uploadFileList, setUploadFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async (page = 1, pageSize = 20) => {
    setLoading(true)
    try {
      const response = await fetch(
        `${API_BASE}/quality/deviation-automation/templates?page=${page}&page_size=${pageSize}`
      )
      if (!response.ok) throw new Error('查询失败')

      const result = await response.json()
      setData(result.data?.items || [])
      setPagination({
        ...pagination,
        current: page,
        pageSize,
        total: result.data?.total || 0,
      })
    } catch (error: any) {
      message.error(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleTableChange = (newPagination: any) => {
    fetchData(newPagination.current, newPagination.pageSize)
  }

  const handleAdd = () => {
    setEditingId(null)
    modalForm.resetFields()
    modalForm.setFieldsValue({ is_active: true })
    setModalVisible(true)
  }

  const handleEdit = (record: Template) => {
    setEditingId(record.id)
    modalForm.setFieldsValue({
      name: record.name,
      description: record.description,
      is_active: record.is_active,
    })
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteDeviationTemplate(id)
      message.success('删除成功')
      fetchData(pagination.current, pagination.pageSize)
    } catch (error: any) {
      message.error(error.message)
    }
  }

  const handleStatusChange = async (id: number, is_active: boolean) => {
    try {
      await updateDeviationTemplateStatus(id, is_active)
      message.success(is_active ? '已启用' : '已停用')
      fetchData(pagination.current, pagination.pageSize)
    } catch (error: any) {
      message.error(error.message)
    }
  }

  const handleModalOk = async () => {
    try {
      const values = await modalForm.validateFields()
      const url = editingId
        ? `${API_BASE}/quality/deviation-automation/templates/${editingId}`
        : `${API_BASE}/quality/deviation-automation/templates`
      const method = editingId ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...values,
          is_active: values.is_active ? 1 : 0,
        }),
      })
      if (!response.ok) throw new Error(editingId ? '更新失败' : '创建失败')

      const result = await response.json()
      message.success(editingId ? '更新成功' : '创建成功')
      setModalVisible(false)

      // 如果是新建模板，打开上传弹窗
      if (!editingId && result.data?.id) {
        setUploadingTemplateId(result.data.id)
        setUploadFileList([])
        setUploadModalVisible(true)
      }

      fetchData(pagination.current, pagination.pageSize)
    } catch (error: any) {
      message.error(error.message)
    }
  }

  const handleUploadTemplateFile = async () => {
    if (!uploadingTemplateId || uploadFileList.length === 0) {
      message.warning('请选择要上传的文件')
      return
    }

    const file = uploadFileList[0]
    if (!file.originFileObj) {
      message.error('文件无效')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      await uploadDeviationTemplate(file.originFileObj as File)

      message.success('模板文件上传成功')
      setUploadModalVisible(false)
      setUploadFileList([])
      fetchData(pagination.current, pagination.pageSize)
    } catch (error: any) {
      message.error(error.message)
    } finally {
      setUploading(false)
    }
  }

  const handleUploadClick = (record: Template) => {
    setUploadingTemplateId(record.id)
    setUploadFileList([])
    setUploadModalVisible(true)
  }

  const handleDownload = (record: Template) => {
    if (!record.file_path) {
      message.warning('模板文件不存在，请先上传')
      return
    }
    window.open(
      `${API_BASE}/quality/deviation-automation/templates/${record.id}/download`,
      '_blank'
    )
  }

  const columns: ColumnsType<Template> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 300,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (is_active, record) => (
        <Switch
          checked={is_active === 1 || is_active === true}
          onChange={(checked) => handleStatusChange(record.id, checked)}
          checkedChildren="启用"
          unCheckedChildren="停用"
          size="small"
        />
      ),
    },
    {
      title: '模板文件',
      dataIndex: 'file_path',
      key: 'file_path',
      width: 120,
      render: (file_path) => (
        file_path ? (
          <Tag color="success">已上传</Tag>
        ) : (
          <Tag color="default">未上传</Tag>
        )
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'create_time',
      key: 'create_time',
      width: 180,
      render: (text) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 250,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<UploadOutlined />}
            onClick={() => handleUploadClick(record)}
          >
            上传
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record)}
            disabled={!record.file_path}
          >
            下载
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此模板？"
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
      <Card title="报告模板管理">
        {/* 操作区 */}
        <div style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增模板
          </Button>
        </div>

        {/* 数据列表 */}
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          onChange={handleTableChange}
        />
      </Card>

      {/* 新增/编辑弹窗 */}
      <Modal
        title={editingId ? '编辑模板' : '新增模板'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        width={500}
        destroyOnClose
      >
        <Form form={modalForm} layout="vertical">
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称，如：标准偏差报告模板" />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea
              placeholder="请输入模板描述"
              rows={3}
            />
          </Form.Item>
          <Form.Item
            name="is_active"
            label="启用状态"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 上传模板文件弹窗 */}
      <Modal
        title="上传模板文件"
        open={uploadModalVisible}
        onOk={handleUploadTemplateFile}
        onCancel={() => setUploadModalVisible(false)}
        confirmLoading={uploading}
        width={500}
      >
        <div style={{ padding: '16px 0' }}>
          <Alert
            message="上传说明"
            description="请上传标准的偏差报告Word模板文件（.docx或.doc格式）。模板中可以使用占位符如 {{偏差编号}}、{{编制人}} 等。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Upload
            accept=".docx,.doc"
            fileList={uploadFileList}
            onChange={({ fileList }) => setUploadFileList(fileList)}
            beforeUpload={() => false}
            maxCount={1}
          >
            <Button icon={<UploadOutlined />}>选择Word文件</Button>
          </Upload>
          <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
            支持 .doc、.docx 格式，单文件不超过20MB
          </div>
        </div>
      </Modal>
    </div>
  )
}
