'use client'

import { useState, useEffect, use } from 'react'
import { useRouter } from 'next/navigation'
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Table,
  Tag,
  Modal,
  Form,
  Select,
  Input,
  Divider,
  Alert,
  message,
  Spin,
  Tabs,
  Popconfirm,
  Descriptions,
  Statistic,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  FileSearchOutlined,
  ExclamationCircleOutlined,
  SafetyOutlined,
  AuditOutlined,
  ReloadOutlined as ReloadIcon,
} from '@ant-design/icons'

import {
  CheckProblem,
  CheckMainDetail,
  RiskLevel,
  HandleStatus,
  HANDLE_STATUS_OPTIONS,
  CheckItemType,
} from '@/types/doc-check'

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
const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
}

// 状态文本映射
const STATUS_LABELS: Record<string, string> = {
  pending: '待处理',
  running: '校验中',
  completed: '已完成',
  failed: '已失败',
  cancelled: '已取消',
}

interface PageProps {
  params: Promise<{ id: string }>
}

export default function DocCheckDetailPage({ params }: PageProps) {
  const resolvedParams = use(params)
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [checkDetail, setCheckDetail] = useState<CheckMainDetail | null>(null)
  const [activeTab, setActiveTab] = useState<string>('duplicate')

  // 问题处理弹窗
  const [problemModalVisible, setProblemModalVisible] = useState(false)
  const [selectedProblem, setSelectedProblem] = useState<CheckProblem | null>(null)
  const [handleForm] = Form.useForm()

  // 加载详情
  const loadDetail = async () => {
    setLoading(true)
    try {
      const response = await fetch(
        `/api/v1/doc-check/records/${resolvedParams.id}`
      )
      const data = await response.json()

      if (data.code === 200) {
        setCheckDetail(data.data)
      } else {
        message.error(data.message || '加载详情失败')
      }
    } catch (error) {
      console.error('加载详情失败:', error)
      message.error('加载详情失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDetail()
  }, [resolvedParams.id])

  // 处理问题
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
        loadDetail()
      } else {
        message.error(data.message || '处理失败')
      }
    } catch (error) {
      message.error('处理失败')
    }
  }

  // 导出报告
  const handleExportReport = async () => {
    if (!checkDetail) return

    try {
      message.loading({ content: '正在生成报告...', key: 'export' })

      const response = await fetch(
        `/api/v1/doc-check/export/${checkDetail.id}?format=pdf`
      )

      const data = await response.json()

      if (data.code === 200) {
        window.open(data.data.download_url, '_blank')
        message.success({ content: '报告生成成功', key: 'export' })
      } else {
        message.error({ content: data.message || '生成失败', key: 'export' })
      }
    } catch (error) {
      message.error({ content: '生成失败', key: 'export' })
    }
  }

  // 确认通过
  const handleConfirmPass = async () => {
    if (!checkDetail) return

    try {
      const response = await fetch(
        `/api/v1/doc-check/records/${checkDetail.id}/confirm`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      )

      const data = await response.json()

      if (data.code === 200) {
        message.success('确认通过成功')
        loadDetail()
      } else {
        message.error(data.message || '确认失败')
      }
    } catch (error) {
      message.error('确认失败')
    }
  }

  // 表格列定义
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

  // 按类型筛选问题
  const getFilteredProblems = (type: CheckItemType) => {
    if (!checkDetail) return []
    return checkDetail.problems.filter((p) => p.problem_type === type)
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

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!checkDetail) {
    return (
      <div style={{ padding: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/quality/doc-check')}>
          返回列表
        </Button>
        <Alert type="error" title="未找到该记录" style={{ marginTop: 16 }} />
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/quality/doc-check')}>
          返回列表
        </Button>
      </div>

      {/* 基本信息卡片 */}
      <Card title="校验记录详情" style={{ marginBottom: 16 }}>
        <Descriptions column={4} bordered>
          <Descriptions.Item label="文件名">{checkDetail.file_name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={STATUS_COLORS[checkDetail.status]}>{STATUS_LABELS[checkDetail.status]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="总问题数">{checkDetail.total_problems}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(checkDetail.created_at).toLocaleString()}
          </Descriptions.Item>
        </Descriptions>

        <Divider />

        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="高风险问题"
              value={checkDetail.risk_high}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="中风险问题"
              value={checkDetail.risk_medium}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="低风险问题"
              value={checkDetail.risk_low}
              valueStyle={{ color: '#3f8600' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Col>
        </Row>
      </Card>

      {/* 问题列表 */}
      <Card
        title="问题列表"
        extra={
          <Space>
            <Button icon={<ReloadIcon />} onClick={loadDetail}>
              刷新
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleExportReport}>
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
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

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