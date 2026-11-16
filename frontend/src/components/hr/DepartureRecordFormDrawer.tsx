'use client'

import { useEffect, useState } from 'react'
import { Button, DatePicker, Drawer, Form, Input, InputNumber, Radio, Select, message } from 'antd'
import dayjs from 'dayjs'

import { RemoteEmployeeSelect } from './RemoteEmployeeSelect'

import { createDepartureRecord, updateDepartureRecord } from '@/actions/hr'
import { fetchEmployeeProfileDetail } from '@/lib/api/client/hr'
import type { DepartureRecord, DepartureRecordCreateInput, DepartureRecordUpdateInput } from '@/types/hr'
import {
  EDUCATION_OPTIONS,
  GENDER_OPTIONS,
  GROUP_CLASSIFICATION_OPTIONS,
  LEAVE_CATEGORY_OPTIONS,
  PERSONNEL_IDENTITY_OPTIONS,
  POSITION_LEVEL_OPTIONS,
  toOptions,
} from './onboardingOptions'

interface DepartureRecordFormDrawerProps {
  open: boolean
  record: DepartureRecord | null
  onClose: () => void
  onSaved: () => void
}

interface FormValues {
  person_id?: string
  department_level1: string
  department_level2: string
  name: string
  gender: string
  position: string
  hire_date: dayjs.Dayjs | null
  education: string | null
  age: number | null
  position_level: string
  personnel_identity: string
  leave_date: dayjs.Dayjs
  leave_category: string
  leave_reason: string
  group_classification: string
}

function toFormValues(record: DepartureRecord): FormValues {
  return {
    person_id: record.person_id ?? undefined,
    department_level1: record.department_level1,
    department_level2: record.department_level2,
    name: record.name,
    gender: record.gender,
    position: record.position,
    hire_date: record.hire_date ? dayjs(record.hire_date) : null,
    education: record.education,
    age: record.age,
    position_level: record.position_level,
    personnel_identity: record.personnel_identity,
    leave_date: dayjs(record.leave_date),
    leave_category: record.leave_category,
    leave_reason: record.leave_reason,
    group_classification: record.group_classification,
  }
}

const required = { required: true, message: '必填' }

