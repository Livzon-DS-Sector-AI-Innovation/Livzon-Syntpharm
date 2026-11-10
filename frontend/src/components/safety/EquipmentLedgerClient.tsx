'use client'

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Empty, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons'

import {
  createEquipmentFacilityHazardAction,
  deleteEquipmentFacilityHazardAction,
  exportEquipmentFacilityHazardsAction,
  updateEquipmentFacilityHazardAction,
} from '@/actions/risk-grading'
import { fetchEquipmentFacilityHazards, fetchRiskGradingOptions } from '@/lib/api/client/risk-grading'
import {
  deriveEquipmentEvaluationGrade,
  EQUIPMENT_GRADE_TAG_STYLES,
  lookupRiskEvaluation,
  toNumberOptions,
  toValueLabelOptions,
  type EquipmentFacilityHazard,
  type EquipmentFacilityHazardCreate,
  type EquipmentFacilityHazardExportParams,
} from '@/types/safety/risk-grading'

const QUERY_KEY = 'equipment-facility-hazards'
const OPTIONS_QUERY_KEY = 'risk-grading-options'

function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export default function EquipmentLedgerClient() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<EquipmentFacilityHazardCreate>()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editing, setEditing] = useState<EquipmentFacilityHazard | null>(null)
  const [exporting, setExporting] = useState(false)

  const [controlLevel, setControlLevel] = useState<string>()
  const [evaluationGrade, setEvaluationGrade] = useState<number>()
  const [residualRisk, setResidualRisk] = useState<string>()
  const [keyword, setKeyword] = useState<string>()
  const [keywordInput, setKeywordInput] = useState('')

  const exportParams = useMemo<EquipmentFacilityHazardExportParams>(
    () => ({
      control_level: controlLevel,
      evaluation_grade: evaluationGrade,
      residual_risk: residualRisk,
      keyword,
    }),
    [controlLevel, evaluationGrade, residualRisk, keyword],
  )

  const { data: options } = useQuery({
    queryKey: [OPTIONS_QUERY_KEY],
    queryFn: fetchRiskGradingOptions,
    staleTime: Infinity,
  })

  const departmentOptions = useMemo(() => toValueLabelOptions(options?.departments ?? []), [options])
  const equipmentMeasureOptions = useMemo(() => options?.equipment_measures ?? [], [options])
  const residualRiskOptions = useMemo(() => options?.residual_risks ?? [], [options])
  const executionLevelOptions = useMemo(() => options?.execution_levels ?? [], [options])
  const likelihoodOptions = useMemo(() => toNumberOptions(options?.likelihood_levels ?? []), [options])
  const severityOptions = useMemo(() => toValueLabelOptions(options?.severity_levels ?? []), [options])
  const gradeOptions = useMemo(
    () =>
      (options?.equipment_grade_bands ?? [])
        .slice()
        .sort((a, b) => a.grade - b.grade)
        .map((band) => ({ value: band.grade, label: band.label })),
    [options],
  )
  const equipmentMeasureLabels = useMemo(
    () => Object.fromEntries(equipmentMeasureOptions.map((item) => [item.value, item.label])),
    [equipmentMeasureOptions],
  )
  const executionLevelLabels = useMemo(
    () => Object.fromEntries(executionLevelOptions.map((item) => [item.value, item.label])),
    [executionLevelOptions],
  )
  const safetyRiskMatrix = options?.safety_risk_matrix

  const { data, isLoading } = useQuery({
    queryKey: [QUERY_KEY, page, pageSize, controlLevel, evaluationGrade, residualRisk, keyword],
    queryFn: () =>
      fetchEquipmentFacilityHazards({
        page,
        page_size: pageSize,
        ...exportParams,
      }),
  })

  const rows = data?.data ?? []
  const total = data?.meta.total ?? 0

  const watchedL = Form.useWatch('likelihood_l', form)
  const watchedS = Form.useWatch('severity_s', form)

  const previewR = useMemo(() => {
    if (watchedL === undefined || watchedL === null || !watchedS) return null
    return lookupRiskEvaluation(safetyRiskMatrix, Number(watchedL), watchedS)
  }, [safetyRiskMatrix, watchedL, watchedS])

  const previewGrade = useMemo(
    () => deriveEquipmentEvaluationGrade(previewR, options?.equipment_grade_bands),
    [previewR, options],
  )

  const resetFilters = () => {
    setControlLevel(undefined)
    setEvaluationGrade(undefined)
    setResidualRisk(undefined)
    setKeyword(undefined)
    setKeywordInput('')
    setPage(1)
  }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setOpen(true)
  }

  const openEdit = (record: EquipmentFacilityHazard) => {
    setEditing(record)
    form.setFieldsValue({
      equipment_facility_tag: record.equipment_facility_tag,
      inspection_item: record.inspection_item,
      inspection_standard: record.inspection_standard,
      nonconformity_consequence: record.nonconformity_consequence,
      likelihood_l: record.likelihood_l,
      severity_s: record.severity_s,
      current_control_measures: record.current_control_measures,
      improvement_measures: record.improvement_measures,
      residual_risk: record.residual_risk,
      control_level: record.control_level,
      execution_level: record.execution_level,
      remarks: record.remarks,
    })
    setOpen(true)
  }

  const closeEditor = () => {
    setOpen(false)
    setEditing(null)
    form.resetFields()
  }

  const handleSubmit = async () => {
    let values: EquipmentFacilityHazardCreate
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    setSubmitting(true)
    try {
      if (editing) {
        await updateEquipmentFacilityHazardAction(editing.id, values)
        message.success('更新成功')
      } else {
        await createEquipmentFacilityHazardAction(values)
        message.success('创建成功')
      }
      closeEditor()
      await queryClient.invalidateQueries({ queryKey: [QUERY_KEY] })
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : editing ? '更新失败' : '创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (record: EquipmentFacilityHazard) => {
    try {
      await deleteEquipmentFacilityHazardAction(record.id)
      message.success('删除成功')
      if (rows.length === 1 && page > 1) {
        setPage(page - 1)
      }
      await queryClient.invalidateQueries({ queryKey: [QUERY_KEY] })
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : '删除失败')
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const { blob, filename } = await exportEquipmentFacilityHazardsAction(exportParams)
      downloadBlob(blob, filename)
      message.success('导出成功')
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : '导出失败')
    } finally {
      setExporting(false)
    }
  }

  const columns: ColumnsType<EquipmentFacilityHazard> = [
    { title: '设备设施/位号', dataIndex: 'equipment_facility_tag', width: 180, fixed: 'left' },
    { title: '检查项目', dataIndex: 'inspection_item', width: 200 },
    { title: '检查标准', dataIndex: 'inspection_standard', width: 240 },
    { title: '不符合标准情况及后果', dataIndex: 'nonconformity_consequence', width: 240 },
    { title: 'L（可能性）', dataIndex: 'likelihood_l', width: 100 },
    { title: 'S（严重性）', dataIndex: 'severity_s', width: 100 },
    {
      title: 'R（危险评价）',
      dataIndex: 'risk_evaluation_r',
      width: 110,
      render: (value: number) => <Tag color="volcano">{value}</Tag>,
    },
    {
      title: '评价级别',
      dataIndex: 'evaluation_grade',
      width: 100,
      render: (_value: number, record) => (
        <Tag style={EQUIPMENT_GRADE_TAG_STYLES[record.evaluation_grade]}>{record.evaluation_grade_label}</Tag>
      ),
    },
    {
      title: '现有管控措施',
      dataIndex: 'current_control_measures',
      width: 220,
      render: (value: string[]) => value.map((key) => equipmentMeasureLabels[key] ?? key).join('；'),
    },
    {
      title: '建议改进（新增）措施',
      dataIndex: 'improvement_measures',
      width: 220,
      render: (value: string[]) => value.map((key) => equipmentMeasureLabels[key] ?? key).join('；'),
    },
    {
      title: '残余风险',
      dataIndex: 'residual_risk',
      width: 130,
      render: (_value: string, record) => record.residual_risk_label,
    },
    { title: '管控层级', dataIndex: 'control_level', width: 180 },
    {
      title: '执行层级',
      dataIndex: 'execution_level',
      width: 100,
      render: (value: string) => executionLevelLabels[value] ?? value,
    },
    { title: '备注', dataIndex: 'remarks', width: 220 },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_value: unknown, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该记录？"
            description="删除后列表不再显示，但数据行保留。"
            okText="删除"
            cancelText="取消"
            onConfirm={() => handleDelete(record)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">设备设施危险源台账</h1>
        <Space>
          <Button icon={<DownloadOutlined />} loading={exporting} onClick={handleExport}>
            导出当前筛选
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建
          </Button>
        </Space>
      </div>

      <Space size="middle" wrap>
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="管控层级"
          style={{ width: 180 }}
          value={controlLevel}
          options={departmentOptions}
          onChange={(value) => {
            setControlLevel(value)
            setPage(1)
          }}
        />
        <Select
          allowClear
          placeholder="评价级别"
          style={{ width: 130 }}
          value={evaluationGrade}
          options={gradeOptions}
          onChange={(value) => {
            setEvaluationGrade(value)
            setPage(1)
          }}
        />
        <Select
          allowClear
          placeholder="残余风险"
          style={{ width: 150 }}
          value={residualRisk}
          options={residualRiskOptions}
          onChange={(value) => {
            setResidualRisk(value)
            setPage(1)
          }}
        />
        <Input.Search
          allowClear
          placeholder="搜索设备设施/位号、检查项目、检查标准等"
          style={{ width: 300 }}
          value={keywordInput}
          onChange={(event) => setKeywordInput(event.target.value)}
          onSearch={(value) => {
            setKeyword(value.trim() || undefined)
            setPage(1)
          }}
        />
        <Button icon={<ReloadOutlined />} onClick={resetFilters}>
          重置
        </Button>
      </Space>

      <Table<EquipmentFacilityHazard>
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={rows}
        scroll={{ x: 2700 }}
        locale={{ emptyText: <Empty description="暂无设备设施危险源台账记录" /> }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (count) => `共 ${count} 条`,
          onChange: (nextPage, nextPageSize) => {
            setPage(nextPage)
            setPageSize(nextPageSize)
          },
        }}
      />

      <Modal
        title={editing ? '编辑设备设施危险源' : '新建设备设施危险源'}
        open={open}
        width={880}
        onCancel={closeEditor}
        onOk={handleSubmit}
        okText="保存"
        cancelText="取消"
        confirmLoading={submitting}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" requiredMark>
          <Form.Item
            name="equipment_facility_tag"
            label="设备设施/位号"
            rules={[{ required: true, whitespace: true, message: '请填写设备设施/位号' }]}
          >
            <Input maxLength={255} placeholder="一期自由文本，如：R-101 反应釜" />
          </Form.Item>
          <Form.Item
            name="inspection_item"
            label="检查项目"
            rules={[{ required: true, whitespace: true, message: '请填写检查项目' }]}
          >
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>
          <Form.Item
            name="inspection_standard"
            label="检查标准"
            rules={[{ required: true, whitespace: true, message: '请填写检查标准' }]}
          >
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>
          <Form.Item
            name="nonconformity_consequence"
            label="不符合标准情况及后果"
            rules={[{ required: true, whitespace: true, message: '请填写不符合标准情况及后果' }]}
          >
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>

          <Space size="large" align="start" wrap>
            <Form.Item
              name="likelihood_l"
              label="可能性 L（1–5）"
              rules={[{ required: true, message: '请选择可能性 L' }]}
            >
              <Select options={likelihoodOptions} placeholder="1–5" style={{ width: 160 }} />
            </Form.Item>
            <Form.Item
              name="severity_s"
              label="严重性 S（A–E）"
              rules={[{ required: true, message: '请选择严重性 S' }]}
            >
              <Select options={severityOptions} placeholder="A–E" style={{ width: 160 }} />
            </Form.Item>
            <Form.Item label="危险评价 R（自动查表）">
              <Input
                readOnly
                value={previewR === null ? '' : String(previewR)}
                placeholder="按 L/S 查安全风险矩阵"
                style={{ width: 160 }}
              />
            </Form.Item>
            <Form.Item label="评价级别（自动计算）">
              <div style={{ minHeight: 32, display: 'flex', alignItems: 'center' }}>
                {previewGrade ? (
                  <Tag style={EQUIPMENT_GRADE_TAG_STYLES[previewGrade.grade]}>{previewGrade.label}</Tag>
                ) : (
                  <span className="text-[var(--color-muted)]">未选择 L / S</span>
                )}
              </div>
            </Form.Item>
          </Space>

          <Form.Item
            name="current_control_measures"
            label="现有管控措施"
            rules={[{ required: true, type: 'array', min: 1, message: '请至少选择一项现有管控措施' }]}
          >
            <Select mode="multiple" options={equipmentMeasureOptions} placeholder="可多选" />
          </Form.Item>
          <Form.Item
            name="improvement_measures"
            label="建议改进（新增）措施"
            rules={[{ required: true, type: 'array', min: 1, message: '请至少选择一项建议改进措施' }]}
          >
            <Select mode="multiple" options={equipmentMeasureOptions} placeholder="可多选" />
          </Form.Item>
          <Form.Item name="residual_risk" label="残余风险" rules={[{ required: true, message: '请选择残余风险' }]}>
            <Select options={residualRiskOptions} placeholder="仅 1–3 级" />
          </Form.Item>
          <Form.Item name="control_level" label="管控层级" rules={[{ required: true, message: '请选择管控层级' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={departmentOptions}
              placeholder="选择部门"
            />
          </Form.Item>
          <Form.Item name="execution_level" label="执行层级" rules={[{ required: true, message: '请选择执行层级' }]}>
            <Select options={executionLevelOptions} placeholder="车间 / 班组长" />
          </Form.Item>
          <Form.Item
            name="remarks"
            label="备注"
            rules={[{ required: true, whitespace: true, message: '请填写备注' }]}
          >
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
