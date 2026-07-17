'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
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
  Progress,
  Tabs,
  Table,
  Tag,
  Modal,
  message,
  Divider,
  Alert,
  Popconfirm,
  Checkbox,
  InputNumber,
  Spin,
  Result,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile, RcFile } from 'antd/es/upload'
import {
  UploadOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  DownloadOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  WarningOutlined,
  SafetyOutlined,
  AuditOutlined,
  FileSearchOutlined,
  LoadingOutlined,
} from '@ant-design/icons'

import {
  // 类型
  CheckConfig,
  CheckProblem,
  CheckMainDetail,
  CheckStatus,
  FileType,
  RiskLevel,
  HandleStatus,
  CheckItemType,
  // 选项
  FILE_TYPE_OPTIONS,
  RISK_LEVEL_OPTIONS,
  HANDLE_STATUS_OPTIONS,
  CHECK_ITEM_OPTIONS,
  // 常量
  CHECK_STEPS,
} from '@/types/doc-check'

import {
  startCheck,
  getCheckProgress,
  handleProblem,
  exportCheckReport,
  confirmCheck,
} from '@/actions/doc-check'

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

// 风险颜色映射
const RISK_COLORS: Record<RiskLevel, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
}

// 风险标签映射
const RISK_LABELS: Record<RiskLevel, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
}

// 状态颜色映射
const STATUS_COLORS: Record<CheckStatus, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
}

// 状态文本映射
const STATUS_LABELS: Record<CheckStatus, string> = {
  pending: '待处理',
  running: '校验中',
  completed: '已完成',
  failed: '已失败',
  cancelled: '已取消',
}

