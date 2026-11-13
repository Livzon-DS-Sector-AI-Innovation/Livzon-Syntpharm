'use client'

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'

import {
  createWorkActivityHazardAction,
  deleteWorkActivityHazardAction,
  exportWorkActivityHazardsAction,
  updateWorkActivityHazardAction,
} from '@/actions/risk-grading'
import { fetchRiskGradingOptions, fetchWorkActivityHazards } from '@/lib/api/client/risk-grading'
import {
  STANDARD_LINKS,
  computeRiskValue,
  deriveEvaluationGrade,
  toValueLabelOptions,
  type WorkActivityHazard,
  type WorkActivityHazardCreate,
  type WorkActivityHazardExportParams,
} from '@/types/safety/risk-grading'

const QUERY_KEY = 'work-activity-hazards'
const OPTIONS_QUERY_KEY = 'risk-grading-options'

function formatDecimal(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (!Number.isFinite(number)) return value
  return String(Number(number.toFixed(6)))
}

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

function StandardLink({ href, label, field }: { href: string; label: string; field: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${field}：打开 ${label} 国家标准全文`}
      title={`查看 ${label}`}
      style={{ marginLeft: 6 }}
    >
      <QuestionCircleOutlined />
    </a>
  )
}

export default function WorkActivityLedgerClient() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<WorkActivityHazardCreate>()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editing, setEditing] = useState<WorkActivityHazard | null>(null)
  const [exporting, setExporting] = useState(false)

  const [controlLevel, setControlLevel] = useState<string>()
  const [evaluationGrade, setEvaluationGrade] = useState<number>()
  const [residualRisk, setResidualRisk] = useState<string>()
  const [keyword, setKeyword] = useState<string>()
  const [keywordInput, setKeywordInput] = useState('')

  const exportParams = useMemo<WorkActivityHazardExportParams>(
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
  const controlMeasureOptions = useMemo(() => options?.control_measures ?? [], [options])
  const residualRiskOptions = useMemo(() => options?.residual_risks ?? [], [options])
  const executionLevelOptions = useMemo(() => options?.execution_levels ?? [], [options])
  const controlMeasureLabels = useMemo(
    () => Object.fromEntries(controlMeasureOptions.map((item) => [item.value, item.label])),
    [controlMeasureOptions],
  )
  const executionLevelLabels = useMemo(
    () => Object.fromEntries(executionLevelOptions.map((item) => [item.value, item.label])),
    [executionLevelOptions],
  )
  const gradeOptions = useMemo(
    () =>
      [...new Set((options?.grade_thresholds ?? []).map((item) => item.grade))]
        .sort((a, b) => a - b)
        .map((grade) => ({ value: grade, label: `${grade}级` })),
    [options],
  )
  const likelihoodRange = options?.likelihood_range
  const exposureRange = options?.exposure_range
  const consequenceRange = options?.consequence_range
  const likelihoodMin = likelihoodRange ? Number(likelihoodRange.min) : undefined
  const likelihoodMax = likelihoodRange ? Number(likelihoodRange.max) : undefined
  const exposureMin = exposureRange ? Number(exposureRange.min) : undefined
  const exposureMax = exposureRange ? Number(exposureRange.max) : undefined
  const consequenceMin = consequenceRange ? Number(consequenceRange.min) : undefined
  const consequenceMax = consequenceRange ? Number(consequenceRange.max) : undefined
  const minRiskValue = options ? Number(options.min_risk_value) : undefined

  const { data, isLoading } = useQuery({
    queryKey: [QUERY_KEY, page, pageSize, controlLevel, evaluationGrade, residualRisk, keyword],
    queryFn: () =>
      fetchWorkActivityHazards({
        page,
        page_size: pageSize,
        ...exportParams,
      }),
  })

  const rows = data?.data ?? []
  const total = data?.meta.total ?? 0

  const watchedL = Form.useWatch('likelihood_l', form)
  const watchedE = Form.useWatch('exposure_e', form)
  const watchedC = Form.useWatch('consequence_c', form)

  const previewD = useMemo(() => {
    const l = Number(watchedL)
    const e = Number(watchedE)
    const c = Number(watchedC)
    if (!watchedL || !watchedE || !watchedC || !Number.isFinite(l * e * c)) return null
    return computeRiskValue(l, e, c)
  }, [watchedL, watchedE, watchedC])

  const previewGrade = previewD === null ? null : deriveEvaluationGrade(previewD, options?.grade_thresholds)
  const belowGate = previewD !== null && minRiskValue !== undefined && previewD <= minRiskValue

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

  const openEdit = (record: WorkActivityHazard) => {
    setEditing(record)
    form.setFieldsValue({
      position_location: record.position_location,
      area_activity: record.area_activity,
      hazard_name_or_event: record.hazard_name_or_event,
      possible_harm: record.possible_harm,
      hazard_type: record.hazard_type,
      likelihood_l: Number(record.likelihood_l),
      exposure_e: Number(record.exposure_e),
      consequence_c: Number(record.consequence_c),
      control_measures: record.control_measures,
      residual_risk: record.residual_risk,
      control_level: record.control_level,
      execution_level: record.execution_level,
    })
    setOpen(true)
  }

  const closeEditor = () => {
    setOpen(false)
    setEditing(null)
    form.resetFields()
  }

  const handleSubmit = async () => {
    let values: WorkActivityHazardCreate
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    const d = computeRiskValue(Number(values.likelihood_l), Number(values.exposure_e), Number(values.consequence_c))
    if (minRiskValue !== undefined && d <= minRiskValue) {
      message.error(`风险值 D=${formatDecimal(String(d))} 必须大于 ${minRiskValue}，不允许提交`)
      return
    }
    setSubmitting(true)
    try {
      if (editing) {
        await updateWorkActivityHazardAction(editing.id, values)
        message.success('更新成功')
      } else {
        await createWorkActivityHazardAction(values)
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

  const handleDelete = async (record: WorkActivityHazard) => {
    try {
      await deleteWorkActivityHazardAction(record.id)
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
      const { blob, filename } = await exportWorkActivityHazardsAction(exportParams)
      downloadBlob(blob, filename)
      message.success('导出成功')
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : '导出失败')
    } finally {
      setExporting(false)
    }
  }

  const columns: ColumnsType<WorkActivityHazard> = [
    { title: '岗位/地点', dataIndex: 'position_location', width: 160, fixed: 'left' },
    { title: '区域/活动', dataIndex: 'area_activity', width: 160 },
    { title: '危险源名称或潜在事件', dataIndex: 'hazard_name_or_event', width: 220 },
    { title: '可能导致的危害', dataIndex: 'possible_harm', width: 220 },
    { title: '危险源类型', dataIndex: 'hazard_type', width: 180 },
    { title: 'L', dataIndex: 'likelihood_l', width: 80, render: (value: string) => formatDecimal(value) },
    { title: 'E', dataIndex: 'exposure_e', width: 80, render: (value: string) => formatDecimal(value) },
    { title: 'C', dataIndex: 'consequence_c', width: 80, render: (value: string) => formatDecimal(value) },
    { title: 'D（风险值）', dataIndex: 'risk_value_d', width: 110, render: (value: string) => formatDecimal(value) },
    {
      title: '评价级别',
      dataIndex: 'evaluation_grade',
      width: 100,
      render: (_value: number, record) => <Tag color="blue">{record.evaluation_grade_label}</Tag>,
    },
    {
      title: '控制措施',
      dataIndex: 'control_measures',
      width: 320,
      render: (value: string[]) => value.map((key) => controlMeasureLabels[key] ?? key).join('；'),
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
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">作业活动危险源台账</h1>
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
          placeholder="搜索岗位/地点、区域/活动、危险源名称等"
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

      <Table<WorkActivityHazard>
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={rows}
        scroll={{ x: 2450 }}
        locale={{ emptyText: <Empty description="暂无作业活动危险源台账记录" /> }}
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
        title={editing ? '编辑作业活动危险源' : '新建作业活动危险源'}
        open={open}
        width={880}
        onCancel={closeEditor}
        onOk={handleSubmit}
        okText="保存"
        cancelText="取消"
        confirmLoading={submitting}
        okButtonProps={{ disabled: belowGate }}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" requiredMark>
          <Form.Item
            name="position_location"
            label="岗位/地点"
            rules={[{ required: true, whitespace: true, message: '请填写岗位/地点' }]}
          >
            <Input maxLength={255} placeholder="一期自由文本，如：101车间反应岗" />
          </Form.Item>
          <Form.Item
            name="area_activity"
            label="区域/活动"
            rules={[{ required: true, whitespace: true, message: '请填写区域/活动' }]}
          >
            <Input maxLength={255} placeholder="一期自由文本，如：反应釜投料" />
          </Form.Item>
          <Form.Item
            name="hazard_name_or_event"
            label="危险源名称或潜在事件"
            rules={[{ required: true, whitespace: true, message: '请填写危险源名称或潜在事件' }]}
          >
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>
          <Form.Item
            name="possible_harm"
            label={
              <span>
                可能导致的危害
                <StandardLink
                  href={STANDARD_LINKS.possibleHarm.href}
                  label={STANDARD_LINKS.possibleHarm.label}
                  field="可能导致的危害"
                />
              </span>
            }
            rules={[{ required: true, whitespace: true, message: '请填写可能导致的危害' }]}
          >
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>
          <Form.Item
            name="hazard_type"
            label={
              <span>
                危险源类型
                <StandardLink
                  href={STANDARD_LINKS.hazardType.href}
                  label={STANDARD_LINKS.hazardType.label}
                  field="危险源类型"
                />
              </span>
            }
            rules={[{ required: true, whitespace: true, message: '请填写危险源类型' }]}
          >
            <Input.TextArea rows={2} maxLength={5000} />
          </Form.Item>

          <Space size="large" align="start" wrap>
            <Form.Item
              name="likelihood_l"
              label={likelihoodRange ? `可能性 L（${likelihoodRange.min}–${likelihoodRange.max}）` : '可能性 L'}
              rules={[
                { required: true, message: '请填写可能性 L' },
                {
                  type: 'number',
                  min: likelihoodMin,
                  max: likelihoodMax,
                  message: `可能性 L 必须在 ${likelihoodRange?.min ?? ''}–${likelihoodRange?.max ?? ''} 之间`,
                },
              ]}
            >
              <InputNumber
                min={likelihoodMin}
                max={likelihoodMax}
                step={0.1}
                precision={6}
                style={{ width: 160 }}
              />
            </Form.Item>
            <Form.Item
              name="exposure_e"
              label={exposureRange ? `发生频次 E（${exposureRange.min}–${exposureRange.max}）` : '发生频次 E'}
              rules={[
                { required: true, message: '请填写发生频次 E' },
                {
                  type: 'number',
                  min: exposureMin,
                  max: exposureMax,
                  message: `发生频次 E 必须在 ${exposureRange?.min ?? ''}–${exposureRange?.max ?? ''} 之间`,
                },
              ]}
            >
              <InputNumber min={exposureMin} max={exposureMax} step={0.1} precision={6} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item
              name="consequence_c"
              label={consequenceRange ? `后果 C（${consequenceRange.min}–${consequenceRange.max}）` : '后果 C'}
              rules={[
                { required: true, message: '请填写后果 C' },
                {
                  type: 'number',
                  min: consequenceMin,
                  max: consequenceMax,
                  message: `后果 C 必须在 ${consequenceRange?.min ?? ''}–${consequenceRange?.max ?? ''} 之间`,
                },
              ]}
            >
              <InputNumber min={consequenceMin} max={consequenceMax} step={1} precision={6} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item label="风险值 D（自动计算）">
              <Input
                readOnly
                value={previewD === null ? '' : formatDecimal(String(previewD))}
                placeholder="由 L×E×C 自动计算"
                style={{ width: 160 }}
              />
            </Form.Item>
            <Form.Item label="评价级别（自动计算）">
              <Input
                readOnly
                value={previewGrade === null ? '' : `${previewGrade}级`}
                placeholder="按 D 值自动对应"
                style={{ width: 160 }}
              />
            </Form.Item>
          </Space>

          {belowGate && (
            <Alert
              type="error"
              showIcon
              style={{ marginBottom: 16 }}
              message={`风险值 D=${formatDecimal(String(previewD))} 不满足 D > ${minRiskValue ?? ''}，不允许提交`}
            />
          )}

          <Form.Item
            name="control_measures"
            label="控制措施"
            rules={[{ required: true, type: 'array', min: 1, message: '请至少选择一项控制措施' }]}
          >
            <Select mode="multiple" options={controlMeasureOptions} placeholder="可多选" />
          </Form.Item>
          <Form.Item
            name="residual_risk"
            label="残余风险"
            rules={[{ required: true, message: '请选择残余风险' }]}
          >
            <Select options={residualRiskOptions} placeholder="仅 1–3 级" />
          </Form.Item>
          <Form.Item
            name="control_level"
            label="管控层级"
            rules={[{ required: true, message: '请选择管控层级' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={departmentOptions}
              placeholder="选择部门"
            />
          </Form.Item>
          <Form.Item
            name="execution_level"
            label="执行层级"
            rules={[{ required: true, message: '请选择执行层级' }]}
          >
            <Select options={executionLevelOptions} placeholder="车间 / 班组长" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
