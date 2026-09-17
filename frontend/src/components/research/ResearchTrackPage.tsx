'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {App, Card, Table, Button, Drawer, Form, Input, Select, Tag, Space, Popconfirm, Tabs, Row, Col, Descriptions, Timeline, Modal, DatePicker} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, HistoryOutlined, ExperimentOutlined, FileTextOutlined, DownloadOutlined } from '@ant-design/icons'
import {fetchTracks, fetchTrackDetail} from '@/lib/api/client/research/rd-project'
import { publishConclusionVersion } from '@/actions/research/rd-project'
import { deleteTrack, deleteFinding } from '@/actions/research/modules'
import {
  RdResearchTrack, RdResearchFinding,
  RdTrackType, RdTrackStatus, RdFindingType, RdFindingConfidence,
  TRACK_TYPE_LABELS, STAGE_LABELS,
} from '@/types/research/rd-project'
import dayjs from 'dayjs'
import { createTrack, updateTrack, createFinding, updateFinding } from '@/actions/research/rd-project'


// JSON structure interfaces for ResearchTrackPage
interface ExperimentConditions {
  temperature?: string
  solvent?: string
  time?: string
  ph?: string
}

interface MaterialsUsed {
  reagents?: string
  quantities?: string
}

interface EquipmentUsed {
  instruments?: string
  models?: string
}

interface SpectraRefs {
  hplc?: string
  nmr?: string
  xrd?: string
  ms?: string
}

interface AnalyticalResults {
  purity?: string
  impurities?: string
  yield?: string
}
interface Props { projectId: string; trackTypeFilter?: string }

