'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Card, Table, Button, Drawer, Form, Input, Select, Tag, Space, Popconfirm, Tabs, Row, Col, InputNumber, DatePicker } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { fetchInitiations } from '@/lib/api/client/research/rd-project'
import { deleteInitiation } from '@/actions/research/modules'
import {
  RdInitiation, RdReviewStatus, RdApprovalStatus,
  REVIEW_STATUS_LABELS, APPROVAL_STATUS_LABELS,
} from '@/types/research/rd-project'
import dayjs from 'dayjs'
import { createInitiation, updateInitiation } from '@/actions/research/rd-project'


// JSON structure interfaces for InitiationPage
interface ResourceRequirements {
  personnel?: string
  equipment?: string
  budget?: string
}

interface TimelinePlan {
  start?: string
  milestones?: string
  target_filing?: string
}

interface RiskAssessment {
  technical?: string
  regulatory?: string
  commercial?: string
  mitigation?: string
}
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
  const queryClient = useQueryClient()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<RdInitiation | null>(null)
  const [form] = Form.useForm()

  const { data: items = [], isLoading: loading } = useQuery({
    queryKey: ['initiations', projectId],
    queryFn: async () => {
      const data = await fetchInitiations(projectId)
      return data || []
    },
    enabled: !!projectId,
  })

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
      rr_personnel: (record.resource_requirements as ResourceRequirements)?.personnel || '',
      rr_equipment: (record.resource_requirements as ResourceRequirements)?.equipment || '',
      rr_budget: (record.resource_requirements as ResourceRequirements)?.budget || '',
      // timeline_plan JSON
      tp_start: (record.timeline_plan as TimelinePlan)?.start || '',
      tp_milestones: (record.timeline_plan as TimelinePlan)?.milestones || '',
      tp_target_filing: (record.timeline_plan as TimelinePlan)?.target_filing || '',
      // risk_assessment JSON
      ra_technical: (record.risk_assessment as RiskAssessment)?.technical || '',
      ra_regulatory: (record.risk_assessment as RiskAssessment)?.regulatory || '',
      ra_commercial: (record.risk_assessment as RiskAssessment)?.commercial || '',
      ra_mitigation: (record.risk_assessment as RiskAssessment)?.mitigation || '',
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
        review_status: values.review_status,
        review_date: values.review_date?.format('YYYY-MM-DD') || null,
        review_comments: values.review_comments,
        review_score: values.review_score,
        approval_status: values.approval_status,
        approval_date: values.approval_date?.format('YYYY-MM-DD') || null,
        approval_comments: values.approval_comments,
        notes: values.notes,
      }

      if (editingRecord) {
        await updateInitiation(editingRecord.id, payload)
        msgApi.success('更新成功')
      } else {
        await createInitiation(projectId, payload)
        msgApi.success('创建成功')
      }
      setDrawerOpen(false)
      queryClient.invalidateQueries({ queryKey: ['initiations', projectId] })
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteInitiation(id)
      msgApi.success('删除成功')
      queryClient.invalidateQueries({ queryKey: ['initiations', projectId] })
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
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
      key: 'review',
      label: '评审信息',
      children: (
        <>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="review_status" label="评审状态">
                <Select options={reviewStatusOptions} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="review_score" label="评审评分 (1-10)">
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="review_date" label="评审日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="review_comments" label="评审意见">
            <Input.TextArea rows={4} placeholder="评审意见及建议" />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'approval',
      label: '批准信息',
      children: (
        <>
          <Form.Item name="approval_status" label="批准状态">
            <Select options={approvalStatusOptions} />
          </Form.Item>
          <Form.Item name="approval_date" label="批准日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="approval_comments" label="批准意见">
            <Input.TextArea rows={4} placeholder="批准意见" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="其他备注" />
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
