'use client'

import { useState, useEffect, useCallback } from 'react'
import { App, Card, Tabs, Tag, Button, Descriptions, Table, Modal, Form, Input, Select, DatePicker, Space, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, ArrowRightOutlined } from '@ant-design/icons'
import {
  RdProject, RdMilestone, RdStageRecord, RdResearchTrack, RdResearchFinding,
  STAGE_LABELS, STAGE_ORDER,
} from '@/types/research/rd-project'
import { fetchMilestones, fetchStages, fetchStageTransitionCheck,  } from '@/lib/api/client/research/rd-project'
import { ProcessValidationPage } from './ProcessValidationPage'
import { RegistrationFilingPage } from './RegistrationFilingPage'
import { StageDeliverablesTab } from './StageDeliverablesTab'
import dayjs from 'dayjs'
import { createMilestone, updateMilestone, createStage, updateStage, doTransition } from '@/actions/research/rd-project'

interface Props { project: RdProject }

const stageColorMap: Record<string, { color: string; bg: string }> = {
  initiation: { color: '#1677ff', bg: '#e6f4ff' },
  route_dev: { color: '#7b3ff2', bg: '#e6e0f5' },
  optimization: { color: '#fa8c16', bg: '#fff7e6' },
  pilot: { color: '#13c2c2', bg: '#e6fffb' },
  validation: { color: '#52c41a', bg: '#e6f7e6' },
  filing: { color: '#eb2f96', bg: '#fff0f6' },
}

const statusColorMap: Record<string, { color: string; bg: string }> = {
  initiation: { color: '#1677ff', bg: '#e6f4ff' },
  active: { color: '#52c41a', bg: '#e6f7e6' },
  completed: { color: '#787671', bg: '#f0eeec' },
  on_hold: { color: '#fa8c16', bg: '#fff7e6' },
  terminated: { color: '#e03131', bg: '#fff1f0' },
}

