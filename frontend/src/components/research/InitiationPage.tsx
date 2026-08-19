'use client'

import { useState, useEffect } from 'react'
import { App, Card, Table, Button, Drawer, Form, Input, Select, Tag, Space, Modal, Tabs, Row, Col, InputNumber, DatePicker, Upload } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, RobotOutlined, UploadOutlined } from '@ant-design/icons'
import { fetchInitiations } from '@/lib/api/client/research/rd-project'
import { deleteInitiation } from '@/actions/research/modules'
import {
  RdInitiation, RdReviewStatus, RdApprovalStatus,
  REVIEW_STATUS_LABELS, APPROVAL_STATUS_LABELS,
} from '@/types/research/rd-project'
import dayjs from 'dayjs'
import { createInitiation, updateInitiation } from '@/actions/research/rd-project'

interface Props { projectId: string }

const reviewStatusOptions = Object.entries(REVIEW_STATUS_LABELS).map(([value, label]) => ({ value, label }))
const approvalStatusOptions = Object.entries(APPROVAL_STATUS_LABELS).map(([value, label]) => ({ value, label }))

const reviewColorMap: Record<string, string> = {
  pending: 'default',
  approved: 'success',
  rejected: 'error',
}

const approvalColorMap: Record<string, string> = {
  pending: 'default',
  approved: 'success',
  rejected: 'error',
}