export default function DocCheckPage() {
  // ============ 状态管理 ============

  // 上传相关状态
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploadedFile, setUploadedFile] = useState<{
    file_id: string
    file_name: string
    file_path: string
  } | null>(null)

  // 表单状态
  const [fileForm] = Form.useForm()
  const [checkConfig, setCheckConfig] = useState<CheckConfig>(DEFAULT_CHECK_CONFIG)

  // 校验进度状态
  const [checking, setChecking] = useState(false)
  const [checkProgress, setCheckProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('')
  const [taskId, setTaskId] = useState('')
  const [checkError, setCheckError] = useState<string | null>(null)

  // 校验结果状态
  const [checkResult, setCheckResult] = useState<CheckMainDetail | null>(null)
  const [activeTab, setActiveTab] = useState<string>('duplicate')

  // 记录列表状态
  const [records, setRecords] = useState<CheckMainDetail[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  // 问题处理弹窗
  const [problemModalVisible, setProblemModalVisible] = useState(false)
  const [selectedProblem, setSelectedProblem] = useState<CheckProblem | null>(null)
  const [handleForm] = Form.useForm()

  // 轮询定时器
  const pollRef = useRef<NodeJS.Timeout | null>(null)

  // ============ 文件上传处理 ============

  const handleFileChange = ({ fileList: newFileList }: { fileList: UploadFile[] }) => {
    setFileList(newFileList)
    setUploadedFile(null)
    setCheckResult(null)
    setCheckProgress(0)
    setCurrentStep('')
    setCheckError(null)
  }

  const beforeUpload = (file: RcFile) => {
    // 检查文件大小 (20MB)
    const isLt20M = file.size / 1024 / 1024 < 20
    if (!isLt20M) {
      message.error('文件大小不能超过 20MB')
      return Upload.LIST_IGNORE
    }

    // 检查文件类型
    const isWord = file.type === 'application/msword' || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    const isPdf = file.type === 'application/pdf'
    const isDoc = file.name.toLowerCase().endsWith('.doc') || file.name.toLowerCase().endsWith('.docx')
    const isPdfExt = file.name.toLowerCase().endsWith('.pdf')

    if (!((isWord || isPdf) && (isDoc || isPdfExt))) {
      message.error('仅支持 Word(.doc/.docx) 和 PDF 格式')
      return Upload.LIST_IGNORE
    }

    // 不自动上传
    return false
  }

  // 上传文件到服务器
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

  // 开始AI预审
  const handleStartCheck = async () => {
    if (!uploadedFile) {
      message.warning('请先上传文件')
      return
    }

    setChecking(true)
    setCheckProgress(0)
    setCurrentStep('文件解析中')
    setCheckError(null)
    setCheckResult(null)

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
        const taskId = data.data.task_id
        setTaskId(taskId)
        message.success({ content: 'AI预审已启动', key: 'check' })

        // 开始轮询进度
        startPollingProgress(taskId)
      } else {
        message.error({ content: data.message || '启动失败', key: 'check' })
        setChecking(false)
      }
    } catch (error) {
      message.error({ content: '启动失败', key: 'check' })
      setChecking(false)
    }
  }

  // 轮询校验进度
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
            // 校验完成
            if (pollRef.current) {
              clearInterval(pollRef.current)
            }
            setChecking(false)

            // 获取详细结果
            if (progressData.result) {
              setCheckResult({
                id: tid,
                file_name: uploadedFile?.file_name || '',
                status: 'completed',
                total_problems: progressData.result.total_problems,
                risk_high: progressData.result.risk_high,
                risk_medium: progressData.result.risk_medium,
                risk_low: progressData.result.risk_low,
                problems: progressData.result.problems,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              })
            }

            message.success({ content: 'AI预审完成', key: 'check' })
          } else if (progressData.status === 'failed') {
            // 校验失败
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

  // 清空内容
  const handleClear = () => {
    setFileList([])
    setUploadedFile(null)
    setCheckResult(null)
    setCheckProgress(0)
    setCurrentStep('')
    setCheckError(null)
    setTaskId('')
    fileForm.resetFields()

    if (pollRef.current) {
      clearInterval(pollRef.current)
    }
  }

  // ============ 校验配置处理 ============

  const handleConfigChange = (checkedValues: string[]) => {
    setCheckConfig({
      enable_duplicate_check: checkedValues.includes('duplicate_check'),
      enable_conflict_check: checkedValues.includes('conflict_check'),
      enable_regulation_check: checkedValues.includes('regulation_check'),
      enable_internal_control_check: checkedValues.includes('internal_control_check'),
      severe_duplicate_threshold: checkConfig.severe_duplicate_threshold,
      suspected_duplicate_threshold: checkConfig.suspected_duplicate_threshold,
    })
  }

  const handleThresholdChange = (field: 'severe_duplicate_threshold' | 'suspected_duplicate_threshold', value: number) => {
    setCheckConfig({
      ...checkConfig,
      [field]: value,
    })
  }

  // ============ 问题处理 ============

  const handleViewProblem = (problem: CheckProblem) => {
    setSelectedProblem(problem)
    handleForm.setFieldsValue({
      handle_status: problem.handle_status,
      ignore_reason: problem.ignore_reason,
    })
    setProblemModalVisible(true)
  }

  const handleConfirmProblem = async () => {
    try {
      const values = await handleForm.validateFields()

      if (!selectedProblem) return

      const response = await fetch(
        `/api/v1/doc-check/problems/${selectedProblem.id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            handle_status: values.handle_status,
            ignore_reason: values.ignore_reason,
          }),
        }
      )

      const data = await response.json()

      if (data.code === 200) {
        message.success('处理成功')
        setProblemModalVisible(false)

        // 刷新结果
        if (checkResult) {
          const updatedProblems = checkResult.problems.map((p) =>
            p.id === selectedProblem.id ? { ...p, ...values } : p
          )
          setCheckResult({ ...checkResult, problems: updatedProblems })
        }
      } else {
        message.error(data.message || '处理失败')
      }
    } catch (error) {
      message.error('处理失败')
    }
  }

  // ============ 报告操作 ============

  const handleExportReport = async () => {
    if (!checkResult) return

    try {
      message.loading({ content: '正在生成报告...', key: 'export' })

      const response = await fetch(
        `/api/v1/doc-check/export/${checkResult.id}?format=pdf`
      )

      const data = await response.json()

      if (data.code === 200) {
        // 下载文件
        window.open(data.data.download_url, '_blank')
        message.success({ content: '报告生成成功', key: 'export' })
      } else {
        message.error({ content: data.message || '生成失败', key: 'export' })
      }
    } catch (error) {
      message.error({ content: '生成失败', key: 'export' })
    }
  }

  const handleConfirmPass = async () => {
    if (!checkResult) return

    try {
      const response = await fetch(
        `/api/v1/doc-check/records/${checkResult.id}/confirm`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      )

      const data = await response.json()

      if (data.code === 200) {
        message.success('确认通过成功')
        // 刷新记录
        loadRecords()
      } else {
        message.error(data.message || '确认失败')
      }
    } catch (error) {
      message.error('确认失败')
    }
  }

  const handleReCheck = () => {
    if (!uploadedFile) {
      message.warning('请先上传文件')
      return
    }
    handleStartCheck()
  }

  // ============ 记录列表 ============

  const loadRecords = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(
        `/api/v1/doc-check/records?page=${page}&page_size=${pageSize}`
      )
      const data = await response.json()

      if (data.code === 200) {
        setRecords(data.data.items || [])
        setTotal(data.data.total || 0)
      }
    } catch (error) {
      console.error('加载记录失败:', error)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  useEffect(() => {
    loadRecords()
  }, [loadRecords])

  // ============ 表格列定义 ============

  // 查重结果列
  const duplicateColumns: ColumnsType<CheckProblem> = [
    { title: '序号', dataIndex: 'id', key: 'index', width: 60, render: (_, __, index) => index + 1 },
    { title: '重复段落', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '源文件', dataIndex: 'source_file', key: 'source_file', width: 150 },
    { title: '源文件编号', dataIndex: 'source_file_no', key: 'source_file_no', width: 120 },
    {
      title: '相似度',
      dataIndex: 'similarity',
      key: 'similarity',
      width: 80,
      render: (val: number) => `${val?.toFixed(1) || '-'}%`,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 90,
      render: (val: RiskLevel) => <Tag color={RISK_COLORS[val]}>{RISK_LABELS[val]}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewProblem(record)}>
          处理
        </Button>
      ),
    },
  ]

  // 冲突结果列
  const conflictColumns: ColumnsType<CheckProblem> = [
    { title: '序号', dataIndex: 'id', key: 'index', width: 60, render: (_, __, index) => index + 1 },
    { title: '冲突参数', dataIndex: 'conflict_param', key: 'conflict_param', ellipsis: true },
    { title: '本文档内容', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '系统标准', dataIndex: 'system_content', key: 'system_content', ellipsis: true },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 90,
      render: (val: RiskLevel) => <Tag color={RISK_COLORS[val]}>{RISK_LABELS[val]}</Tag>,
    },
    { title: '整改建议', dataIndex: 'suggestion', key: 'suggestion', ellipsis: true },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewProblem(record)}>
          处理
        </Button>
      ),
    },
  ]

  // 法规合规列
  const regulationColumns: ColumnsType<CheckProblem> = [
    { title: '序号', dataIndex: 'id', key: 'index', width: 60, render: (_, __, index) => index + 1 },
    { title: '问题位置', dataIndex: 'location', key: 'location', width: 100 },
    { title: '违规描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '法规依据', dataIndex: 'regulation_basis', key: 'regulation_basis', ellipsis: true },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 90,
      render: (val: RiskLevel) => <Tag color={RISK_COLORS[val]}>{RISK_LABELS[val]}</Tag>,
    },
    { title: '整改建议', dataIndex: 'suggestion', key: 'suggestion', ellipsis: true },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewProblem(record)}>
          处理
        </Button>
      ),
    },
  ]

  // 内控合规列
  const internalColumns: ColumnsType<CheckProblem> = [
    { title: '序号', dataIndex: 'id', key: 'index', width: 60, render: (_, __, index) => index + 1 },
    { title: '问题位置', dataIndex: 'location', key: 'location', width: 100 },
    { title: '不符描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '上级文件依据', dataIndex: 'internal_file_basis', key: 'internal_file_basis', ellipsis: true },
    { title: '整改建议', dataIndex: 'suggestion', key: 'suggestion', ellipsis: true },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewProblem(record)}>
          处理
        </Button>
      ),
    },
  ]

  // ============ 标签页数据 ============

  const getFilteredProblems = (type: CheckItemType) => {
    if (!checkResult) return []
    return checkResult.problems.filter((p) => p.problem_type === type)
  }

  const tabItems = [
    {
      key: 'duplicate',
      label: (
        <Space>
          <FileSearchOutlined />
          查重结果
          {getFilteredProblems('duplicate').length > 0 && (
            <Tag color="blue">{getFilteredProblems('duplicate').length}</Tag>
          )}
        </Space>
      ),
      children: (
        <Table
          columns={duplicateColumns}
          dataSource={getFilteredProblems('duplicate')}
          rowKey="id"
          pagination={false}
          scroll={{ y: 400 }}
          locale={{ emptyText: '暂无查重问题' }}
        />
      ),
    },
    {
      key: 'conflict',
      label: (
        <Space>
          <ExclamationCircleOutlined />
          条款冲突
          {getFilteredProblems('conflict').length > 0 && (
            <Tag color="blue">{getFilteredProblems('conflict').length}</Tag>
          )}
        </Space>
      ),
      children: (
        <Table
          columns={conflictColumns}
          dataSource={getFilteredProblems('conflict')}
          rowKey="id"
          pagination={false}
          scroll={{ y: 400 }}
          locale={{ emptyText: '暂无冲突问题' }}
        />
      ),
    },
    {
      key: 'regulation',
      label: (
        <Space>
          <SafetyOutlined />
          法规合规
          {getFilteredProblems('regulation').length > 0 && (
            <Tag color="blue">{getFilteredProblems('regulation').length}</Tag>
          )}
        </Space>
      ),
      children: (
        <Table
          columns={regulationColumns}
          dataSource={getFilteredProblems('regulation')}
          rowKey="id"
          pagination={false}
          scroll={{ y: 400 }}
          locale={{ emptyText: '暂无法规问题' }}
        />
      ),
    },
    {
      key: 'internal_control',
      label: (
        <Space>
          <AuditOutlined />
          内控合规
          {getFilteredProblems('internal_control').length > 0 && (
            <Tag color="blue">{getFilteredProblems('internal_control').length}</Tag>
          )}
        </Space>
      ),
      children: (
        <Table
          columns={internalColumns}
          dataSource={getFilteredProblems('internal_control')}
          rowKey="id"
          pagination={false}
          scroll={{ y: 400 }}
          locale={{ emptyText: '暂无内控问题' }}
        />
      ),
    },
  ]

  // ============ 渲染 ============

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={16}>
        {/* 左侧：文件上传区域 */}
        <Col span={10}>
          <Card title={<Space><FileTextOutlined />文件上传区域</Space>}>
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
        <Col span={14}>
          {/* 校验配置 */}
          <Card title={<Space><AuditOutlined />AI校验可配置项</Space>} style={{ marginBottom: 16 }}>
            <Checkbox.Group
              defaultValue={[
                'duplicate_check',
                'conflict_check',
                'regulation_check',
                'internal_control_check',
              ]}
              onChange={handleConfigChange}
            >
              <Row gutter={[0, 8]}>
                <Col span={24}>
                  <Checkbox value="duplicate_check">全文智能查重</Checkbox>
                </Col>
                <Col span={24}>
                  <Checkbox value="conflict_check">跨文件条款冲突检测</Checkbox>
                </Col>
                <Col span={24}>
                  <Checkbox value="regulation_check">GMP/药典法规合规校验</Checkbox>
                </Col>
                <Col span={24}>
                  <Checkbox value="internal_control_check">企业内控标准校验</Checkbox>
                </Col>
              </Row>
            </Checkbox.Group>

            <Divider style={{ marginTop: 16 }} />

            <Row gutter={16}>
              <Col span={12}>
                <Space>
                  <span>严重重复阈值：</span>
                  <InputNumber
                    value={checkConfig.severe_duplicate_threshold}
                    onChange={(val) => handleThresholdChange('severe_duplicate_threshold', val || 85)}
                    min={0}
                    max={100}
                    formatter={(value) => `${value}%`}
                    parser={(value) => parseInt(value?.replace('%', '') || '0')}
                    style={{ width: 80 }}
                  />
                </Space>
              </Col>
              <Col span={12}>
                <Space>
                  <span>疑似重复阈值：</span>
                  <InputNumber
                    value={checkConfig.suspected_duplicate_threshold}
                    onChange={(val) => handleThresholdChange('suspected_duplicate_threshold', val || 70)}
                    min={0}
                    max={100}
                    formatter={(value) => `${value}%`}
                    parser={(value) => parseInt(value?.replace('%', '') || '0')}
                    style={{ width: 80 }}
                  />
                </Space>
              </Col>
            </Row>
          </Card>

          {/* 校验进度 */}
          <Card title={<Space><LoadingOutlined />校验进度展示</Space>} style={{ marginBottom: 16 }}>
            {checking || checkProgress > 0 ? (
              <div>
                <Progress
                  percent={checkProgress}
                  status={checkError ? 'exception' : 'active'}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
                <div style={{ textAlign: 'center', marginTop: 8 }}>
                  <Space>
                    <span>{currentStep}</span>
                    {checkError && (
                      <Tag color="red">{checkError}</Tag>
                    )}
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

          {/* 校验结果统计 */}
          {checkResult && (
            <Card
              title={
                <Space>
                  <CheckCircleOutlined />
                  校验结果
                </Space>
              }
              extra={
                <Space>
                  <Tag color="red">高风险: {checkResult.risk_high}</Tag>
                  <Tag color="orange">中风险: {checkResult.risk_medium}</Tag>
                  <Tag color="green">低风险: {checkResult.risk_low}</Tag>
                </Space>
              }
            >
              <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={tabItems}
              />

              <Divider />

              <Space style={{ width: '100%', justifyContent: 'center' }}>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={handleExportReport}
                >
                  导出PDF报告
                </Button>
                <Popconfirm
                  title="确认通过后，将标记该文件已审核通过"
                  onConfirm={handleConfirmPass}
                >
                  <Button type="primary" icon={<CheckCircleOutlined />}>
                    确认无误通过
                  </Button>
                </Popconfirm>
                <Button icon={<ReloadOutlined />} onClick={handleReCheck}>
                  重新校验
                </Button>
              </Space>
            </Card>
          )}
        </Col>
      </Row>

      {/* 问题处理弹窗 */}
      <Modal
        title="问题处理"
        open={problemModalVisible}
        onCancel={() => setProblemModalVisible(false)}
        footer={
          <Space>
            <Button onClick={() => setProblemModalVisible(false)}>取消</Button>
            <Button type="primary" onClick={handleConfirmProblem}>
              确认
            </Button>
          </Space>
        }
      >
        {selectedProblem && (
          <Form form={handleForm} layout="vertical">
            <Alert
              type={selectedProblem.risk_level === 'high' ? 'error' : 'warning'}
              message={`风险等级: ${RISK_LABELS[selectedProblem.risk_level]}`}
              style={{ marginBottom: 16 }}
            />

            <Divider>问题描述</Divider>
            <p>{selectedProblem.description}</p>

            {selectedProblem.suggestion && (
              <>
                <Divider>整改建议</Divider>
                <p>{selectedProblem.suggestion}</p>
              </>
            )}

            <Divider>处理操作</Divider>

            <Form.Item name="handle_status" label="处理状态" rules={[{ required: true }]}>
              <Select placeholder="请选择处理状态">
                {HANDLE_STATUS_OPTIONS.map((option) => (
                  <Select.Option key={option.value} value={option.value}>
                    {option.label}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item name="ignore_reason" label="忽略原因">
              <Input.TextArea rows={3} placeholder="请输入忽略原因（仅在选择忽略时填写）" />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  )
}