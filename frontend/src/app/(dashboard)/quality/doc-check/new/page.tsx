'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import {
  Card,
  Row,
  Col,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Space,
  Upload,
  Divider,
  message,
  Progress,
  Result,
} from 'antd'
import type { UploadFile, RcFile } from 'antd/es/upload'
import {
  UploadOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  FileTextOutlined,
} from '@ant-design/icons'

import {
  CheckConfig,
  FILE_TYPE_OPTIONS,
} from '@/types/doc-check'

const { Dragger } = Upload

// 默认校验配置
const DEFAULT_CHECK_CONFIG: CheckConfig = {
  enable_duplicate_check: true,
  enable_conflict_check: true,
  enable_regulation_check: true,
  enable_internal_control_check: true,
  severe_duplicate_threshold: 85,
  suspected_duplicate_threshold: 70,
}

interface UploadResponse {
  file_id: string
  file_name: string
  file_path: string
}


export default function DocCheckNewPage() {
  const router = useRouter()
  const pollRef = useRef<NodeJS.Timeout | null>(null)

  // 表单状态
  const [fileForm] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploadedFile, setUploadedFile] = useState<UploadResponse | null>(null)

  // 校验状态
  const [checking, setChecking] = useState(false)
  const [checkProgress, setCheckProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('')
  const [_taskId, setTaskId] = useState('')
  const [checkError, setCheckError] = useState<string | null>(null)
  const [checkConfig, setCheckConfig] = useState<CheckConfig>(DEFAULT_CHECK_CONFIG)

  // 文件上传
  const handleFileChange = ({ fileList: newFileList }: { fileList: UploadFile[] }) => {
    setFileList(newFileList)
    setUploadedFile(null)
    setCheckProgress(0)
    setCurrentStep('')
    setCheckError(null)
  }

  const beforeUpload = (file: RcFile) => {
    const isLt20M = file.size / 1024 / 1024 < 20
    if (!isLt20M) {
      message.error('文件大小不能超过 20MB')
      return Upload.LIST_IGNORE
    }

    const isWord = file.type === 'application/msword' || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    const isPdf = file.type === 'application/pdf'
    const isDoc = file.name.toLowerCase().endsWith('.doc') || file.name.toLowerCase().endsWith('.docx')
    const isPdfExt = file.name.toLowerCase().endsWith('.pdf')

    if (!((isWord || isPdf) && (isDoc || isPdfExt))) {
      message.error('仅支持 Word(.doc/.docx) 和 PDF 格式')
      return Upload.LIST_IGNORE
    }

    return false
  }

  const handleUploadFile = async () => {
    try {
      const values = await fileForm.validateFields()

      const files = fileList
        .filter((f) => f.originFileObj)
        .map((f) => f.originFileObj as File)

      if (files.length === 0) {
        message.warning('请先选择文件')
        return
      }

      const formData = new FormData()
      formData.append('file', files[0])
      formData.append('file_name', values.file_name)
      if (values.file_no) formData.append('file_no', values.file_no)
      if (values.file_version) formData.append('file_version', values.file_version)
      if (values.file_type) formData.append('file_type', values.file_type)
      if (values.preparer) formData.append('preparer', values.preparer)
      if (values.prepare_date) formData.append('prepare_date', values.prepare_date.format('YYYY-MM-DD'))

      message.loading({ content: '正在上传文件...', key: 'upload' })

      const response = await fetch(
        `/api/v1/doc-check/upload`,
        {
          method: 'POST',
          body: formData,
        }
      )

      const data = await response.json()

      if (data.code === 200) {
        message.success({ content: '文件上传成功', key: 'upload' })
        setUploadedFile(data.data)
      } else {
        message.error({ content: data.message || '文件上传失败', key: 'upload' })
      }
    } catch (error: unknown) {
      if ((error as { errorFields?: unknown }).errorFields) {
        return
      }
      message.error({ content: (error as Error).message || '文件上传失败', key: 'upload' })
    }
  }

  // 开始校验
  const handleStartCheck = async () => {
    if (!uploadedFile) {
      message.warning('请先上传文件')
      return
    }

    setChecking(true)
    setCheckProgress(0)
    setCurrentStep('文件解析中')
    setCheckError(null)

    try {
      message.loading({ content: '正在启动AI预审...', key: 'check' })

      const response = await fetch(
        `/api/v1/doc-check/check`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_id: uploadedFile.file_id,
            check_config: checkConfig,
          }),
        }
      )

      const data = await response.json()

      if (data.code === 200) {
        const tid = data.data.task_id
        setTaskId(tid)
        message.success({ content: 'AI预审已启动', key: 'check' })
        startPollingProgress(tid)
      } else {
        message.error({ content: data.message || '启动失败', key: 'check' })
        setChecking(false)
      }
    } catch (_error) {
      message.error({ content: '启动失败', key: 'check' })
      setChecking(false)
    }
  }

  // 轮询进度
  const startPollingProgress = (tid: string) => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
    }

    pollRef.current = setInterval(async () => {
      try {
        const response = await fetch(
          `/api/v1/doc-check/check/${tid}/progress`
        )
        const data = await response.json()

        if (data.code === 200) {
          const progressData = data.data
          setCheckProgress(progressData.progress)
          setCurrentStep(progressData.current_step)

          if (progressData.status === 'completed') {
            if (pollRef.current) {
              clearInterval(pollRef.current)
            }
            setChecking(false)
            message.success({ content: 'AI预审完成，即将跳转到详情页...', key: 'check' })
            // 跳转到详情页
            setTimeout(() => {
              router.push(`/quality/doc-check/${tid}`)
            }, 1500)
          } else if (progressData.status === 'failed') {
            if (pollRef.current) {
              clearInterval(pollRef.current)
            }
            setChecking(false)
            setCheckError(progressData.message || '校验失败')
            message.error({ content: '校验失败', key: 'check' })
          }
        }
      } catch (error) {
        console.error('获取进度失败:', error)
      }
    }, 2000)
  }

  // 清空
  const handleClear = () => {
    setFileList([])
    setUploadedFile(null)
    setCheckProgress(0)
    setCurrentStep('')
    setCheckError(null)
    setTaskId('')
    fileForm.resetFields()

    if (pollRef.current) {
      clearInterval(pollRef.current)
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push('/quality/doc-check')}
        >
          返回列表
        </Button>
      </div>

      <Row gutter={24}>
        {/* 左侧：文件上传 */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <FileTextOutlined />
                新建AI预审任务
              </Space>
            }
          >
            <Form form={fileForm} layout="vertical">
              <Form.Item name="file_name" label="文件名称" rules={[{ required: true, message: '请输入文件名称' }]}>
                <Input placeholder="请输入文件名称" />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="file_no" label="文件编号">
                    <Input placeholder="请输入文件编号" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="file_version" label="文件版本">
                    <Input placeholder="如：V1.0" />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item name="file_type" label="文件类型" rules={[{ required: true, message: '请选择文件类型' }]}>
                <Select placeholder="请选择文件类型">
                  {FILE_TYPE_OPTIONS.map((option) => (
                    <Select.Option key={option.value} value={option.value}>
                      {option.label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="preparer" label="编制人">
                    <Input placeholder="请输入编制人" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="prepare_date" label="编制日期">
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Divider>上传文件</Divider>

              <Dragger
                fileList={fileList}
                onChange={handleFileChange}
                beforeUpload={beforeUpload}
                multiple={false}
                maxCount={1}
                listType="text"
                accept=".doc,.docx,.pdf"
              >
                <p className="ant-upload-drag-icon">
                  <UploadOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽上传文件</p>
                <p className="ant-upload-hint">支持 Word(.doc/.docx) 和 PDF 格式，单文件≤20MB</p>
              </Dragger>

              <Divider />

              <Space style={{ width: '100%', justifyContent: 'center' }}>
                <Button
                  type="primary"
                  icon={<UploadOutlined />}
                  onClick={handleUploadFile}
                  disabled={fileList.length === 0}
                >
                  上传文件
                </Button>
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={handleStartCheck}
                  disabled={!uploadedFile || checking}
                  loading={checking}
                >
                  开始AI预审
                </Button>
                <Button icon={<DeleteOutlined />} onClick={handleClear}>
                  清空内容
                </Button>
              </Space>
            </Form>
          </Card>
        </Col>

        {/* 右侧：校验配置和进度 */}
        <Col span={12}>
          <Card title="校验配置" style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 16 }}>
              <Checkbox.Group
                defaultValue={['duplicate_check', 'conflict_check', 'regulation_check', 'internal_control_check']}
                onChange={(checkedValues) => {
                  setCheckConfig({
                    enable_duplicate_check: checkedValues.includes('duplicate_check'),
                    enable_conflict_check: checkedValues.includes('conflict_check'),
                    enable_regulation_check: checkedValues.includes('regulation_check'),
                    enable_internal_control_check: checkedValues.includes('internal_control_check'),
                    severe_duplicate_threshold: checkConfig.severe_duplicate_threshold,
                    suspected_duplicate_threshold: checkConfig.suspected_duplicate_threshold,
                  })
                }}
              >
                <Space direction="vertical">
                  <Checkbox value="duplicate_check">全文智能查重</Checkbox>
                  <Checkbox value="conflict_check">跨文件条款冲突检测</Checkbox>
                  <Checkbox value="regulation_check">GMP/药典法规合规校验</Checkbox>
                  <Checkbox value="internal_control_check">企业内控标准校验</Checkbox>
                </Space>
              </Checkbox.Group>
            </div>

            <Divider style={{ margin: '16px 0' }} />

            <Space>
              <span>严重重复阈值：</span>
              <InputNumber
                value={checkConfig.severe_duplicate_threshold}
                onChange={(val) => setCheckConfig({ ...checkConfig, severe_duplicate_threshold: val || 85 })}
                min={0}
                max={100}
                formatter={(value) => `${value}%`}
                parser={(value) => parseInt(value?.replace('%', '') || '0')}
                style={{ width: 80 }}
              />
            </Space>
            <br /><br />
            <Space>
              <span>疑似重复阈值：</span>
              <InputNumber
                value={checkConfig.suspected_duplicate_threshold}
                onChange={(val) => setCheckConfig({ ...checkConfig, suspected_duplicate_threshold: val || 70 })}
                min={0}
                max={100}
                formatter={(value) => `${value}%`}
                parser={(value) => parseInt(value?.replace('%', '') || '0')}
                style={{ width: 80 }}
              />
            </Space>
          </Card>

          <Card title="校验进度">
            {checking || checkProgress > 0 ? (
              <div>
                <Progress
                  percent={checkProgress}
                  status={checkError ? 'exception' : 'active'}
                  strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
                />
                <div style={{ textAlign: 'center', marginTop: 8 }}>
                  <Space>
                    <span>{currentStep}</span>
                    {checkError && <Tag color="red">{checkError}</Tag>}
                  </Space>
                </div>
              </div>
            ) : (
              <Result
                status="info"
                title="等待上传文件"
                subTitle="请先上传文件并开始AI预审"
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// 需要添加 Checkbox 和 InputNumber 导入
import { Checkbox } from 'antd'
import { InputNumber } from 'antd'
import { Tag } from 'antd'