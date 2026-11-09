'use client'

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Empty, Form, Input, Modal, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'

import { createEquipmentFacilityHazardAction } from '@/actions/risk-grading'
import { fetchEquipmentFacilityHazards } from '@/lib/api/client/risk-grading'
import {
  EQUIPMENT_MEASURE_LABELS,
  EQUIPMENT_MEASURE_OPTIONS,
  EXECUTION_LEVEL_LABELS,
  EXECUTION_LEVEL_OPTIONS,
  LIKELIHOOD_LEVEL_OPTIONS,
  RESIDUAL_RISK_OPTIONS,
  RISK_GRADING_DEPARTMENT_OPTIONS,
  SEVERITY_LEVEL_OPTIONS,
  lookupRiskEvaluation,
  type EquipmentFacilityHazard,
  type EquipmentFacilityHazardCreate,
} from '@/types/safety/risk-grading'

const QUERY_KEY = 'equipment-facility-hazards'

export default function EquipmentLedgerClient() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<EquipmentFacilityHazardCreate>()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: [QUERY_KEY, page, pageSize],
    queryFn: () => fetchEquipmentFacilityHazards({ page, page_size: pageSize }),
  })

  const rows = data?.data ?? []
  const total = data?.meta.total ?? 0

  const watchedL = Form.useWatch('likelihood_l', form)
  const watchedS = Form.useWatch('severity_s', form)

  const previewR = useMemo(() => {
    if (watchedL === undefined || watchedL === null || !watchedS) return null
    return lookupRiskEvaluation(Number(watchedL), watchedS)
  }, [watchedL, watchedS])

  const openCreate = () => {
    form.resetFields()
    setOpen(true)
  }

  const closeEditor = () => {
    setOpen(false)
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
      await createEquipmentFacilityHazardAction(values)
      message.success('创建成功')
      closeEditor()
      await queryClient.invalidateQueries({ queryKey: [QUERY_KEY] })
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : '创建失败')
    } finally {
      setSubmitting(false)
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
      title: '现有管控措施',
      dataIndex: 'current_control_measures',
      width: 220,
      render: (value: string[]) => value.map((key) => EQUIPMENT_MEASURE_LABELS[key] ?? key).join('；'),
    },
    {
      title: '建议改进（新增）措施',
      dataIndex: 'improvement_measures',
      width: 220,
      render: (value: string[]) => value.map((key) => EQUIPMENT_MEASURE_LABELS[key] ?? key).join('；'),
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
    { title: '备注', dataIndex: 'remarks', width: 220 },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">设备设施危险源台账</h1>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: [QUERY_KEY] })}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建
          </Button>
        </Space>
      </div>

      <Table<EquipmentFacilityHazard>
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={rows}
        scroll={{ x: 2450 }}
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
        title="新建设备设施危险源"
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
              <Select options={LIKELIHOOD_LEVEL_OPTIONS} placeholder="1–5" style={{ width: 160 }} />
            </Form.Item>
            <Form.Item
              name="severity_s"
              label="严重性 S（A–E）"
              rules={[{ required: true, message: '请选择严重性 S' }]}
            >
              <Select options={SEVERITY_LEVEL_OPTIONS} placeholder="A–E" style={{ width: 160 }} />
            </Form.Item>
            <Form.Item label="危险评价 R（自动查表）">
              <Input
                readOnly
                value={previewR === null ? '' : String(previewR)}
                placeholder="按 L/S 查安全风险矩阵"
                style={{ width: 160 }}
              />
            </Form.Item>
          </Space>

          <Form.Item
            name="current_control_measures"
            label="现有管控措施"
            rules={[{ required: true, type: 'array', min: 1, message: '请至少选择一项现有管控措施' }]}
          >
            <Select mode="multiple" options={EQUIPMENT_MEASURE_OPTIONS} placeholder="可多选" />
          </Form.Item>
          <Form.Item
            name="improvement_measures"
            label="建议改进（新增）措施"
            rules={[{ required: true, type: 'array', min: 1, message: '请至少选择一项建议改进措施' }]}
          >
            <Select mode="multiple" options={EQUIPMENT_MEASURE_OPTIONS} placeholder="可多选" />
          </Form.Item>
          <Form.Item name="residual_risk" label="残余风险" rules={[{ required: true, message: '请选择残余风险' }]}>
            <Select options={RESIDUAL_RISK_OPTIONS} placeholder="仅 1–3 级" />
          </Form.Item>
          <Form.Item name="control_level" label="管控层级" rules={[{ required: true, message: '请选择管控层级' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={RISK_GRADING_DEPARTMENT_OPTIONS}
              placeholder="选择部门"
            />
          </Form.Item>
          <Form.Item name="execution_level" label="执行层级" rules={[{ required: true, message: '请选择执行层级' }]}>
            <Select options={EXECUTION_LEVEL_OPTIONS} placeholder="车间 / 班组长" />
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