export function InitiationPage({ projectId }: Props) {
  const { message: msgApi } = App.useApp()
  const [items, setItems] = useState<RdInitiation[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<RdInitiation | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchInitiations(projectId)
      setItems(data)
    } catch (e: any) {
      msgApi.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [projectId])

  const openCreate = () => {
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({
      review_status: 'pending',
      approval_status: 'pending',
      application_date: dayjs(),
    })
    setDrawerOpen(true)
  }

  const openEdit = (record: RdInitiation) => {
    setEditingRecord(record)
    form.setFieldsValue({
      project_background: record.project_background,
      market_analysis: record.market_analysis,
      technical_feasibility: record.technical_feasibility,
      expected_outcomes: record.expected_outcomes,
      application_date: record.application_date ? dayjs(record.application_date) : undefined,
      // resource_requirements JSON
      rr_personnel: (record.resource_requirements as any)?.personnel || '',
      rr_equipment: (record.resource_requirements as any)?.equipment || '',
      rr_budget: (record.resource_requirements as any)?.budget || '',
      // timeline_plan JSON
      tp_start: (record.timeline_plan as any)?.start || '',
      tp_milestones: (record.timeline_plan as any)?.milestones || '',
      tp_target_filing: (record.timeline_plan as any)?.target_filing || '',
      // risk_assessment JSON
      ra_technical: (record.risk_assessment as any)?.technical || '',
      ra_regulatory: (record.risk_assessment as any)?.regulatory || '',
      ra_commercial: (record.risk_assessment as any)?.commercial || '',
      ra_mitigation: (record.risk_assessment as any)?.mitigation || '',
      // review
      review_status: record.review_status,
      review_date: record.review_date ? dayjs(record.review_date) : undefined,
      review_comments: record.review_comments,
      review_score: record.review_score,
      // approval
      approval_status: record.approval_status,
      approval_date: record.approval_date ? dayjs(record.approval_date) : undefined,
      approval_comments: record.approval_comments,
      notes: record.notes,
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      const payload = {
        project_background: values.project_background,
        market_analysis: values.market_analysis,
        technical_feasibility: values.technical_feasibility,
        expected_outcomes: values.expected_outcomes,
        application_date: values.application_date?.format('YYYY-MM-DD') || null,
        resource_requirements: {
          personnel: values.rr_personnel,
          equipment: values.rr_equipment,
          budget: values.rr_budget,
        },
        timeline_plan: {
          start: values.tp_start,
          milestones: values.tp_milestones,
          target_filing: values.tp_target_filing,
        },
        risk_assessment: {
          technical: values.ra_technical,
          regulatory: values.ra_regulatory,
          commercial: values.ra_commercial,
          mitigation: values.ra_mitigation,
        },
        domestic_filing_content: values.filing_content,
      }

      if (editingRecord) {
        await updateInitiation(editingRecord.id, payload)
        msgApi.success('更新成功')
      } else {
        await createInitiation(projectId, payload as any)
        msgApi.success('创建成功')
      }
      setDrawerOpen(false)
      loadData()
    } catch (e: any) {
      if (e.errorFields) return
      msgApi.error(e.message || '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteInitiation(id)
      msgApi.success('删除成功')
      loadData()
    } catch (e: any) {
      msgApi.error(e.message || '删除失败')
    }
  }

  const columns = [
    {
      title: '项目背景',
      dataIndex: 'project_background',
      key: 'project_background',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '申请日期',
      dataIndex: 'application_date',
      key: 'application_date',
      width: 120,
      render: (text: string) => text ? dayjs(text).format('YYYY-MM-DD') : '-',
    },
    {
      title: '评审状态',
      dataIndex: 'review_status',
      key: 'review_status',
      width: 100,
      render: (status: RdReviewStatus) => (
        <Tag color={reviewColorMap[status]}>{REVIEW_STATUS_LABELS[status]}</Tag>
      ),
    },
    {
      title: '评审评分',
      dataIndex: 'review_score',
      key: 'review_score',
      width: 90,
      render: (score: number) => score ? `${score}/10` : '-',
    },
    {
      title: '批准状态',
      dataIndex: 'approval_status',
      key: 'approval_status',
      width: 100,
      render: (status: RdApprovalStatus) => (
        <Tag color={approvalColorMap[status]}>{APPROVAL_STATUS_LABELS[status]}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: RdInitiation) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const tabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: (
        <>
          <Form.Item name="project_background" label="项目背景">
            <Input.TextArea rows={4} placeholder="项目背景介绍" />
          </Form.Item>
          <Form.Item name="market_analysis" label="市场分析">
            <Input.TextArea rows={4} placeholder="市场需求、竞争格局分析" />
          </Form.Item>
          <Form.Item name="technical_feasibility" label="技术可行性分析">
            <Input.TextArea rows={4} placeholder="技术路线、关键工艺难点分析" />
          </Form.Item>
          <Form.Item name="expected_outcomes" label="预期成果">
            <Input.TextArea rows={3} placeholder="预期研发成果与目标" />
          </Form.Item>
          <Form.Item name="application_date" label="申请日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'resource',
      label: '资源与计划',
      children: (
        <>
          <Form.Item name="rr_personnel" label="人员需求">
            <Input.TextArea rows={3} placeholder="所需研发人员及分工" />
          </Form.Item>
          <Form.Item name="rr_equipment" label="设备需求">
            <Input.TextArea rows={3} placeholder="所需设备及仪器" />
          </Form.Item>
          <Form.Item name="rr_budget" label="预算">
            <Input.TextArea rows={3} placeholder="研发预算估算" />
          </Form.Item>
          <Form.Item name="tp_start" label="计划启动时间">
            <Input placeholder="如：2026年Q3" />
          </Form.Item>
          <Form.Item name="tp_milestones" label="关键里程碑">
            <Input.TextArea rows={3} placeholder="各阶段关键节点" />
          </Form.Item>
          <Form.Item name="tp_target_filing" label="目标申报时间">
            <Input placeholder="如：2027年Q2" />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'risk',
      label: '风险评估',
      children: (
        <>
          <Form.Item name="ra_technical" label="技术风险">
            <Input.TextArea rows={3} placeholder="技术方面的风险点" />
          </Form.Item>
          <Form.Item name="ra_regulatory" label="法规风险">
            <Input.TextArea rows={3} placeholder="法规政策方面的风险" />
          </Form.Item>
          <Form.Item name="ra_commercial" label="商业风险">
            <Input.TextArea rows={3} placeholder="市场/商业方面的风险" />
          </Form.Item>
          <Form.Item name="ra_mitigation" label="风险缓解措施">
            <Input.TextArea rows={3} placeholder="针对以上风险的应对方案" />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'domestic_filing',
      label: '国内申报信息',
      children: (
        <>
          <Form.Item name="filing_content" label="申报内容详情">
            <Input.TextArea rows={10} placeholder="在此填写详细的国内申报信息..." />
          </Form.Item>
          <Form.Item label="AI 辅助录入">
            <Space>
              <Button icon={<RobotOutlined />}>AI 智能识别</Button>
              <Upload>
                <Button icon={<UploadOutlined />}>上传文件</Button>
              </Upload>
            </Space>
          </Form.Item>
        </>
      ),
    },
  ]

  return (
    <>
      <Card
        title="立项申请"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建立项
          </Button>
        }
      >
        <Table
          scroll={{ x: "max-content" }}
          dataSource={items}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="small"
        />
      </Card>

      <Drawer
        title={editingRecord ? '编辑立项' : '新建立项'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={720}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSave}>保存</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Tabs items={tabItems} />
        </Form>
      </Drawer>
    </>
  )
}
