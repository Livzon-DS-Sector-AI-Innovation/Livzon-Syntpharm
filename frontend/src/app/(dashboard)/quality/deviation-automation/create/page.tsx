'use client'
import { createDeviationTask, generateDeviationReport, submitDeviationApproval, uploadDeviationFile, triggerAIProcess, uploadDeviationFileWithTask } from '@/actions/quality'

import { useState } from 'react'
import {
  Card,
  Form,
  Input,
  DatePicker,
  Button,
  Space,
  Upload,
  message,
  Spin,
  Modal,
  Table,
  Tag,
} from 'antd'
import {
  UploadOutlined,
  ReloadOutlined,
  RobotOutlined,
  DownloadOutlined,
  FileWordOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useRouter } from 'next/navigation'

const API_BASE = '/api/v1'

interface ReportTemplate {
  id: number
  name: string
  description: string
  file_path: string | null
  is_active: number
  create_time: string
}

export default function CreateDeviationReportPage() {
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [taskId, setTaskId] = useState<number | null>(null)
  const [templateModalVisible, setTemplateModalVisible] = useState(false)
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const router = useRouter()

  // 获取模板列表
  const fetchTemplates = async () => {
    setTemplatesLoading(true)
    try {
      const response = await fetch(`${API_BASE}/quality/deviation-automation/templates?is_active=1`)
      if (!response.ok) throw new Error('获取模板列表失败')
      const result = await response.json()
      setTemplates(result.data?.items || [])
    } catch (error: any) {
      message.error(error.message)
    } finally {
      setTemplatesLoading(false)
    }
  }

  // 下载模板
  const handleDownloadTemplate = (template: ReportTemplate) => {
    if (!template.file_path) {
      message.warning('该模板暂无文件，请先上传模板文件')
      return
    }
    window.open(`${API_BASE}/quality/deviation-automation/templates/${template.id}/download`, '_blank')
    setTemplateModalVisible(false)
  }

  // 显示模板选择弹窗
  const showTemplateModal = () => {
    fetchTemplates()
    setTemplateModalVisible(true)
  }

  // 创建任务
  const handleCreateTask = async (values: any) => {
    try {
      const response = await createDeviationTask({
        deviation_no: values.deviation_no,
        creator: values.creator,
        auditor: values.auditor,
        report_date: values.report_date.format('YYYY-MM-DD'),
      })

      return (response.data as any).task_id
    } catch (error: any) {
      throw new Error(error.message)
    }
  }

  // 上传文件
  const handleUploadFile = async (taskId: number, file: File) => {
    return await uploadDeviationFileWithTask(taskId, file)
  }

  // 触发AI处理
  const handleAIProcess = async (taskId: number) => {
    return await triggerAIProcess(taskId)
  }

  // 提交处理
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()

      if (fileList.length === 0) {
        message.error('请上传原始Word文件')
        return
      }

      setProcessing(true)

      // 1. 创建任务
      const newTaskId = await handleCreateTask(values)
      setTaskId(newTaskId)
      message.success('任务创建成功')

      // 2. 上传文件
      setUploading(true)
      await handleUploadFile(newTaskId, fileList[0].originFileObj as File)
      setUploading(false)
      message.success('文件上传成功')

      // 3. 触发AI处理
      message.loading('AI正在处理，请稍候...')
      await handleAIProcess(newTaskId)
      message.success('AI处理完成')

      // 4. 跳转到预览页面
      router.push(`/quality/deviation-automation/preview/${newTaskId}`)
    } catch (error: any) {
      message.error(error.message || '处理失败')
    } finally {
      setProcessing(false)
      setUploading(false)
    }
  }

  // 重置表单
  const handleReset = () => {
    form.resetFields()
    setFileList([])
    setTaskId(null)
  }

  // 模板表格列
  const templateColumns: ColumnsType<ReportTemplate> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (is_active: number) => (
        <Tag color={is_active === 1 ? 'green' : 'default'}>
          {is_active === 1 ? '启用' : '停用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button
          type="link"
          icon={<DownloadOutlined />}
          onClick={() => handleDownloadTemplate(record)}
          disabled={!record.file_path}
        >
          下载模板
        </Button>
      ),
    },
  ]

  // 上传变化
  const handleUploadChange = ({ fileList: newFileList }: { fileList: UploadFile[] }) => {
    setFileList(newFileList)
  }

  return (
    <div style={{ padding: 24 }}>
      <Card title="新建偏差报告">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            report_date: dayjs(),
          }}
        >
          {/* 基础信息区 */}
          <Card title="基础信息" size="small" style={{ marginBottom: 16 }}>
            <Space size="large" wrap>
              <Form.Item
                name="deviation_no"
                label="偏差编号"
                rules={[{ required: true, message: '请输入偏差编号' }]}
              >
                <Input placeholder="请输入偏差编号" style={{ width: 200 }} />
              </Form.Item>

              <Form.Item
                name="creator"
                label="报告编制人"
                rules={[{ required: true, message: '请输入报告编制人' }]}
              >
                <Input placeholder="请输入报告编制人" style={{ width: 150 }} />
              </Form.Item>

              <Form.Item
                name="auditor"
                label="QA审核人"
              >
                <Input placeholder="选填" style={{ width: 150 }} />
              </Form.Item>

              <Form.Item
                name="report_date"
                label="编制日期"
                rules={[{ required: true, message: '请选择日期' }]}
              >
                <DatePicker style={{ width: 150 }} />
              </Form.Item>
            </Space>
          </Card>

          {/* 文件上传区 */}
          <Card title="原始文件上传" size="small" style={{ marginBottom: 16 }}>
            <Space style={{ marginBottom: 12 }}>
              <Button
                icon={<DownloadOutlined />}
                onClick={showTemplateModal}
              >
                下载模板
              </Button>
            </Space>
            <Upload
              accept=".docx,.doc"
              fileList={fileList}
              onChange={handleUploadChange}
              beforeUpload={() => false}
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>上传Word文件</Button>
            </Upload>
            <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
              支持 .doc、.docx 格式，单文件不超过20MB
            </div>
          </Card>

          {/* 功能按钮区 */}
          <Space>
            <Button
              type="primary"
              icon={<RobotOutlined />}
              onClick={handleSubmit}
              loading={processing || uploading}
              disabled={fileList.length === 0}
            >
              {uploading ? '上传文件中...' : processing ? 'AI处理中...' : 'AI解析并生成报告'}
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置
            </Button>
          </Space>
        </Form>
      </Card>

      {/* 模板选择弹窗 */}
      <Modal
        title="选择报告模板"
        open={templateModalVisible}
        onCancel={() => setTemplateModalVisible(false)}
        footer={null}
        width={600}
      >
        <Table
          columns={templateColumns}
          dataSource={templates}
          rowKey="id"
          loading={templatesLoading}
          pagination={false}
          size="small"
        />
      </Modal>
    </div>
  )
}
