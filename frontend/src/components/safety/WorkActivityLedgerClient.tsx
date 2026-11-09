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
  Select,
  Space,
  Table,
  Tag,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, QuestionCircleOutlined } from '@ant-design/icons'

import { createWorkActivityHazardAction } from '@/actions/risk-grading'
import { fetchWorkActivityHazards } from '@/lib/api/client/risk-grading'
import {
  CONTROL_MEASURE_LABELS,
  CONTROL_MEASURE_OPTIONS,
  EXECUTION_LEVEL_LABELS,
  EXECUTION_LEVEL_OPTIONS,
  RESIDUAL_RISK_OPTIONS,
  RISK_GRADING_DEPARTMENT_OPTIONS,
  STANDARD_LINKS,
  computeRiskValue,
  deriveEvaluationGrade,
  type WorkActivityHazard,
  type WorkActivityHazardCreate,
} from '@/types/safety/risk-grading'

const QUERY_KEY = 'work-activity-hazards'

function formatDecimal(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (!Number.isFinite(number)) return value
  return String(Number(number.toFixed(6)))
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

  const { data, isLoading } = useQuery({
    queryKey: [QUERY_KEY, page, pageSize],
    queryFn: () => fetchWorkActivityHazards({ page, page_size: pageSize }),
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

  const previewGrade = previewD === null ? null : deriveEvaluationGrade(previewD)
  const belowGate = previewD !== null && previewD <= 20

  const openCreate = () => {
    form.resetFields()
    setOpen(true)
  }

  const closeCreate = () => {
    setOpen(false)
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
    if (d <= 20) {
      message.error(`风险值 D=${formatDecimal(String(d))} 必须大于 20，不允许提交`)
      return
    }
    setSubmitting(true)
    try {
      await createWorkActivityHazardAction(values)
      message.success('创建成功')
      closeCreate()
      await queryClient.invalidateQueries({ queryKey: [QUERY_KEY] })
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : '创建失败')
    } finally {
      setSubmitting(false)
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
      render: (value: string[]) => value.map((key) => CONTROL_MEASURE_LABELS[key] ?? key).join('；'),
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
      render: (value: string) => EXECUTION_LEVEL_LABELS[value] ?? value,
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">作业活动危险源台账</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建
        </Button>
      </div>

      <Table<WorkActivityHazard>
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={rows}
        scroll={{ x: 2300 }}
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
        title="新建作业活动危险源"
        open={open}
        width={880}
        onCancel={closeCreate}
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
              label="可能性 L（0.1–10）"
              rules={[
                { required: true, message: '请填写可能性 L' },
                { type: 'number', min: 0.1, max: 10, message: '可能性 L 必须在 0.1–10 之间' },
              ]}
            >
              <InputNumber min={0.1} max={10} step={0.1} precision={2} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item
              name="exposure_e"
              label="发生频次 E（0.5–10）"
              rules={[
                { required: true, message: '请填写发生频次 E' },
                { type: 'number', min: 0.5, max: 10, message: '发生频次 E 必须在 0.5–10 之间' },
              ]}
            >
              <InputNumber min={0.5} max={10} step={0.1} precision={2} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item
              name="consequence_c"
              label="后果 C（1–100）"
              rules={[
                { required: true, message: '请填写后果 C' },
                { type: 'number', min: 1, max: 100, message: '后果 C 必须在 1–100 之间' },
              ]}
            >
              <InputNumber min={1} max={100} step={1} precision={2} style={{ width: 160 }} />
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
              message={`风险值 D=${formatDecimal(String(previewD))} 不满足 D > 20，不允许提交`}
            />
          )}

          <Form.Item
            name="control_measures"
            label="控制措施"
            rules={[{ required: true, type: 'array', min: 1, message: '请至少选择一项控制措施' }]}
          >
            <Select mode="multiple" options={CONTROL_MEASURE_OPTIONS} placeholder="可多选" />
          </Form.Item>
          <Form.Item
            name="residual_risk"
            label="残余风险"
            rules={[{ required: true, message: '请选择残余风险' }]}
          >
            <Select options={RESIDUAL_RISK_OPTIONS} placeholder="仅 1–3 级" />
          </Form.Item>
          <Form.Item
            name="control_level"
            label="管控层级"
            rules={[{ required: true, message: '请选择管控层级' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={RISK_GRADING_DEPARTMENT_OPTIONS}
              placeholder="选择部门"
            />
          </Form.Item>
          <Form.Item
            name="execution_level"
            label="执行层级"
            rules={[{ required: true, message: '请选择执行层级' }]}
          >
            <Select options={EXECUTION_LEVEL_OPTIONS} placeholder="车间 / 班组长" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
