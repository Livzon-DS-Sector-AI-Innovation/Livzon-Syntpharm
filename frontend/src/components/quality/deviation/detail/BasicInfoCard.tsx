'use client'

import { useMemo, useState } from 'react'
import { App, Button, Card, DatePicker, Form, Input, Select, Switch } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { updateDeviationLedger } from '@/actions/quality'
import { RemoteUserSelect, type RemoteUserSelectOption } from '@/components/common/RemoteUserSelect'
import type {
  DeviationLedgerDetail,
  DeviationLedgerOption,
  DeviationLedgerUpdateInput,
} from '@/types/quality'

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
  cross_dept_reviewers?: { department: string; investigator_ids?: string[] }[]
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
  const personFallback = useMemo<RemoteUserSelectOption[]>(() => {
    const map = new Map<string, RemoteUserSelectOption>()
    for (const person of ledger.handlers ?? []) {
      map.set(person.id, { value: person.id, label: person.name, avatar: person.avatar_url })
    }
    for (const reviewer of ledger.cross_dept_reviewers ?? []) {
      const ids = reviewer.investigator_ids ?? []
      const names = reviewer.investigator_names ?? []
      ids.forEach((id, index) => {
        if (map.has(id)) return
        map.set(id, { value: id, label: names[index] ?? '未知人员', description: reviewer.department })
      })
    }
    return [...map.values()]
  }, [ledger.handlers, ledger.cross_dept_reviewers])

  const handleSave = async () => {
    const values = await form.validateFields()
    const payload: DeviationLedgerUpdateInput = {
      title: values.title,
      department: values.department,
      discovery_date: values.discovery_date.format('YYYY-MM-DD'),
      discovery_time: values.discovery_time,
      discovery_location: values.discovery_location,
      affected_items: values.affected_items,
      batch_number: values.batch_number,
      description: values.description,
      handler_ids: values.handler_ids ?? [],
      needs_cross_dept_review: values.needs_cross_dept_review,
      cross_dept_reviewers: values.needs_cross_dept_review ? (values.cross_dept_reviewers ?? []) : [],
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
    <Card
      id="basic-info"
      size="small"
      title="基本信息"
      className="scroll-mt-40 shadow-sm"
      extra={
        ledger.editable && (
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

        <Form.Item name="handler_ids" label="调查人" extra="调查人收到调查任务，可为多人">
          <RemoteUserSelect
            mode="multiple"
            placeholder="搜索姓名选择调查人，可多选"
            fallbackOptions={personFallback}
          />
        </Form.Item>

        <Form.Item name="needs_cross_dept_review" label="是否需要跨部门审核" valuePropName="checked">
          <Switch aria-label="是否需要跨部门审核" />
        </Form.Item>

        {crossReview && (
          <Form.List name="cross_dept_reviewers">
            {(fields, { add, remove }) => (
              <div className="mb-4 flex flex-col gap-2">
                {fields.map((field) => (
                  <div key={field.key} className="flex w-full flex-col gap-2 sm:flex-row sm:items-start">
                    <Form.Item
                      name={[field.name, 'department']}
                      rules={[{ required: true, message: '请选择跨部门' }]}
                      className="!mb-0 w-full sm:w-[200px]"
                    >
                      <Select
                        showSearch
                        optionFilterProp="label"
                        placeholder="跨部门"
                        options={departmentOptions.map((item) => ({ value: item.value, label: item.label }))}
                      />
                    </Form.Item>
                    <Form.Item name={[field.name, 'investigator_ids']} className="!mb-0 min-w-0 flex-1">
                      <RemoteUserSelect
                        mode="multiple"
                        placeholder="该部门参与调查人（可留空，由部门负责人审核）"
                        fallbackOptions={personFallback}
                      />
                    </Form.Item>
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => remove(field.name)}
                      aria-label="删除跨部门"
                      className="self-end sm:self-auto"
                    />
                  </div>
                ))}
                <Button
                  type="dashed"
                  icon={<PlusOutlined />}
                  onClick={() => add({ department: '', investigator_ids: [] })}
                >
                  增加跨部门
                </Button>
              </div>
            )}
          </Form.List>
        )}
      </Form>
    </Card>
  )
}