export default function DepartureRecordFormDrawer({
  open,
  record,
  onClose,
  onSaved,
}: DepartureRecordFormDrawerProps) {
  const [form] = Form.useForm<FormValues>()
  const editing = Boolean(record)
  const [loadingSnapshot, setLoadingSnapshot] = useState(false)
  const [manual, setManual] = useState(false)

  useEffect(() => {
    if (!open) return
    if (record) {
      form.setFieldsValue(toFormValues(record))
    } else {
      form.resetFields()
    }
  }, [open, record, form])

  const handlePersonChange = async (personId: string) => {
    setLoadingSnapshot(true)
    try {
      const detail = await fetchEmployeeProfileDetail(personId)
      form.setFieldsValue({
        department_level1: detail.department_level1_name,
        department_level2: detail.department_level2_name,
        name: detail.name,
        gender: detail.gender_label,
        position: detail.job_title_name,
        hire_date: detail.hire_date ? dayjs(detail.hire_date) : null,
        education: EDUCATION_OPTIONS.includes(detail.education) ? detail.education : null,
        age: detail.age ?? null,
      })
    } catch (error) {
      message.error(error instanceof Error ? error.message : '人员档案加载失败')
    } finally {
      setLoadingSnapshot(false)
    }
  }

  const closeDrawer = () => {
    setManual(false)
    onClose()
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const mutable = {
        position_level: values.position_level,
        personnel_identity: values.personnel_identity,
        leave_date: values.leave_date.format('YYYY-MM-DD'),
        leave_category: values.leave_category,
        leave_reason: values.leave_reason,
        education: values.education ?? undefined,
        age: values.age ?? undefined,
        group_classification: values.group_classification,
      } as DepartureRecordUpdateInput
      if (record) {
        await updateDepartureRecord(record.id, mutable)
        message.success('离职记录已更新')
      } else {
        await createDepartureRecord({
          ...(manual
            ? {
                department_level1: values.department_level1,
                department_level2: values.department_level2,
                name: values.name,
                gender: values.gender,
                position: values.position,
                hire_date: values.hire_date ? values.hire_date.format('YYYY-MM-DD') : undefined,
              }
            : { person_id: values.person_id }),
          ...mutable,
        } as DepartureRecordCreateInput)
        message.success('离职记录已创建')
      }
      onSaved()
      closeDrawer()
    } catch (error) {
      if (error instanceof Error) message.error(error.message || '保存失败')
    }
  }

  return (
    <Drawer
      open={open}
      onClose={closeDrawer}
      width={620}
      title={editing ? '编辑离职记录' : '新建离职记录'}
      destroyOnHidden
      footer={
        <div className="flex justify-end gap-2">
          <Button onClick={closeDrawer}>取消</Button>
          <Button type="primary" loading={loadingSnapshot} onClick={handleSubmit}>
            保存
          </Button>
        </div>
      }
    >
      <Form form={form} layout="vertical" requiredMark>
        <div className="grid gap-x-4 sm:grid-cols-2">
          {!editing && (
            <Form.Item label="人员来源" className="sm:col-span-2">
              <Radio.Group
                value={manual ? 'manual' : 'profile'}
                onChange={(event) => {
                  const nextManual = event.target.value === 'manual'
                  setManual(nextManual)
                  if (nextManual) {
                    form.setFieldsValue({ person_id: undefined, name: undefined, department_level1: undefined, department_level2: undefined, position: undefined, gender: undefined, hire_date: null })
                  }
                }}
                options={[
                  { label: '从员工档案选择', value: 'profile' },
                  { label: '不在档案中，手动录入', value: 'manual' },
                ]}
                optionType="button"
              />
            </Form.Item>
          )}
          {!editing && !manual && (
            <Form.Item label="选择人员" name="person_id" rules={[required]}>
              <RemoteEmployeeSelect
                onSelect={(employee) => {
                  if (employee) void handlePersonChange(employee.id)
                }}
              />
            </Form.Item>
          )}
          <Form.Item label="姓名" name="name" rules={[required]}>
            <Input disabled={!manual} />
          </Form.Item>
          <Form.Item label="一级部门" name="department_level1" rules={[required]}>
            <Input disabled={!manual} />
          </Form.Item>
          <Form.Item label="二级部门（可空）" name="department_level2">
            <Input disabled={!manual} placeholder="没有二级部门时留空" />
          </Form.Item>
          <Form.Item label="岗位" name="position" rules={[required]}>
            <Input disabled={!manual} />
          </Form.Item>
          <Form.Item label="岗位层级" name="position_level" rules={[required]}>
            <Select options={toOptions(POSITION_LEVEL_OPTIONS)} placeholder="请选择" />
          </Form.Item>
          <Form.Item label="人员身份" name="personnel_identity" rules={[required]}>
            <Select options={toOptions(PERSONNEL_IDENTITY_OPTIONS)} placeholder="请选择" />
          </Form.Item>
          <Form.Item label="性别" name="gender" rules={[required]}>
            <Select options={toOptions(GENDER_OPTIONS)} disabled={!manual} />
          </Form.Item>
          <Form.Item label="入职日期" name="hire_date" rules={[required]}>
            <DatePicker className="w-full" disabled={!manual} />
          </Form.Item>
          <Form.Item label="离职日期" name="leave_date" rules={[required]}>
            <DatePicker className="w-full" />
          </Form.Item>
          <Form.Item label="学历" name="education" rules={[required]}>
            <Select options={toOptions(EDUCATION_OPTIONS)} placeholder="请选择或由档案带入" />
          </Form.Item>
          <Form.Item label="年龄" name="age" rules={[required]}>
            <InputNumber className="w-full" min={16} max={100} precision={0} placeholder="由档案带入或手工填写" />
          </Form.Item>
          <Form.Item label="离职类别" name="leave_category" rules={[required]}>
            <Select options={toOptions(LEAVE_CATEGORY_OPTIONS)} placeholder="请选择" />
          </Form.Item>
          <Form.Item label="司龄">
            <Input
              value={record ? `${Number(record.tenure_years).toFixed(1)} 年` : ''}
              placeholder="保存后由入离职日期自动计算"
              disabled
            />
          </Form.Item>
          <Form.Item label="离职原因" name="leave_reason" rules={[required]} className="sm:col-span-2">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="集团月报表人员分类" name="group_classification" rules={[required]}>
            <Select options={toOptions(GROUP_CLASSIFICATION_OPTIONS)} placeholder="请选择" />
          </Form.Item>
        </div>
      </Form>
    </Drawer>
  )
}
