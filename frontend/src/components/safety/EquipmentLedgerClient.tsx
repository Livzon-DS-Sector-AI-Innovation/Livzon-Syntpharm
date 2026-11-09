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
  type EquipmentFacilityHazardExportParams,
} from '@/types/safety/risk-grading'

const QUERY_KEY = 'equipment-facility-hazards'

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
  const [residualRisk, setResidualRisk] = useState<string>()
  const [keyword, setKeyword] = useState<string>()
  const [keywordInput, setKeywordInput] = useState('')

  const exportParams = useMemo<EquipmentFacilityHazardExportParams>(
    () => ({
      control_level: controlLevel,
      residual_risk: residualRisk,
      keyword,
    }),
    [controlLevel, residualRisk, keyword],
  )

  const { data, isLoading } = useQuery({
    queryKey: [QUERY_KEY, page, pageSize, controlLevel, residualRisk, keyword],
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
    return lookupRiskEvaluation(Number(watchedL), watchedS)
  }, [watchedL, watchedS])

  const resetFilters = () => {
    setControlLevel(undefined)
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
          <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: [QUERY_KEY] })}>
            刷新
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
          options={RISK_GRADING_DEPARTMENT_OPTIONS}
          onChange={(value) => {
            setControlLevel(value)
            setPage(1)
          }}
        />
        <Select
          allowClear
          placeholder="残余风险"
          style={{ width: 150 }}
          value={residualRisk}
          options={RESIDUAL_RISK_OPTIONS}
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
        scroll={{ x: 2600 }}
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
