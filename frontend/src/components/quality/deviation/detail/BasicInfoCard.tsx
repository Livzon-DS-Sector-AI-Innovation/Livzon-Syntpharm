'use client'

import { useMemo, useState } from 'react'
import { App, Button, DatePicker, Form, Input, Select, Switch } from 'antd'
import dayjs from 'dayjs'
import { updateDeviationLedger } from '@/actions/quality'
import { RemoteUserMultiSelect } from '@/components/common/RemoteUserSelect'
import { toPersonIds } from '@/lib/utils/form-person'
import {
  CrossDeptReviewerFields,
  toCrossDeptRowsPayload,
  type PersonSnapshot,
} from '../CrossDeptReviewerFields'
import type {
  DeviationLedgerDetail,
  DeviationLedgerOption,
  DeviationLedgerUpdateInput,
} from '@/types/quality'
import { SectionCard } from './SectionCard'

interface BasicInfoCardProps {
  ledger: DeviationLedgerDetail
  departmentOptions: DeviationLedgerOption[]
  onUpdated: (ledger: DeviationLedgerDetail) => void
}

interface BasicFormValues {
  title: string
  department: string
  discovery_date: dayjs.Dayjs
  discovery_time?: string
  discovery_location: string
  affected_items: string
  batch_number: string
  description: string
  handler_ids?: string[]
  needs_cross_dept_review: boolean
  cross_dept_reviewers?: {
    department: string
    investigator_ids?: string[]
    dept_head_id?: string | null
    dept_head_name?: string | null
  }[]
}

