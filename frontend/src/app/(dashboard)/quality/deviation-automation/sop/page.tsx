'use client'
import {createSopTemplate, createSopFromTemplate, updateSopTemplate, deleteSopTemplate, deleteSopRule, updateSopRuleStatus, createSopRule, uploadSopRule, aiParseSopRule} from '@/actions/quality'

import { useState, useRef } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Form,
  Input,
  Select,
  Tag,
  Modal,
  message,
  Popconfirm,
  Upload,
  Divider,
  Alert,
} from 'antd'
import {
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UploadOutlined,
  DownloadOutlined,
  RobotOutlined,
  FileWordOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { UploadProps, UploadFile } from 'antd/es/upload'

const API_BASE = '/api/v1'

interface SopRule {
  id: number
  sop_code: string
  sop_full_name: string
  sop_version: string
  business_tag: string
  standard_limit: string
  standard_sentence: string
  sop_file_path: string | null
  status: number
  create_time: string
  update_time: string
}

interface SopRuleFormData {
  sop_code: string
  sop_full_name: string
  sop_version: string
  business_tag: string
  standard_limit: string
  standard_sentence: string
}

const statusOptions = [
  { label: '生效', value: 1 },
  { label: '停用', value: 0 },
]

const getStatusTag = (status: number) => {
  return (
    <Tag color={status === 1 ? 'success' : 'default'}>
      {status === 1 ? '生效' : '停用'}
    </Tag>
  )
}

export default function SopManagementPage() {
  const [form] = Form.useForm()
  const [modalForm] = Form.useForm()
  const [data, setData] = useState<SopRule[]>([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  })
  const [modalVisible, setModalVisible] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [uploading, setUploading] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [parseResult, setParseResult] = useState<string | null>(null)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const fileListRef = useRef<UploadFile[]>([])

  const fetchData = async (page = 1, pageSize = 20) => {
    setLoading(true)
    try {
      const values = form.getFieldsValue()
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('page_size', String(pageSize))

      if (values.sop_code) params.set('sop_code', values.sop_code)
      if (values.sop_full_name) params.set('sop_full_name', values.sop_full_name)
      if (values.status !== undefined) params.set('status', String(values.status))

      const response = await fetch(
        `${API_BASE}/quality/deviation-automation/sop-rules?${params.toString()}`
      )
      if (!response.ok) throw new Error('查询失败')

      const result = await response.json()
      setData(result.data.items)
      setPagination({
        ...pagination,
        current: page,
        pageSize,
        total: result.data.total,
      })
    } catch (error: any) {
      message.error(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    fetchData(1, pagination.pageSize)
  }

  const handleReset = () => {
    form.resetFields()
    fetchData(1, pagination.pageSize)
  }

  const handleTableChange = (newPagination: any) => {
    fetchData(newPagination.current, newPagination.pageSize)
  }

  const handleAdd = () => {
    setEditingId(null)
    modalForm.resetFields()
    setFileList([])
    fileListRef.current = []
    setParseResult(null)
    setModalVisible(true)
  }

  const handleEdit = (record: SopRule) => {
    setEditingId(record.id)
    modalForm.setFieldsValue({
      sop_code: record.sop_code,
      sop_full_name: record.sop_full_name,
      sop_version: record.sop_version,
      business_tag: record.business_tag,
      standard_limit: record.standard_limit,
      standard_sentence: record.standard_sentence,
    })
    setFileList(record.sop_file_path ? [{ uid: '-1', name: '已上传文件.docx', status: 'done' }] : [])
    fileListRef.current = record.sop_file_path ? [{ uid: '-1', name: '已上传文件.docx', status: 'done' }] : []
    setParseResult(null)
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteSopRule(id)
      message.success('删除成功')
      fetchData(pagination.current, pagination.pageSize)
    } catch (error: any) {
      message.error(error.message)
    }
  }

  const handleStatusChange = async (id: number, newStatus: number) => {
    try {
      await updateSopRuleStatus(id, newStatus)
      message.success(newStatus === 1 ? '已启用' : '已停用')
      fetchData(pagination.current, pagination.pageSize)
    } catch (error: any) {
      message.error(error.message)
    }
  }

  const handleModalOk = async () => {
    try {
      const values = await modalForm.validateFields()

      // 如果是新建规则且已有文件上传了，需要先保存获取id再关联文件
      if (!editingId && fileList.length > 0 && fileList[0]?.name !== '已上传文件.docx') {
        // 文件已上传，保存时不需要再处理文件
      }

      const url = editingId
        ? `${API_BASE}/quality/deviation-automation/sop-rules/${editingId}`
        : `${API_BASE}/quality/deviation-automation/sop-rules`
      const method = editingId ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      })
      if (!response.ok) throw new Error(editingId ? '更新失败' : '创建失败')

      message.success(editingId ? '更新成功' : '创建成功')
      setModalVisible(false)
      fetchData(pagination.current, pagination.pageSize)
    } catch (error: any) {
      message.error(error.message)
    }
  }

  // 处理上传：新建时先保存规则获取id，编辑时直接上传
  const handleUpload = async (file: File) => {
    let currentRuleId = editingId

    // 如果是新建规则，先保存获取id（不强制验证，允许空值）
    if (!currentRuleId) {
      try {
        message.loading({ content: '正在保存规则...', key: 'upload' })

        // 获取表单值（不验证，允许为空）
        const values = modalForm.getFieldsValue(true)

        // 先保存规则获取id（必填项使用空字符串或占位符）
        const saveResult = await createSopRule({
            sop_code: values.sop_code || `SOP-TEMP-${Date.now()}`,
            sop_full_name: values.sop_full_name || '临时规则',
            sop_version: values.sop_version || 'V1.0',
            business_tag: values.business_tag || '',
            standard_limit: values.standard_limit || '',
            standard_sentence: values.standard_sentence || '',
          })
        currentRuleId = (saveResult.data as any).id
        setEditingId(currentRuleId) // 更新editingId
        message.success({ content: '规则已保存，正在上传文件...', key: 'upload' })
      } catch (error: any) {
        message.error({ content: error.message || '保存规则失败', key: 'upload' })
        return false
      }
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      if (!currentRuleId) {
        throw new Error('规则ID不存在')
      }
      await uploadSopRule(currentRuleId, file)

      message.success({ content: '文件上传成功', key: 'upload' })
      setFileList([{ uid: '-1', name: file.name, status: 'done' }])
      fileListRef.current = [{ uid: '-1', name: file.name, status: 'done' }]
      setParseResult(null)
      fetchData(pagination.current, pagination.pageSize)
      return false
    } catch (error: any) {
      message.error({ content: error.message || '上传失败', key: 'upload' })
      return false
    } finally {
      setUploading(false)
    }
  }

  const handleAiParse = async () => {
    if (!editingId) {
      message.warning('请先上传SOP文件后再进行AI解析')
      return
    }

    setParsing(true)
    setParseResult(null)
    try {
      const response = await aiParseSopRule(editingId)

      setParseResult((response.data as any).ai_result)

      // 如果解析出了数据，更新表单
      if ((response.data as any).parsed_data) {
        const parsed = (response.data as any).parsed_data
        modalForm.setFieldsValue({
          sop_code: parsed.sop_code || modalForm.getFieldValue('sop_code'),
          sop_full_name: parsed.sop_full_name || modalForm.getFieldValue('sop_full_name'),
          sop_version: parsed.sop_version || modalForm.getFieldValue('sop_version'),
          business_tag: parsed.business_tag || modalForm.getFieldValue('business_tag'),
          standard_limit: parsed.standard_limit || modalForm.getFieldValue('standard_limit'),
          standard_sentence: parsed.standard_sentence || modalForm.getFieldValue('standard_sentence'),
        })
      }

      message.success('AI解析完成')
      fetchData(pagination.current, pagination.pageSize)
    } catch (error: any) {
      message.error(error.message || 'AI解析失败')
    } finally {
      setParsing(false)
    }
  }

  const handleDownload = async (record: SopRule) => {
    if (!record.sop_file_path) {
      message.warning('该规则暂无上传文件')
      return
    }

    try {
      const response = await fetch(
        `${API_BASE}/quality/deviation-automation/sop-rules/${record.id}/download`
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '下载失败')
      }

      // 获取文件名
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `${record.sop_code}.docx`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (match) {
          filename = match[1].replace(/['"]/g, '')
        }
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success('下载成功')
    } catch (error: any) {
      message.error(error.message || '下载失败')
    }
  }

  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.docx,.doc',
    fileList: fileList,
    beforeUpload: handleUpload,
    onChange: ({ fileList: newFileList }) => {
      setFileList(newFileList)
      fileListRef.current = newFileList
    },
    onRemove: () => {
      setFileList([])
      fileListRef.current = []
    },
    maxCount: 1,
    customRequest: ({ file, onSuccess, onError }) => {
      // 使用 beforeUpload 处理
      handleUpload(file as File).then((result) => {
        if (result !== false) {
          onSuccess?.({})
        }
      }).catch((err) => {
        onError?.(err as any)
      })
      return false
    },
  }

  const columns: ColumnsType<SopRule> = [
    {
      title: 'SOP编号',
      dataIndex: 'sop_code',
      key: 'sop_code',
      width: 120,
    },
    {
      title: 'SOP全称',
      dataIndex: 'sop_full_name',
      key: 'sop_full_name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '版本',
      dataIndex: 'sop_version',
      key: 'sop_version',
      width: 80,
    },
    {
      title: '业务标签',
      dataIndex: 'business_tag',
      key: 'business_tag',
      width: 100,
    },
    {
      title: '标准限度',
      dataIndex: 'standard_limit',
      key: 'standard_limit',
      width: 150,
      ellipsis: true,
    },
    {
      title: '标准语句',
      dataIndex: 'standard_sentence',
      key: 'standard_sentence',
      width: 250,
      ellipsis: true,
    },
    {
      title: '文件',
      dataIndex: 'sop_file_path',
      key: 'sop_file_path',
      width: 80,
      render: (path) => path ? <FileWordOutlined style={{ color: '#1677ff' }} /> : <span style={{ color: '#999' }}>无</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status) => getStatusTag(status),
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          {record.sop_file_path && (
            <Button
              type="link"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record)}
            >
              下载
            </Button>
          )}
          <Button
            type="link"
            size="small"
            onClick={() => handleStatusChange(record.id, record.status === 1 ? 0 : 1)}
          >
            {record.status === 1 ? '停用' : '启用'}
          </Button>
          <Popconfirm
            title="确定删除此规则？"
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
      <Card title="SOP规则管理">
        {/* 查询条件 */}
        <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="sop_code" label="SOP编号">
            <Input placeholder="请输入" style={{ width: 150 }} />
          </Form.Item>
          <Form.Item name="sop_full_name" label="SOP全称">
            <Input placeholder="请输入" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select
              placeholder="请选择"
              style={{ width: 100 }}
              allowClear
              options={statusOptions}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
              <Button onClick={handleReset}>重置</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                新增规则
              </Button>
            </Space>
          </Form.Item>
        </Form>

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
        title={editingId ? '编辑SOP规则' : '新增SOP规则'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        width={800}
        destroyOnClose
      >
        <Form form={modalForm} layout="vertical">
          <Form.Item
            name="sop_code"
            label="SOP编号"
            rules={[{ required: true, message: '请输入SOP编号' }]}
          >
            <Input placeholder="请输入SOP编号，如 SOP-QA-001" />
          </Form.Item>
          <Form.Item
            name="sop_full_name"
            label="SOP全称"
            rules={[{ required: true, message: '请输入SOP全称' }]}
          >
            <Input placeholder="请输入SOP全称" />
          </Form.Item>
          <Form.Item
            name="sop_version"
            label="版本"
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="请输入版本号，如 V1.0" />
          </Form.Item>
          <Form.Item
            name="business_tag"
            label="业务标签"
            rules={[{ required: true, message: '请输入业务标签' }]}
          >
            <Input placeholder="请输入业务标签，如 偏差管理、质量控制" />
          </Form.Item>
          <Form.Item
            name="standard_limit"
            label="标准限度"
            rules={[{ required: true, message: '请输入标准限度' }]}
          >
            <Input.TextArea
              placeholder="请输入标准限度，用于判断偏差是否超标"
              rows={2}
            />
          </Form.Item>
          <Form.Item
            name="standard_sentence"
            label="标准语句"
            rules={[{ required: true, message: '请输入标准语句' }]}
          >
            <Input.TextArea
              placeholder="请输入标准语句，用于生成偏差报告的参考语句"
              rows={4}
            />
          </Form.Item>
        </Form>

        <Divider titlePlacement="left">SOP文件管理</Divider>

        <div style={{ marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <Upload {...uploadProps}>
                <Button icon={<UploadOutlined />} loading={uploading}>
                  {fileList.length > 0 ? '重新上传文件' : '上传SOP文件'}
                </Button>
              </Upload>
              <Button
                icon={<RobotOutlined />}
                onClick={handleAiParse}
                loading={parsing}
                disabled={!editingId}
              >
                AI解析提取
              </Button>
            </Space>
            <div style={{ fontSize: 12, color: '#999' }}>
              支持上传 .docx、.doc 格式的SOP文件，上传后可使用AI自动提取关键信息
            </div>

            {parseResult && (
              <Alert
                type="info"
                message="AI解析结果"
                description={
                  <pre style={{ maxHeight: 200, overflow: 'auto', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                    {parseResult}
                  </pre>
                }
                style={{ marginTop: 8 }}
              />
            )}
          </Space>
        </div>
      </Modal>
    </div>
  )
}
