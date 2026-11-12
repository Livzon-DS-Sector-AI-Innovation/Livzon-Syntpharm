'use client'

import { useState } from 'react'
import { App, Button, Checkbox, DatePicker, Form, Input, Select, Space, Upload } from 'antd'
import { DeleteOutlined, PlusOutlined, UploadOutlined, WarningOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'
import {
  appendDeviationInvestigationRecord,
  submitDeviationInvestigation,
  uploadDeviationAttachment,
} from '@/actions/quality'
import type { DeviationInvestigationInput, DeviationLedgerDetail } from '@/types/quality'

const { TextArea } = Input

interface CapaRowValue {
  summary?: string
  executor?: string
  due?: Dayjs
}

interface FormValues {
  nonconformity_description: string
  root_cause_analysis: string
  risk_assessment: string
  has_urgent?: boolean
  urgent_measures?: string
  capa_proposals?: CapaRowValue[]
  attachment_file_ids?: string[]
}

interface InvestigationRecordFormProps {
  ledger: DeviationLedgerDetail
  /** submit=提交调查（流转审核）；append=追加记录（不流转） */
  mode: 'submit' | 'append'
  /** 提交/追加成功：宿主收起表单并刷新 */
  onSubmitted: (ledger: DeviationLedgerDetail) => void
  /** 仅台账数据变化（如上传新附件）：宿主刷新但不收起表单 */
  onLedgerChange: (ledger: DeviationLedgerDetail) => void
  onCancel: () => void
}

/** 单文件上限 20MB，与台账上传一致 */
const MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024

/**
 * 结构化调查记录表单：「提交调查报告」与「追加记录」共用。
 * 顺序：不符合事项描述 / 根本原因分析 / 风险评估（必填）→ CAPA 多行
 * →「有紧急处理措施」（勾选后必填并以黄色警示块展示）→ 记录附件（引用台账 file_id）。
 */
export function InvestigationRecordForm({ ledger, mode, onSubmitted, onLedgerChange, onCancel }: InvestigationRecordFormProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm<FormValues>()
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const hasUrgent = Form.useWatch('has_urgent', form)
  const attachments = ledger.attachments ?? []

  const handleSubmit = async (values: FormValues) => {
    const capaRows = values.capa_proposals ?? []
    const body: DeviationInvestigationInput = {
      nonconformity_description: values.nonconformity_description.trim(),
      root_cause_analysis: values.root_cause_analysis.trim(),
      risk_assessment: values.risk_assessment.trim(),
      urgent_measures: values.has_urgent ? (values.urgent_measures ?? '').trim() : null,
      capa_proposals: capaRows.map((row, index) => ({
        sequence: index + 1,
        summary: (row.summary ?? '').trim(),
        executor: row.executor?.trim() || null,
        expected_completion_date: row.due ? row.due.format('YYYY-MM-DD') : null,
      })),
      attachment_file_ids: values.attachment_file_ids ?? [],
    }
    setBusy(true)
    const result =
      mode === 'submit'
        ? await submitDeviationInvestigation(ledger.id, body)
        : await appendDeviationInvestigationRecord(ledger.id, body)
    setBusy(false)
    if (result.code === 200 && result.data) {
      message.success(mode === 'submit' ? '调查已提交，进入部门负责人审核' : '调查记录已追加，流程状态不变')
      onSubmitted(result.data)
    } else {
      message.error(result.message)
    }
  }

  /** 附件先上传到台账，再把新增 file_id 自动加入本记录引用 */
  const handleUpload = async (file: File) => {
    if (file.size > MAX_ATTACHMENT_SIZE) {
      message.error('单个文档不能超过 20MB')
      return
    }
    const knownIds = new Set(attachments.map((item) => item.file_id))
    const formData = new FormData()
    formData.append('file', file)
    setUploading(true)
    const result = await uploadDeviationAttachment(ledger.id, formData)
    setUploading(false)
    if (result.code === 200 && result.data) {
      const known = new Set(attachments.map((item) => item.file_id))
      const newIds = (result.data.attachments ?? [])
        .filter((item) => !known.has(item.file_id) && !knownIds.has(item.file_id))
        .map((item) => item.file_id)
      const current = (form.getFieldValue('attachment_file_ids') ?? []) as string[]
      form.setFieldValue('attachment_file_ids', [...current, ...newIds])
      onLedgerChange(result.data)
    } else {
      message.error(result.message)
    }
  }

  return (
    <Form<FormValues>
      form={form}
      layout="vertical"
      className="mt-3 border-t border-[var(--color-hairline)] pt-3"
      initialValues={{ capa_proposals: [{}], has_urgent: false }}
      onFinish={handleSubmit}
      scrollToFirstError
    >
      <Form.Item
        name="nonconformity_description"
        label="不符合事项描述"
        rules={[{ required: true, whitespace: true, message: '请填写不符合事项描述' }]}
      >
        <TextArea rows={3} maxLength={4000} showCount placeholder="客观描述偏差事实：发生了什么、何时何地、涉及什么" />
      </Form.Item>

      <Form.Item
        name="root_cause_analysis"
        label="根本原因分析"
        rules={[{ required: true, whitespace: true, message: '请填写根本原因分析' }]}
      >
        <TextArea rows={3} maxLength={4000} showCount placeholder="说明导致偏差的根本原因（人/机/料/法/环）" />
      </Form.Item>

      <Form.Item
        name="risk_assessment"
        label="风险评估"
        rules={[{ required: true, whitespace: true, message: '请填写风险评估' }]}
      >
        <TextArea rows={3} maxLength={4000} showCount placeholder="评估对本批次/后续批次/患者与合规的影响" />
      </Form.Item>

      <div className="mb-1 text-[13px] font-medium">改进建议（CAPA），至少一条</div>
      <Form.List
        name="capa_proposals"
        rules={[
          {
            validator: (_, value?: CapaRowValue[]) =>
              value && value.length > 0 ? Promise.resolve() : Promise.reject(new Error('至少需要一条 CAPA 建议')),
          },
        ]}
      >
        {(fields, { add, remove }) => (
          <div className="mb-2 flex flex-col gap-2">
            {fields.map((field, index) => (
              <div key={field.key} className="flex flex-col gap-2 rounded-lg border border-[var(--color-hairline)] p-2 sm:flex-row sm:items-start">
                <span className="mt-1 w-5 shrink-0 text-center text-[12px] text-[var(--color-slate)]">{index + 1}</span>
                <Form.Item
                  name={[field.name, 'summary']}
                  rules={[{ required: true, whitespace: true, message: '请填写 CAPA 内容简述' }]}
                  className="!mb-0 min-w-0 flex-1"
                >
                  <Input placeholder="CAPA 内容简述" maxLength={500} />
                </Form.Item>
                <Form.Item name={[field.name, 'executor']} className="!mb-0 w-full sm:w-[140px]">
                  <Input placeholder="执行人" maxLength={100} />
                </Form.Item>
                <Form.Item name={[field.name, 'due']} className="!mb-0 w-full sm:w-[150px]">
                  <DatePicker className="w-full" placeholder="预计完成日期" />
                </Form.Item>
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  aria-label="删除该条 CAPA"
                  onClick={() => remove(field.name)}
                  disabled={fields.length === 1}
                />
              </div>
            ))}
            <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({})}>
              增加一条 CAPA
            </Button>
          </div>
        )}
      </Form.List>

      <Form.Item name="has_urgent" valuePropName="checked" className="!mb-2">
        <Checkbox>
          <span className="inline-flex items-center gap-1 text-[13px]">
            <WarningOutlined className="text-amber-600" />
            有紧急处理措施
          </span>
        </Checkbox>
      </Form.Item>
      {hasUrgent && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3">
          <Form.Item
            name="urgent_measures"
            label={<span className="text-amber-800">紧急处理措施</span>}
            rules={[{ required: true, whitespace: true, message: '勾选后请填写紧急处理措施' }]}
            className="!mb-0"
          >
            <TextArea rows={2} maxLength={2000} showCount placeholder="为防止偏差扩大已立即采取的措施" />
          </Form.Item>
        </div>
      )}

      <Form.Item name="attachment_file_ids" label="记录附件" extra="附件先上传到台账，本记录按 file_id 引用">
        <Select
          mode="multiple"
          allowClear
          placeholder="从已上传的台账文档中选择（可先上传再选）"
          options={attachments.map((item) => ({ value: item.file_id, label: item.file_name }))}
          optionFilterProp="label"
          notFoundContent="暂无台账文档，可先上传"
        />
      </Form.Item>
      <Upload showUploadList={false} beforeUpload={(file) => { void handleUpload(file); return false }}>
        <Button size="small" icon={<UploadOutlined />} loading={uploading} className="mb-3">
          上传并挂到本记录
        </Button>
      </Upload>

      <Space className="w-full justify-end">
        <Button onClick={onCancel} disabled={busy}>
          取消
        </Button>
        <Button type="primary" htmlType="submit" loading={busy}>
          {mode === 'submit' ? '提交调查报告并进入审核' : '追加调查记录'}
        </Button>
      </Space>
    </Form>
  )
}
