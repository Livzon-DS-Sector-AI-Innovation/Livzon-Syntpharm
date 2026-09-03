'use client'

import { useState, useEffect } from 'react'
import {App, Card, Table, Button, Drawer, Form, Input, Select, Tag, Space, Popconfirm, Tabs} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { fetchFilings } from '@/lib/api/client/research/rd-project'
import { RdRegistrationFiling } from '@/types/research/rd-project'
import { createFiling, updateFiling } from '@/actions/research/rd-project'

interface Props { projectId: string }

const statusOptions = [
  { value: 'draft', label: '草稿' },
  { value: 'in_progress', label: '编写中' },
  { value: 'submitted', label: '已提交' },
  { value: 'approved', label: '已批准' },
]

const statusColorMap: Record<string, string> = {
  draft: 'default',
  in_progress: 'processing',
  submitted: 'warning',
  approved: 'success',
}

const statusLabelMap: Record<string, string> = {
  draft: '草稿',
  in_progress: '编写中',
  submitted: '已提交',
  approved: '已批准',
}

export function RegistrationFilingPage({ projectId }: Props) {
  const { message: msgApi } = App.useApp()
  const [filings, setFilings] = useState<RdRegistrationFiling[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<RdRegistrationFiling | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchFilings(projectId)
      setFilings(data)
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [projectId])

  const openCreate = () => {
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({ status: 'draft' })
    setDrawerOpen(true)
  }

  const openEdit = (record: RdRegistrationFiling) => {
    setEditingRecord(record)
    form.setFieldsValue({
      status: record.status,
      notes: record.notes,
      ctd_m1: record.ctd_structure?.module1_admin || '',
      ctd_m2: record.ctd_structure?.module2_summaries || '',
      ctd_m3_quality: record.ctd_structure?.module3_quality || '',
      ctd_m4_nonclin: record.ctd_structure?.module4_nonclinical || '',
      ctd_m5_clin: record.ctd_structure?.module5_clinical || '',
      ctd_notes: record.ctd_structure?.notes || '',
      prog_timeline: record.filing_progress?.timeline || '',
      prog_milestones: record.filing_progress?.milestones || '',
      prog_agency: record.filing_progress?.regulatory_agency || '',
      prog_status: record.filing_progress?.current_status || '',
      prog_next: record.filing_progress?.next_steps || '',
      prog_notes: record.filing_progress?.notes || '',
      supp_deficiency: record.supplementary_docs?.deficiency_responses || '',
      supp_amendments: record.supplementary_docs?.amendments || '',
      supp_correspondence: record.supplementary_docs?.correspondence || '',
      supp_other: record.supplementary_docs?.other_docs || '',
      supp_notes: record.supplementary_docs?.notes || '',
    })
    setDrawerOpen(true)
  }

  const collectJsonFields = (values: Record<string, unknown>) => ({
    ctd_structure: {
      module1_admin: values.ctd_m1 || '',
      module2_summaries: values.ctd_m2 || '',
      module3_quality: values.ctd_m3_quality || '',
      module4_nonclinical: values.ctd_m4_nonclin || '',
      module5_clinical: values.ctd_m5_clin || '',
      notes: values.ctd_notes || '',
    },
    filing_progress: {
      timeline: values.prog_timeline || '',
      milestones: values.prog_milestones || '',
      regulatory_agency: values.prog_agency || '',
      current_status: values.prog_status || '',
      next_steps: values.prog_next || '',
      notes: values.prog_notes || '',
    },
    supplementary_docs: {
      deficiency_responses: values.supp_deficiency || '',
      amendments: values.supp_amendments || '',
      correspondence: values.supp_correspondence || '',
      other_docs: values.supp_other || '',
      notes: values.supp_notes || '',
    },
  })

  const handleSave = async () => {
    const values = await form.validateFields()
    const jsonFields = collectJsonFields(values)
    const payload = {
      status: values.status,
      notes: values.notes,
      ...jsonFields,
    }
    try {
      if (editingRecord) {
        await updateFiling(editingRecord.id, payload)
        msgApi.success('更新成功')
      } else {
        await createFiling(projectId, payload)
        msgApi.success('创建成功')
      }
      setDrawerOpen(false)
      form.resetFields()
      loadData()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      const { deleteFiling } = await import('@/actions/research/modules')
      await deleteFiling(id)
      msgApi.success('删除成功')
      loadData()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const columns = [
    { title: 'CTD 结构', dataIndex: 'ctd_structure', key: 'ctd_structure', width: 100, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '申报进度', dataIndex: 'filing_progress', key: 'filing_progress', width: 100, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '补充资料', dataIndex: 'supplementary_docs', key: 'supplementary_docs', width: 100, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag color={statusColorMap[v] || 'default'}>{statusLabelMap[v] || v}</Tag> },
    { title: '备注', dataIndex: 'notes', key: 'notes', width: 200, ellipsis: true, render: (v: string) => v || '-' },
    {
      title: '操作', key: 'action', width: 120, fixed: 'right' as const,
      render: (_: unknown, record: RdRegistrationFiling) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除此记录？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消">
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
          <Form.Item name="status" label="状态">
            <Select options={statusOptions} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="备注信息..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'ctd',
      label: 'CTD 文档结构',
      children: (
        <>
          <Form.Item name="ctd_m1" label="模块 1 - 行政信息">
            <Input.TextArea rows={3} placeholder="封面信、申请表、许可证、处方信息、包装标签等行政文件的状态和内容..." />
          </Form.Item>
          <Form.Item name="ctd_m2" label="模块 2 - CTD 概要">
            <Input.TextArea rows={3} placeholder="质量总体概要、非临床和临床概要的编写状态..." />
          </Form.Item>
          <Form.Item name="ctd_m3_quality" label="模块 3 - 质量研究">
            <Input.TextArea rows={4} placeholder="原料药/制剂的质量研究资料，包括：&#10;- 药物研发（处方工艺开发）&#10;- 原料药制造&#10;- 辅料控制&#10;- 质量标准&#10;- 稳定性研究" />
          </Form.Item>
          <Form.Item name="ctd_m4_nonclin" label="模块 4 - 非临床研究">
            <Input.TextArea rows={3} placeholder="药理学、药代动力学、毒理学研究资料状态..." />
          </Form.Item>
          <Form.Item name="ctd_m5_clin" label="模块 5 - 临床研究">
            <Input.TextArea rows={3} placeholder="临床研究报告、生物利用度、临床试验数据等..." />
          </Form.Item>
          <Form.Item name="ctd_notes" label="CTD 补充说明">
            <Input.TextArea rows={2} placeholder="CTD 文档编写的其他说明..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'progress',
      label: '申报进度',
      children: (
        <>
          <Form.Item name="prog_timeline" label="申报时间线">
            <Input.TextArea rows={3} placeholder="关键时间节点，如：&#10;2026-03: 完成资料编写&#10;2026-04: 内部审核&#10;2026-05: 提交 CDE&#10;2026-08: 预计获批" />
          </Form.Item>
          <Form.Item name="prog_milestones" label="里程碑进展">
            <Input.TextArea rows={4} placeholder="已完成的里程碑和当前进展..." />
          </Form.Item>
          <Form.Item name="prog_agency" label="申报机构">
            <Input placeholder="如：CDE（药品审评中心）、FDA、EMA" />
          </Form.Item>
          <Form.Item name="prog_status" label="当前状态">
            <Input.TextArea rows={2} placeholder="当前申报进展的详细描述..." />
          </Form.Item>
          <Form.Item name="prog_next" label="下一步计划">
            <Input.TextArea rows={3} placeholder="后续工作计划和待办事项..." />
          </Form.Item>
          <Form.Item name="prog_notes" label="进度补充说明">
            <Input.TextArea rows={2} placeholder="其他进度相关内容..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'supplementary',
      label: '补充资料',
      children: (
        <>
          <Form.Item name="supp_deficiency" label="缺陷回复">
            <Input.TextArea rows={4} placeholder="审评意见/缺陷通知的回复情况，如：&#10;第1次发补（2026-07）：已回复3/5项&#10;- 杂质研究补充：已完成&#10;- 稳定性补充：进行中&#10;- 工艺验证补充：待开始" />
          </Form.Item>
          <Form.Item name="supp_amendments" label="补充申请">
            <Input.TextArea rows={3} placeholder="已提交或计划提交的补充申请/变更说明..." />
          </Form.Item>
          <Form.Item name="supp_correspondence" label="往来函件">
            <Input.TextArea rows={3} placeholder="与审评机构的往来函件记录..." />
          </Form.Item>
          <Form.Item name="supp_other" label="其他补充文件">
            <Input.TextArea rows={3} placeholder="其他补充资料说明..." />
          </Form.Item>
          <Form.Item name="supp_notes" label="补充资料说明">
            <Input.TextArea rows={2} placeholder="其他说明..." />
          </Form.Item>
        </>
      ),
    },
  ]

  return (
    <div>
      <Card
        title="申报资料记录"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建记录</Button>}
      >
        <Table
          dataSource={filings}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ x: 800 }}
        />
      </Card>

      <Drawer
        title={editingRecord ? '编辑申报资料记录' : '新建申报资料记录'}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); form.resetFields() }}
        styles={{ wrapper: { width: 720 } }}
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