export function ProjectDetailPage({ project }: Props) {
  const { modal, message: msgApi } = App.useApp()
  const [tab, setTab] = useState('overview')
  const [milestones, setMilestones] = useState<RdMilestone[]>([])
  const [stages, setStages] = useState<RdStageRecord[]>([])
  const [loading, setLoading] = useState(false)

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [m, s] = await Promise.all([
        fetchMilestones(project.id),
        fetchStages(project.id),
      ])
      setMilestones(m)
      setStages(s)
    } catch (e) {
      msgApi.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }, [project.id])

  useEffect(() => { loadAll() }, [loadAll])

  const stageCfg = stageColorMap[project.current_stage || 'initiation'] || { color: '#787671', bg: '#f0eeec' }
  const statusCfg = statusColorMap[project.status] || { color: '#787671', bg: '#f0eeec' }

  // 阶段流转
  const handleTransition = async (targetStage: string) => {
    modal.confirm({
      title: `确认阶段流转`,
      content: `将项目从 "${STAGE_LABELS[project.current_stage as keyof typeof STAGE_LABELS]}" 流转到 "${STAGE_LABELS[targetStage as keyof typeof STAGE_LABELS]}"？`,
      onOk: async () => {
        try {
          const result = await doTransition(project.id, targetStage)
          if (result.success) {
            msgApi.success('阶段流转成功')
            loadAll()
          } else {
            msgApi.error('阶段流转失败')
          }
        } catch (e: any) {
          msgApi.error(e.message || '阶段流转失败')
        }
      },
    })
  }

  const nextStage = STAGE_ORDER[STAGE_ORDER.indexOf(project.current_stage as any) + 1]

  // 里程碑表单
  const [milestoneForm] = Form.useForm()
  const [milestoneModalOpen, setMilestoneModalOpen] = useState(false)
  const handleAddMilestone = () => {
    milestoneForm.resetFields()
    setMilestoneModalOpen(true)
  }
  const handleSaveMilestone = async () => {
    const values = await milestoneForm.validateFields()
    try {
      await createMilestone(project.id, { ...values, planned_date: values.planned_date?.format('YYYY-MM-DD') })
      msgApi.success('里程碑创建成功')
      setMilestoneModalOpen(false)
      loadAll()
    } catch (e: any) { msgApi.error(e.message) }
  }

  const tabs = [
    {
      key: 'overview',
      label: '项目总览',
      children: (
        <Card>
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="品种名称">{project.name}</Descriptions.Item>
            <Descriptions.Item label="API全称">{project.api_name}</Descriptions.Item>
            <Descriptions.Item label="CAS号">{project.cas_number || '-'}</Descriptions.Item>
            <Descriptions.Item label="分子式">{project.molecular_formula || '-'}</Descriptions.Item>
            <Descriptions.Item label="分子量">{project.molecular_weight || '-'}</Descriptions.Item>
            <Descriptions.Item label="适应症">{project.indication || '-'}</Descriptions.Item>
            <Descriptions.Item label="项目类型">{project.project_type || '-'}</Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Tag color={project.priority === 'high' ? 'red' : project.priority === 'urgent' ? 'magenta' : 'blue'}>{project.priority}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="当前阶段">
              <Tag style={{ color: stageCfg.color, background: stageCfg.bg, border: 'none', fontWeight: 600 }}>{STAGE_LABELS[project.current_stage as keyof typeof STAGE_LABELS] || project.current_stage}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag style={{ color: statusCfg.color, background: statusCfg.bg, border: 'none' }}>{project.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="总体进度">{project.overall_progress != null ? `${project.overall_progress}%` : '-'}</Descriptions.Item>
            <Descriptions.Item label="开始日期">{project.start_date || '-'}</Descriptions.Item>
            <Descriptions.Item label="目标申报日期">{project.target_filing_date || '-'}</Descriptions.Item>
            <Descriptions.Item label="实际申报日期">{project.actual_filing_date || '-'}</Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>{project.notes || '-'}</Descriptions.Item>
          </Descriptions>
          {nextStage && (
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Button type="primary" icon={<ArrowRightOutlined />} onClick={() => handleTransition(nextStage)}>
                流转到 {STAGE_LABELS[nextStage as keyof typeof STAGE_LABELS]}
              </Button>
            </div>
          )}
        </Card>
      ),
    },
    {
      key: 'milestones',
      label: `里程碑 (${milestones.length})`,
      children: (
        <Card title="里程碑管理" extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleAddMilestone}>添加里程碑</Button>}>
          <Table dataSource={milestones} rowKey="id" size="small" loading={loading} pagination={false}
            columns={[
              { title: '标题', dataIndex: 'title', key: 'title' },
              { title: '类型', dataIndex: 'milestone_type', key: 'milestone_type', render: (v: string) => v || '-' },
              { title: '阶段', dataIndex: 'stage', key: 'stage', render: (v: string) => STAGE_LABELS[v as keyof typeof STAGE_LABELS] || v || '-' },
              { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{v}</Tag> },
              { title: '计划日期', dataIndex: 'planned_date', key: 'planned_date', render: (v: string) => v || '-' },
              { title: '实际日期', dataIndex: 'actual_date', key: 'actual_date', render: (v: string) => v || '-' },
              { title: '决策', dataIndex: 'decision', key: 'decision', render: (v: string) => v ? <Tag color={v === 'go' ? 'green' : v === 'no_go' ? 'red' : 'orange'}>{v}</Tag> : '-' },
            ]}
          />
        </Card>
      ),
    },
    {
      key: 'stages',
      label: `阶段记录 (${stages.length})`,
      children: (
        <Card title="阶段记录">
          <Table dataSource={stages} rowKey="id" size="small" loading={loading} pagination={false}
            columns={[
              { title: '阶段', dataIndex: 'stage', key: 'stage', render: (v: string) => STAGE_LABELS[v as keyof typeof STAGE_LABELS] || v },
              { title: '版本', dataIndex: 'version', key: 'version' },
              { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{v}</Tag> },
              { title: '开始时间', dataIndex: 'started_at', key: 'started_at', render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-' },
              { title: '完成时间', dataIndex: 'completed_at', key: 'completed_at', render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-' },
              { title: '转段评审', dataIndex: 'gate_review_status', key: 'gate_review_status', render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
            ]}
          />
        </Card>
      ),
    },
    {
      key: 'deliverables',
      label: '阶段交付物',
      children: <StageDeliverablesTab projectId={project.id} currentStage={project.current_stage} />,
    },
    {
      key: 'validation',
      label: '工艺验证',
      children: <ProcessValidationPage projectId={project.id} />,
    },
    {
      key: 'filing',
      label: '申报资料',
      children: <RegistrationFilingPage projectId={project.id} />,
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>{project.name}</h1>
          <p style={{ color: '#666', margin: '4px 0 0 0' }}>{project.api_name} {project.cas_number && `| CAS: ${project.cas_number}`}</p>
        </div>
      </div>
      <Tabs activeKey={tab} onChange={setTab} items={tabs} />

      {/* 里程碑弹窗 */}
      <Modal title="添加里程碑" open={milestoneModalOpen} onOk={handleSaveMilestone} onCancel={() => setMilestoneModalOpen(false)} width={500}>
        <Form form={milestoneForm} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="milestone_type" label="类型">
            <Select options={[{ value: 'gate_review', label: '转段评审' }, { value: 'decision', label: '决策点' }, { value: 'achievement', label: '成就' }]} />
          </Form.Item>
          <Form.Item name="stage" label="阶段">
            <Select options={STAGE_ORDER.map(s => ({ value: s, label: STAGE_LABELS[s as keyof typeof STAGE_LABELS] }))} />
          </Form.Item>
          <Form.Item name="planned_date" label="计划日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

    </div>
  )
}
