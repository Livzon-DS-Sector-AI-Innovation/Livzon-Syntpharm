'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Card, Table, Button, Drawer, Form, Input, Select, Tag, Space, Popconfirm, Tabs, Row, Col } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { fetchReports } from '@/lib/api/client/research/rd-project'
import { deleteReport } from '@/actions/research/modules'
import type { components } from '@/types/generated/schema'
type RdReportCreate = Omit<components['schemas']['RdReportCreate'], 'project_id'>
import { createReport, updateReport } from '@/actions/research/rd-project'
import {
  RdReport, RdReportType, RdReportStatus,
  REPORT_TYPE_LABELS, REPORT_STATUS_LABELS, STAGE_LABELS,
} from '@/types/research/rd-project'

interface Props { projectId: string }

const typeOptions = Object.entries(REPORT_TYPE_LABELS).map(([value, label]) => ({ value, label }))
const statusOptions = Object.entries(REPORT_STATUS_LABELS).map(([value, label]) => ({ value, label }))
const stageOptions = Object.entries(STAGE_LABELS).map(([value, label]) => ({ value, label }))

const statusColorMap: Record<string, string> = {
  draft: 'default',
  in_progress: 'processing',
  reviewed: 'cyan',
  approved: 'success',
}

const typeColorMap: Record<string, string> = {
  summary: 'blue',
  stage: 'purple',
  annual: 'orange',
  final: 'green',
  custom: 'default',
}

export function ReportPage({ projectId }: Props) {
  const { message: msgApi } = App.useApp()
  const queryClient = useQueryClient()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<RdReport | null>(null)
  const [form] = Form.useForm()

  const { data: reports = [], isLoading: loading } = useQuery({
    queryKey: ['reports', projectId],
    queryFn: async () => {
      const data = await fetchReports(projectId)
      return data || []
    },
    enabled: !!projectId,
  })

  const openCreate = () => {
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({ status: 'draft', report_type: 'summary', version: 'v1.0' })
    setDrawerOpen(true)
  }

  const openEdit = (record: RdReport) => {
    setEditingRecord(record)
    form.setFieldsValue({
      title: record.title,
      report_type: record.report_type,
      stage: record.stage,
      status: record.status,
      version: record.version,
      summary: record.summary,
      content: record.content,
      kf_summary: record.key_findings?.summary || '',
      kf_data: record.key_findings?.key_data || '',
      kf_issues: record.key_findings?.issues || '',
      recommendations: record.recommendations,
      notes: record.notes,
    })
    setDrawerOpen(true)
  }

  const collectJsonFields = (values: Record<string, unknown>) => ({
    key_findings: {
      summary: values.kf_summary || '',
      key_data: values.kf_data || '',
      issues: values.kf_issues || '',
    },
  })

  const handleSave = async () => {
    const values = await form.validateFields()
    const jsonFields = collectJsonFields(values)
    const payload: RdReportCreate = {
      title: values.title,
      report_type: values.report_type,
      stage: values.stage,
      status: values.status,
      version: values.version,
      summary: values.summary,
      content: values.content,
      recommendations: values.recommendations,
      notes: values.notes,
      ...jsonFields,
    }
    try {
      if (editingRecord) {
        await updateReport(editingRecord.id, payload)
        msgApi.success('更新成功')
      } else {
        await createReport(projectId, payload)
        msgApi.success('创建成功')
      }
      setDrawerOpen(false)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['reports', projectId] })
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteReport(id)
      msgApi.success('删除成功')
      queryClient.invalidateQueries({ queryKey: ['reports', projectId] })
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const columns = [
    { title: '报告标题', dataIndex: 'title', key: 'title', width: 250, ellipsis: true },
    { title: '类型', dataIndex: 'report_type', key: 'report_type', width: 110,
      render: (v: string) => <Tag color={typeColorMap[v] || 'default'}>{REPORT_TYPE_LABELS[v as RdReportType] || v}</Tag> },
    { title: '阶段', dataIndex: 'stage', key: 'stage', width: 90,
      render: (v: string) => v ? (STAGE_LABELS[v as keyof typeof STAGE_LABELS] || v) : '-' },
    { title: '版本', dataIndex: 'version', key: 'version', width: 70 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string) => <Tag color={statusColorMap[v] || 'default'}>{REPORT_STATUS_LABELS[v as RdReportStatus] || v}</Tag> },
    { title: '摘要', dataIndex: 'summary', key: 'summary', width: 200, ellipsis: true, render: (v: string) => v || '-' },
    {
      title: '操作', key: 'action', width: 120, fixed: 'right' as const,
      render: (_: unknown, record: RdReport) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除此报告？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消">
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
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
          <Form.Item name="title" label="报告标题" rules={[{ required: true, message: '请输入报告标题' }]}>
            <Input placeholder="如：化合物A研发总结报告" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="report_type" label="报告类型" rules={[{ required: true }]}>
                <Select options={typeOptions} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="stage" label="关联阶段">
                <Select options={[{ value: '', label: '无' }, ...stageOptions]} allowClear />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="version" label="版本号">
                <Input placeholder="如：v1.0" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="status" label="状态">
            <Select options={statusOptions} />
          </Form.Item>
          <Form.Item name="summary" label="摘要">
            <Input.TextArea rows={3} placeholder="报告摘要，简要概述报告内容..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'content',
      label: '报告内容',
      children: (
        <>
          <Form.Item name="content" label="报告正文">
            <Input.TextArea rows={16} placeholder="报告正文内容...&#10;&#10;建议结构：&#10;1. 项目概述&#10;2. 研发过程&#10;3. 关键实验结果&#10;4. 数据分析&#10;5. 结论与建议" />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'findings',
      label: '关键发现',
      children: (
        <>
          <Form.Item name="kf_summary" label="关键发现总结">
            <Input.TextArea rows={4} placeholder="总结研发过程中的关键发现和重要结论..." />
          </Form.Item>
          <Form.Item name="kf_data" label="关键数据">
            <Input.TextArea rows={4} placeholder="列出关键实验数据，如：&#10;- 最优工艺条件：温度60℃，时间2h，收率87.5%&#10;- 产品纯度：99.2%&#10;- 杂质总量：0.15%" />
          </Form.Item>
          <Form.Item name="kf_issues" label="发现的问题">
            <Input.TextArea rows={3} placeholder="研发过程中发现的问题和风险..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'conclusion',
      label: '结论与建议',
      children: (
        <>
          <Form.Item name="recommendations" label="建议与结论">
            <Input.TextArea rows={6} placeholder="基于研发结果提出的建议、后续工作计划、风险评估等..." />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="其他备注..." />
          </Form.Item>
        </>
      ),
    },
  ]

  return (
    <div>
      <Card
        title="研发报告"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建报告</Button>}
      >
        <Table
          dataSource={reports}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1000 }}
        />
      </Card>

      <Drawer
        title={editingRecord ? '编辑研发报告' : '新建研发报告'}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); form.resetFields() }}
        styles={{ wrapper: { width: 780 } }}
        extra={
          <Space>
            <Button onClick={() => { setDrawerOpen(false); form.resetFields() }}>取消</Button>
            <Button type="primary" onClick={handleSave}>保存</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Tabs items={tabItems} />
        </Form>
      </Drawer>
    </div>
  )
}
