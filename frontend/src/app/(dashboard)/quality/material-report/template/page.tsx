'use client'

import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  message,
  Modal,
  Form,
  Input,
  Upload,
  Popconfirm,
  Spin,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  UploadOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  FileWordOutlined,
} from '@ant-design/icons'
import Link from 'next/link'
import dayjs from 'dayjs'
import {
  getTemplates,
  uploadTemplate,
  deleteTemplate,
  previewTemplate,
  updateTemplate,
} from '@/actions/material-report'
import type { TemplateListItem, TemplateResponse } from '@/types/material-report'
import type { UploadProps } from 'antd'

export default function TemplateListPage() {
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [templates, setTemplates] = useState<TemplateListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [previewModalVisible, setPreviewModalVisible] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateListItem | null>(null)
  const [previewData, setPreviewData] = useState<any>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()

  const fetchTemplates = async () => {
    setLoading(true)
    try {
      const result = await getTemplates({ is_active: undefined, page, page_size: pageSize })
      setTemplates(result.data?.items || [])
      setTotal(result.data?.total || 0)
    } catch (error) {
      message.error('获取模板列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTemplates()
  }, [page, pageSize])

  // 上传模板
  const handleUpload = async () => {
    try {
      const values = await form.validateFields()
      if (!values.file) {
        message.error('请选择模板文件')
        return
      }

      setUploading(true)
      await uploadTemplate(
        values.file,
        values.template_name,
        values.template_description
      )
      message.success('模板上传成功')
      setUploadModalVisible(false)
      form.resetFields()
      fetchTemplates()
    } catch (error: any) {
      message.error(error.message || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  // 编辑模板
  const handleEdit = (template: TemplateListItem) => {
    setSelectedTemplate(template)
    editForm.setFieldsValue({
      template_name: template.template_name,
      template_description: template.template_description,
    })
    setEditModalVisible(true)
  }

  const handleUpdate = async () => {
    try {
      const values = await editForm.validateFields()
      if (!selectedTemplate) return

      await updateTemplate(selectedTemplate.id, {
        template_name: values.template_name,
        template_description: values.template_description,
      })
      message.success('模板更新成功')
      setEditModalVisible(false)
      fetchTemplates()
    } catch (error: any) {
      message.error(error.message || '更新失败')
    }
  }

  // 预览模板
  const handlePreview = async (template: TemplateListItem) => {
    setSelectedTemplate(template)
    setPreviewModalVisible(true)
    setPreviewLoading(true)
    try {
      const result = await previewTemplate(template.id)
      setPreviewData(result.data)
    } catch (error) {
      message.error('获取模板预览失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  // 删除模板
  const handleDelete = async (id: string) => {
    try {
      await deleteTemplate(id)
      message.success('模板删除成功')
      fetchTemplates()
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  // 上传组件props
  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.docx,.doc',
    maxCount: 1,
    beforeUpload: (file) => {
      form.setFieldsValue({ file })
      return false
    },
  }

  const columns: ColumnsType<TemplateListItem> = [
    {
      title: '模板名称',
      dataIndex: 'template_name',
      key: 'template_name',
    },
    {
      title: '模板描述',
      dataIndex: 'template_description',
      key: 'template_description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
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
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            预览
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
            title="确定删除该模板吗？"
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
        title="Word模板管理"
        extra={
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalVisible(true)}
          >
            上传模板
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
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

      {/* 上传模板弹窗 */}
      <Modal
        title="上传Word模板"
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false)
          form.resetFields()
        }}
        onOk={handleUpload}
        confirmLoading={uploading}
        okText="上传"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="file"
            label="模板文件"
            rules={[{ required: true, message: '请选择Word模板文件' }]}
          >
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>选择Word文件 (.docx, .doc)</Button>
            </Upload>
          </Form.Item>
          <Form.Item
            name="template_name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" />
          </Form.Item>
          <Form.Item name="template_description" label="模板描述">
            <Input.TextArea placeholder="请输入模板描述（可选）" rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑模板弹窗 */}
      <Modal
        title="编辑模板"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false)
          editForm.resetFields()
        }}
        onOk={handleUpdate}
        okText="保存"
        cancelText="取消"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="template_name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" />
          </Form.Item>
          <Form.Item name="template_description" label="模板描述">
            <Input.TextArea placeholder="请输入模板描述（可选）" rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 预览模板弹窗 */}
      <Modal
        title={`模板预览 - ${selectedTemplate?.template_name || ''}`}
        open={previewModalVisible}
        onCancel={() => {
          setPreviewModalVisible(false)
          setPreviewData(null)
        }}
        footer={null}
        width={800}
      >
        {previewLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : previewData ? (
          <div>
            <h4>静态字段</h4>
            {previewData.field_mapping && Object.keys(previewData.field_mapping).length > 0 ? (
              <div style={{ marginBottom: 16 }}>
                {Object.entries(previewData.field_mapping).map(([key, config]: [string, any]) => (
                  <Tag key={key} style={{ margin: 4 }}>
                    {config.label || key}
                  </Tag>
                ))}
              </div>
            ) : (
              <p style={{ color: '#999' }}>无静态字段</p>
            )}

            <h4>表格字段</h4>
            {previewData.table_fields && previewData.table_fields.columns?.length > 0 ? (
              <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {previewData.table_fields.columns.map((col: any) => (
                        <th
                          key={col.key}
                          style={{
                            border: '1px solid #d9d9d9',
                            padding: 8,
                            textAlign: 'left',
                          }}
                        >
                          {col.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      {previewData.table_fields.columns.map((col: any) => (
                        <td
                          key={col.key}
                          style={{
                            border: '1px solid #d9d9d9',
                            padding: 8,
                            color: '#999',
                          }}
                        >
                          示例数据
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: '#999' }}>无表格字段（请确保Word文档包含表格）</p>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