export function BasicInfoCard({
  ledger,
  departmentOptions,
  onUpdated,
}: BasicInfoCardProps) {
  const [form] = Form.useForm<BasicFormValues>()
  const { message } = App.useApp()
  const [saving, setSaving] = useState(false)
  const crossReview = Form.useWatch('needs_cross_dept_review', form)

  // 已保存人员的回显快照：调查人带头像，跨部门调查人只有姓名快照（头像走首字兜底）
  const personSnapshots = useMemo<Map<string, PersonSnapshot>>(() => {
    const map = new Map<string, PersonSnapshot>()
    for (const person of ledger.handlers ?? []) {
      map.set(person.id, { name: person.name, avatar: person.avatar_url })
    }
    for (const reviewer of ledger.cross_dept_reviewers ?? []) {
      const ids = reviewer.investigator_ids ?? []
      const names = reviewer.investigator_names ?? []
      ids.forEach((id, index) => {
        if (map.has(id)) return
        map.set(id, { name: names[index] ?? '未知人员' })
      })
      if (reviewer.dept_head_id && !map.has(reviewer.dept_head_id)) {
        map.set(reviewer.dept_head_id, { name: reviewer.dept_head_name ?? '未知人员' })
      }
    }
    return map
  }, [ledger.handlers, ledger.cross_dept_reviewers])

  // 快照与已选 UUID 同序：表单值变化后重新按 id 取名，避免删人后姓名错位
  const handlerIds = Form.useWatch<string[]>('handler_ids', form) ?? []
  const handlerLabels = handlerIds.map((id) => personSnapshots.get(id)?.name ?? '未知人员')
  const handlerAvatars = handlerIds.map((id) => personSnapshots.get(id)?.avatar ?? null)

  // pending_investigation 环节（上报人∪调查人）可动态增删改跨部门名单，其余字段后端锁定
  const canEditCrossDeptOnly = !ledger.editable && Boolean(ledger.can_edit_cross_dept)

  const handleSave = async () => {
    const values = await form.validateFields()
    const rows = values.needs_cross_dept_review ? toCrossDeptRowsPayload(values.cross_dept_reviewers ?? []) : []
    if (values.needs_cross_dept_review && rows.length === 0) {
      message.warning('开启跨部门审核后至少需要一行跨部门（部门与部门负责人必选）')
      return
    }
    const crossDeptPayload: DeviationLedgerUpdateInput = {
      needs_cross_dept_review: values.needs_cross_dept_review,
      cross_dept_reviewers: rows,
    }
    const payload: DeviationLedgerUpdateInput = canEditCrossDeptOnly
      ? crossDeptPayload
      : {
          title: values.title,
          department: values.department,
          discovery_date: values.discovery_date.format('YYYY-MM-DD'),
          discovery_time: values.discovery_time,
          discovery_location: values.discovery_location,
          affected_items: values.affected_items,
          batch_number: values.batch_number,
          description: values.description,
          handler_ids: values.handler_ids ?? [],
          ...crossDeptPayload,
        }
    setSaving(true)
    const result = await updateDeviationLedger(ledger.id, payload)
    setSaving(false)
    if (result.code === 200 && result.data) {
      message.success('基础信息已保存')
      onUpdated(result.data)
    } else {
      message.error(result.message)
    }
  }

  return (
    <SectionCard
      section="basic-info"
      ledger={ledger}
      extra={
        (ledger.editable || ledger.can_edit_cross_dept) && (
          <Button type="primary" size="small" loading={saving} onClick={handleSave}>
            保存
          </Button>
        )
      }
    >
      <Form<BasicFormValues>
        form={form}
        layout="vertical"
        disabled={!ledger.editable}
        initialValues={{
          title: ledger.title,
          department: ledger.department,
          discovery_date: dayjs(ledger.discovery_date),
          discovery_time: ledger.discovery_time ?? undefined,
          discovery_location: ledger.discovery_location,
          affected_items: ledger.affected_items,
          batch_number: ledger.batch_number,
          description: ledger.description,
          handler_ids: (ledger.handler_ids ?? []) as string[],
          needs_cross_dept_review: ledger.needs_cross_dept_review,
          cross_dept_reviewers: (ledger.cross_dept_reviewers ?? []) as BasicFormValues['cross_dept_reviewers'],
        }}
      >
        <Form.Item name="title" label="偏差名称" rules={[{ required: true, message: '请填写偏差名称' }]}>
          <Input maxLength={500} showCount />
        </Form.Item>

        <div className="grid gap-x-4 md:grid-cols-2">
          <Form.Item name="department" label="发生部门" rules={[{ required: true, message: '请选择发生部门' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={departmentOptions.map((item) => ({ value: item.value, label: item.label }))}
            />
          </Form.Item>
          <Form.Item name="discovery_date" label="发现日期" rules={[{ required: true, message: '请选择发现日期' }]}>
            <DatePicker className="w-full" />
          </Form.Item>
          <Form.Item name="discovery_time" label="发现时间">
            <Input placeholder="如 14:30" maxLength={20} />
          </Form.Item>
          <Form.Item name="discovery_location" label="发现地点">
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="affected_items" label="涉及物料">
            <Input maxLength={500} />
          </Form.Item>
          <Form.Item name="batch_number" label="涉及批次">
            <Input maxLength={255} />
          </Form.Item>
        </div>

        <Form.Item name="description" label="偏差描述">
          <Input.TextArea rows={4} maxLength={4000} showCount />
        </Form.Item>

        <Form.Item
          name="handler_ids"
          label="调查人"
          extra="调查人收到调查任务，可为多人"
          normalize={toPersonIds}
        >
          <RemoteUserMultiSelect
            placeholder="搜索姓名选择调查人，可多选"
            labels={handlerLabels}
            avatarSrcs={handlerAvatars}
            feishuBoundOnly={false}
          />
        </Form.Item>

        <div className={canEditCrossDeptOnly ? 'rounded-lg border border-[var(--color-hairline)] bg-[var(--color-surface-soft)] p-3' : undefined}>
          {canEditCrossDeptOnly && (
            <p className="mb-2 text-xs text-[var(--color-slate)]">
              调查环节中仅可维护跨部门会签名单（部门 + 调查人 + 部门负责人）；已通过的行在保存后保持通过状态。
            </p>
          )}
          <Form.Item
            name="needs_cross_dept_review"
            label="是否需要跨部门审核"
            valuePropName="checked"
            className={canEditCrossDeptOnly ? '!mb-2' : undefined}
          >
            <Switch aria-label="是否需要跨部门审核" {...(canEditCrossDeptOnly ? { disabled: false } : {})} />
          </Form.Item>

          {crossReview && (
            <CrossDeptReviewerFields
              form={form}
              departmentOptions={departmentOptions}
              personSnapshots={personSnapshots}
              unlock={canEditCrossDeptOnly}
            />
          )}
        </div>
      </Form>
    </SectionCard>
  )
}