const typeOptions = Object.entries(TRACK_TYPE_LABELS).map(([value, label]) => ({ value, label }))
const statusOptions = [
  { value: 'active', label: '进行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'completed', label: '已完成' },
  { value: 'archived', label: '已归档' },
]
const priorityOptions = [
  { value: 'low', label: '低' },
  { value: 'normal', label: '普通' },
  { value: 'high', label: '高' },
  { value: 'urgent', label: '紧急' },
]
const findingTypeOptions = [
  { value: 'identification', label: '识别' },
  { value: 'classification', label: '分类' },
  { value: 'control_strategy', label: '控制策略' },
  { value: 'characterization', label: '表征' },
]
const confidenceOptions = [
  { value: 'preliminary', label: '初步' },
  { value: 'confirmed', label: '已确认' },
  { value: 'final', label: '最终' },
]

const statusColorMap: Record<string, string> = {
  active: 'processing',
  paused: 'warning',
  completed: 'success',
  archived: 'default',
}

const confidenceColorMap: Record<string, string> = {
  preliminary: 'orange',
  confirmed: 'blue',
  final: 'green',
}

const typeColorMap: Record<string, string> = {
  impurity: 'red',
  crystal_form: 'purple',
  stability: 'cyan',
  quality_standard: 'blue',
  custom: 'default',
}

export function ResearchTrackPage({ projectId, trackTypeFilter }: Props) {
  const { message: msgApi, modal: _modal } = App.useApp()
  const queryClient = useQueryClient()
  
  // Track detail
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null)
  
  // Create/Edit track drawer
  const [trackDrawerOpen, setTrackDrawerOpen] = useState(false)
  const [editingTrack, setEditingTrack] = useState<RdResearchTrack | null>(null)
  const [trackForm] = Form.useForm()
  
  // Finding drawer
  const [findingDrawerOpen, setFindingDrawerOpen] = useState(false)
  const [editingFinding, setEditingFinding] = useState<RdResearchFinding | null>(null)
  const [findingForm] = Form.useForm()
  
  // Conclusion version modal
  const [conclusionModalOpen, setConclusionModalOpen] = useState(false)
  const [conclusionForm] = Form.useForm()

  const { data: tracks = [], isLoading: loading } = useQuery({
    queryKey: ['research-tracks', projectId, trackTypeFilter],
    queryFn: async () => {
      const data = await fetchTracks(projectId)
      const filtered = trackTypeFilter ? data.filter(t => t.type === trackTypeFilter) : data
      return filtered || []
    },
    enabled: !!projectId,
  })

  const { data: selectedTrack = null } = useQuery({
    queryKey: ['track-detail', selectedTrackId],
    queryFn: async () => {
      if (!selectedTrackId) return null
      return await fetchTrackDetail(selectedTrackId)
    },
    enabled: !!selectedTrackId,
  })

  const handleExport = () => {
    window.open(`/api/v1/research/export/tracks?project_id=${projectId}`, '_blank')
  }

  const loadTrackDetail = (trackId: string) => {
    setSelectedTrackId(trackId)
  }

  const openCreateTrack = () => {
    setEditingTrack(null)
    trackForm.resetFields()
    trackForm.setFieldsValue({ status: 'active', priority: 'normal', type: 'impurity' })
    setTrackDrawerOpen(true)
  }

  const openEditTrack = (track: RdResearchTrack) => {
    setEditingTrack(track)
    trackForm.setFieldsValue({
      name: track.name,
      type: track.type,
      description: track.description,
      status: track.status,
      priority: track.priority,
    })
    setTrackDrawerOpen(true)
  }

  const handleSaveTrack = async () => {
    try {
      const values = await trackForm.validateFields()
      if (editingTrack) {
        await updateTrack(editingTrack.id, values)
        msgApi.success('更新成功')
      } else {
        await createTrack(projectId, values)
        msgApi.success('创建成功')
      }
      setTrackDrawerOpen(false)
      queryClient.invalidateQueries({ queryKey: ['research-tracks', projectId] })
      if (selectedTrack && editingTrack?.id === selectedTrack.id) {
        loadTrackDetail(selectedTrack.id)
      }
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const handleDeleteTrack = async (id: string) => {
    try {
      await deleteTrack(id)
      msgApi.success('删除成功')
      if (selectedTrack?.id === id) setSelectedTrackId(null)
      queryClient.invalidateQueries({ queryKey: ['research-tracks', projectId] })
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  // Finding operations
  const openCreateFinding = () => {
    setEditingFinding(null)
    findingForm.resetFields()
    findingForm.setFieldsValue({ confidence: 'preliminary', finding_type: 'identification' })
    setFindingDrawerOpen(true)
  }

  const openEditFinding = (finding: RdResearchFinding) => {
    setEditingFinding(finding)
    findingForm.setFieldsValue({
      finding_type: finding.finding_type,
      conclusion: finding.conclusion,
      confidence: finding.confidence,
      experiment_date: finding.experiment_date ? dayjs(finding.experiment_date) : undefined,
      operator: finding.operator,
      observations: finding.observations,
      notes: finding.notes,
      // JSON fields
      ec_temperature: (finding.experiment_conditions as ExperimentConditions)?.temperature || '',
      ec_solvent: (finding.experiment_conditions as ExperimentConditions)?.solvent || '',
      ec_time: (finding.experiment_conditions as ExperimentConditions)?.time || '',
      ec_ph: (finding.experiment_conditions as ExperimentConditions)?.ph || '',
      mu_reagents: (finding.materials_used as MaterialsUsed)?.reagents || '',
      mu_quantities: (finding.materials_used as MaterialsUsed)?.quantities || '',
      eu_instruments: (finding.equipment_used as EquipmentUsed)?.instruments || '',
      eu_models: (finding.equipment_used as EquipmentUsed)?.models || '',
      sr_hplc: (finding.spectra_refs as SpectraRefs)?.hplc || '',
      sr_nmr: (finding.spectra_refs as SpectraRefs)?.nmr || '',
      sr_xrd: (finding.spectra_refs as SpectraRefs)?.xrd || '',
      sr_ms: (finding.spectra_refs as SpectraRefs)?.ms || '',
      ar_purity: (finding.analytical_results as AnalyticalResults)?.purity || '',
      ar_impurities: (finding.analytical_results as AnalyticalResults)?.impurities || '',
      ar_yield: (finding.analytical_results as AnalyticalResults)?.yield || '',
      // data JSON
      data_summary: finding.data ? JSON.stringify(finding.data, null, 2) : '',
    })
    setFindingDrawerOpen(true)
  }

  const handleSaveFinding = async () => {
    try {
      const values = await findingForm.validateFields()
      const payload = {
        finding_type: values.finding_type,
        conclusion: values.conclusion,
        confidence: values.confidence,
        experiment_date: values.experiment_date?.format('YYYY-MM-DD') || null,
        operator: values.operator,
        observations: values.observations,
        notes: values.notes,
        experiment_conditions: {
          temperature: values.ec_temperature,
          solvent: values.ec_solvent,
          time: values.ec_time,
          ph: values.ec_ph,
        },
        materials_used: {
          reagents: values.mu_reagents,
          quantities: values.mu_quantities,
        },
        equipment_used: {
          instruments: values.eu_instruments,
          models: values.eu_models,
        },
        spectra_refs: {
          hplc: values.sr_hplc,
          nmr: values.sr_nmr,
          xrd: values.sr_xrd,
          ms: values.sr_ms,
        },
        analytical_results: {
          purity: values.ar_purity,
          impurities: values.ar_impurities,
          yield: values.ar_yield,
        },
        data: values.data_summary ? (() => { try { return JSON.parse(values.data_summary) } catch { return { raw: values.data_summary } } })() : null,
      }

      if (editingFinding) {
        await updateFinding(editingFinding.id, payload)
        msgApi.success('更新成功')
      } else if (selectedTrack) {
        await createFinding(selectedTrack.id, payload)
        msgApi.success('创建成功')
      }
      setFindingDrawerOpen(false)
      if (selectedTrack) loadTrackDetail(selectedTrack.id)
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const handleDeleteFinding = async (id: string) => {
    try {
      await deleteFinding(id)
      msgApi.success('删除成功')
      if (selectedTrack) loadTrackDetail(selectedTrack.id)
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  // Conclusion version
  const openConclusionModal = () => {
    conclusionForm.resetFields()
    conclusionForm.setFieldsValue({
      confidence: 'preliminary',
      conclusion: selectedTrack?.current_conclusion || '',
    })
    setConclusionModalOpen(true)
  }

  const handlePublishConclusion = async () => {
    try {
      const values = await conclusionForm.validateFields()
      if (!selectedTrack) return
      await publishConclusionVersion(selectedTrack.id, {
        conclusion: values.conclusion,
        confidence: values.confidence,
        change_summary: values.change_summary,
      })
      msgApi.success('结论版本发布成功')
      setConclusionModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['track-detail', selectedTrack.id] })
      queryClient.invalidateQueries({ queryKey: ['research-tracks', projectId] })
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return
      msgApi.error(e instanceof Error ? e.message : '发布失败')
    }
  }

  // Track list columns
  const trackColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: RdResearchTrack) => (
        <a onClick={() => loadTrackDetail(record.id)} style={{ fontWeight: 500 }}>{text}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: RdTrackType) => (
        <Tag color={typeColorMap[type]}>{TRACK_TYPE_LABELS[type] || type}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: RdTrackStatus) => (
        <Tag color={statusColorMap[status]}>{status === 'active' ? '进行中' : status === 'paused' ? '已暂停' : status === 'completed' ? '已完成' : '已归档'}</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (p: string) => <Tag color={p === 'urgent' ? 'red' : p === 'high' ? 'orange' : 'blue'}>{p === 'urgent' ? '紧急' : p === 'high' ? '高' : p === 'normal' ? '普通' : '低'}</Tag>,
    },
    {
      title: '结论版本',
      dataIndex: 'conclusion_version',
      key: 'conclusion_version',
      width: 90,
      render: (v: number) => v > 0 ? `v${v}` : '-',
    },
    {
      title: '置信度',
      dataIndex: 'conclusion_confidence',
      key: 'conclusion_confidence',
      width: 90,
      render: (c: RdFindingConfidence | null) => c ? <Tag color={confidenceColorMap[c]}>{c === 'preliminary' ? '初步' : c === 'confirmed' ? '已确认' : '最终'}</Tag> : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: RdResearchTrack) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEditTrack(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDeleteTrack(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // Finding columns
  const findingColumns = [
    {
      title: '类型',
      dataIndex: 'finding_type',
      key: 'finding_type',
      width: 100,
      render: (v: RdFindingType | null) => {
        const labels: Record<string, string> = { identification: '识别', classification: '分类', control_strategy: '控制策略', characterization: '表征' }
        return v ? labels[v] || v : '-'
      },
    },
    {
      title: '结论',
      dataIndex: 'conclusion',
      key: 'conclusion',
      ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 90,
      render: (c: RdFindingConfidence) => <Tag color={confidenceColorMap[c]}>{c === 'preliminary' ? '初步' : c === 'confirmed' ? '已确认' : '最终'}</Tag>,
    },
    {
      title: '实验日期',
      dataIndex: 'experiment_date',
      key: 'experiment_date',
      width: 110,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD') : '-',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 60,
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: RdResearchFinding) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEditFinding(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDeleteFinding(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const findings = selectedTrack?.findings || []
  const conclusionHistory = selectedTrack?.conclusion_history || []

  // Detail panel
  const detailPanel = selectedTrack ? (
    <Card
      title={
        <Space>
          <span>{selectedTrack.name}</span>
          <Tag color={typeColorMap[selectedTrack.type]}>{TRACK_TYPE_LABELS[selectedTrack.type] || selectedTrack.type}</Tag>
          <Tag color={statusColorMap[selectedTrack.status]}>{selectedTrack.status === 'active' ? '进行中' : selectedTrack.status === 'paused' ? '已暂停' : selectedTrack.status === 'completed' ? '已完成' : '已归档'}</Tag>
        </Space>
      }
      extra={
        <Space>
          <Button icon={<HistoryOutlined />} onClick={openConclusionModal}>发布结论</Button>
          <Button icon={<EditOutlined />} onClick={() => openEditTrack(selectedTrack)}>编辑</Button>
          <Button onClick={() => setSelectedTrackId(null)}>返回列表</Button>
        </Space>
      }
    >
      <Tabs items={[
        {
          key: 'overview',
          label: '概览',
          children: (
            <>
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="研究项类型">{TRACK_TYPE_LABELS[selectedTrack.type] || selectedTrack.type}</Descriptions.Item>
                <Descriptions.Item label="优先级">{selectedTrack.priority}</Descriptions.Item>
                <Descriptions.Item label="状态">{selectedTrack.status}</Descriptions.Item>
                <Descriptions.Item label="结论版本">{selectedTrack.conclusion_version > 0 ? `v${selectedTrack.conclusion_version}` : '-'}</Descriptions.Item>
                <Descriptions.Item label="置信度">{selectedTrack.conclusion_confidence ? <Tag color={confidenceColorMap[selectedTrack.conclusion_confidence]}>{selectedTrack.conclusion_confidence}</Tag> : '-'}</Descriptions.Item>
                <Descriptions.Item label="活跃阶段">{selectedTrack.active_stages?.map(s => <Tag key={s}>{STAGE_LABELS[s as keyof typeof STAGE_LABELS] || s}</Tag>) || '-'}</Descriptions.Item>
                <Descriptions.Item label="描述" span={2}>{selectedTrack.description || '-'}</Descriptions.Item>
                <Descriptions.Item label="当前结论" span={2}>
                  {selectedTrack.current_conclusion || <span style={{ color: '#999' }}>暂无结论</span>}
                </Descriptions.Item>
              </Descriptions>
            </>
          ),
        },
        {
          key: 'findings',
          label: `研究发现 (${findings.length})`,
          children: (
            <Card
              size="small"
              title={<Space><ExperimentOutlined />研究发现列表</Space>}
              extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreateFinding}>添加发现</Button>}
            >
              <Table
                scroll={{ x: "max-content" }}
                dataSource={findings}
                columns={findingColumns}
                rowKey="id"
                size="small"
                pagination={false}
              />
            </Card>
          ),
        },
        {
          key: 'conclusions',
          label: `结论历史 (${conclusionHistory.length})`,
          children: (
            <Card
              size="small"
              title={<Space><FileTextOutlined />结论版本历史</Space>}
              extra={<Button size="small" icon={<PlusOutlined />} onClick={openConclusionModal}>发布新版本</Button>}
            >
              {conclusionHistory.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无结论版本记录</div>
              ) : (
                <Timeline items={conclusionHistory.map(v => ({
                  color: v.confidence === 'final' ? 'green' : v.confidence === 'confirmed' ? 'blue' : 'orange',
                  children: (
                    <div>
                      <div style={{ fontWeight: 500 }}>
                        v{v.version} <Tag color={confidenceColorMap[v.confidence]}>{v.confidence === 'preliminary' ? '初步' : v.confidence === 'confirmed' ? '已确认' : '最终'}</Tag>
                        <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>{v.created_at ? dayjs(v.created_at).format('YYYY-MM-DD HH:mm') : ''}</span>
                      </div>
                      <div style={{ margin: '4px 0' }}>{v.conclusion || '无结论'}</div>
                      {v.change_summary && <div style={{ color: '#666', fontSize: 12 }}>变更说明：{v.change_summary}</div>}
                    </div>
                  ),
                }))} />
              )}
            </Card>
          ),
        },
      ]} />
    </Card>
  ) : null

  // Finding drawer tabs
  const findingTabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: (
        <>
          <Form.Item name="finding_type" label="发现类型" rules={[{ required: true }]}>
            <Select options={findingTypeOptions} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="experiment_date" label="实验日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="operator" label="操作人">
                <Input placeholder="实验操作人" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="observations" label="实验现象/观察">
            <Input.TextArea rows={3} placeholder="实验过程中的现象和观察结果" />
          </Form.Item>
          <Form.Item name="conclusion" label="结论">
            <Input.TextArea rows={3} placeholder="本次发现的结论" />
          </Form.Item>
          <Form.Item name="confidence" label="置信度" rules={[{ required: true }]}>
            <Select options={confidenceOptions} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'conditions',
      label: '实验条件',
      children: (
        <>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="ec_temperature" label="温度">
                <Input placeholder="如：25°C" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="ec_solvent" label="溶剂">
                <Input placeholder="如：甲醇/水" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="ec_time" label="反应时间">
                <Input placeholder="如：2h" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="ec_ph" label="pH">
                <Input placeholder="如：7.0" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="mu_reagents" label="使用试剂">
            <Input.TextArea rows={2} placeholder="试剂名称及规格" />
          </Form.Item>
          <Form.Item name="mu_quantities" label="用量">
            <Input.TextArea rows={2} placeholder="各试剂用量" />
          </Form.Item>
          <Form.Item name="eu_instruments" label="使用仪器">
            <Input placeholder="如：HPLC、NMR" />
          </Form.Item>
          <Form.Item name="eu_models" label="仪器型号">
            <Input placeholder="如：Agilent 1260" />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'spectra',
      label: '图谱与检测',
      children: (
        <>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="sr_hplc" label="HPLC 图谱">
                <Input placeholder="图谱文件引用或编号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="sr_nmr" label="NMR 图谱">
                <Input placeholder="图谱文件引用或编号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="sr_xrd" label="XRD 图谱">
                <Input placeholder="图谱文件引用或编号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="sr_ms" label="MS 图谱">
                <Input placeholder="图谱文件引用或编号" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="ar_purity" label="纯度">
            <Input placeholder="如：99.5%" />
          </Form.Item>
          <Form.Item name="ar_impurities" label="杂质情况">
            <Input.TextArea rows={3} placeholder="杂质名称、含量、RRT 等" />
          </Form.Item>
          <Form.Item name="ar_yield" label="收率">
            <Input placeholder="如：85%" />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'data',
      label: '原始数据',
      children: (
        <Form.Item name="data_summary" label="结构化数据 (JSON)">
          <Input.TextArea rows={10} placeholder='{"key": "value"}' style={{ fontFamily: 'monospace' }} />
        </Form.Item>
      ),
    },
  ]

  return (
    <>
      {!selectedTrack ? (
        <Card
          title="研究项管理"
          extra={
            <Space>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateTrack}>
                新建研究项
              </Button>
            </Space>
          }
        >
          <Table
            scroll={{ x: "max-content" }}
            dataSource={tracks}
            columns={trackColumns}
            rowKey="id"
            loading={loading}
            pagination={false}
            size="small"
          />
        </Card>
      ) : detailPanel}

      {/* Track create/edit drawer */}
      <Drawer
        title={editingTrack ? '编辑研究项' : '新建研究项'}
        open={trackDrawerOpen}
        onClose={() => setTrackDrawerOpen(false)}
        size="default"
        extra={
          <Space>
            <Button onClick={() => setTrackDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSaveTrack}>保存</Button>
          </Space>
        }
      >
        <Form form={trackForm} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：杂质谱研究" />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select options={typeOptions} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="研究内容说明" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="status" label="状态">
                <Select options={statusOptions} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="priority" label="优先级">
                <Select options={priorityOptions} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Drawer>

      {/* Finding drawer */}
      <Drawer
        title={editingFinding ? '编辑研究发现' : '添加研究发现'}
        open={findingDrawerOpen}
        onClose={() => setFindingDrawerOpen(false)}
        size="large"
        extra={
          <Space>
            <Button onClick={() => setFindingDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSaveFinding}>保存</Button>
          </Space>
        }
      >
        <Form form={findingForm} layout="vertical">
          <Tabs items={findingTabItems} />
        </Form>
      </Drawer>

      {/* Conclusion version modal */}
      <Modal
        title="发布新结论版本"
        open={conclusionModalOpen}
        onOk={handlePublishConclusion}
        onCancel={() => setConclusionModalOpen(false)}
        width={600}
      >
        <Form form={conclusionForm} layout="vertical">
          <Form.Item name="conclusion" label="结论文本" rules={[{ required: true }]}>
            <Input.TextArea rows={4} placeholder="当前研究结论" />
          </Form.Item>
          <Form.Item name="confidence" label="置信度" rules={[{ required: true }]}>
            <Select options={confidenceOptions} />
          </Form.Item>
          <Form.Item name="change_summary" label="变更说明">
            <Input.TextArea rows={2} placeholder="相比上一版本的主要变化" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
