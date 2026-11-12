'use client'

import { useEffect } from 'react'
import { Button, DatePicker, Drawer, Form, Input, InputNumber, Select, message } from 'antd'
import dayjs from 'dayjs'

import { createOnboardingRecord, updateOnboardingRecord } from '@/actions/hr'
import type { OnboardingRecord, OnboardingRecordCreateInput } from '@/types/hr'
import {
  EDUCATION_OPTIONS,
  GENDER_OPTIONS,
  GROUP_CLASSIFICATION_OPTIONS,
  JOIN_CATEGORY_OPTIONS,
  PERSONNEL_IDENTITY_OPTIONS,
  POSITION_LEVEL_OPTIONS,
  toOptions,
} from './onboardingOptions'

interface OnboardingRecordFormDrawerProps {
  open: boolean
  record: OnboardingRecord | null
  onClose: () => void
  onSaved: () => void
}

interface FormValues {
  serial_no: string
  department_level1: string
  department_level2: string
  name: string
  position: string
  position_level: string
  personnel_identity: string
  hire_date: dayjs.Dayjs
  join_category: string
  education: string
  gender: string
  age: number
  mobile: string
  group_classification: string
}

function toFormValues(record: OnboardingRecord): FormValues {
  return {
    serial_no: record.serial_no,
    department_level1: record.department_level1,
    department_level2: record.department_level2,
    name: record.name,
    position: record.position,
    position_level: record.position_level,
    personnel_identity: record.personnel_identity,
    hire_date: dayjs(record.hire_date),
    join_category: record.join_category,
    education: record.education,
    gender: record.gender,
    age: record.age,
    mobile: record.mobile,
    group_classification: record.group_classification,
  }
}

const required = { required: true, message: '必填' }

export default function OnboardingRecordFormDrawer({
  open,
  record,
  onClose,
  onSaved,
}: OnboardingRecordFormDrawerProps) {
  const [form] = Form.useForm<FormValues>()
  const editing = Boolean(record)

  useEffect(() => {
    if (!open) return
    if (record) {
      form.setFieldsValue(toFormValues(record))
    } else {
      form.resetFields()
    }
  }, [open, record, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const payload = {
        ...values,
        hire_date: values.hire_date.format('YYYY-MM-DD'),
      } as OnboardingRecordCreateInput
      if (record) {
        await updateOnboardingRecord(record.id, payload)
        message.success('入职记录已更新')
      } else {
        await createOnboardingRecord(payload)
        message.success('入职记录已创建')
      }
      onSaved()
      onClose()
    } catch (error) {
      if (error instanceof Error) message.error(error.message || '保存失败')
    }
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={620}
      title={editing ? '编辑入职记录' : '新建入职记录'}
      destroyOnHidden
      footer={
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSubmit}>
            保存
          </Button>
        </div>
      }
    >
      <Form form={form} layout="vertical" requiredMark>
        <div className="grid gap-x-4 sm:grid-cols-2">
          <Form.Item label="流水号" name="serial_no" rules={[required]}>
            <Input placeholder="如 260001" />
          </Form.Item>
          <Form.Item label="姓名" name="name" rules={[required]}>
            <Input />
          </Form.Item>
          <Form.Item label="一级部门" name="department_level1" rules={[required]}>
            <Input />
          </Form.Item>
          <Form.Item label="二级部门" name="department_level2" rules={[required]}>
            <Input />
          </Form.Item>
          <Form.Item label="岗位" name="position" rules={[required]}>
            <Input />
          </Form.Item>
          <Form.Item label="岗位层级" name="position_level" rules={[required]}>
            <Select options={toOptions(POSITION_LEVEL_OPTIONS)} placeholder="请选择" />
          </Form.Item>
          <Form.Item label="人员身份" name="personnel_identity" rules={[required]}>
            <Select options={toOptions(PERSONNEL_IDENTITY_OPTIONS)} placeholder="请选择" />
          </Form.Item>
          <Form.Item label="入职日期" name="hire_date" rules={[required]}>
            <DatePicker className="w-full" />
          </Form.Item>
          <Form.Item label="入职类别" name="join_category" rules={[required]}>
            <Select options={toOptions(JOIN_CATEGORY_OPTIONS)} placeholder="请选择" />
          </Form.Item>
          <Form.Item label="学历" name="education" rules={[required]}>
            <Select options={toOptions(EDUCATION_OPTIONS)} placeholder="请选择" />
          </Form.Item>
          <Form.Item label="性别" name="gender" rules={[required]}>
            <Select options={toOptions(GENDER_OPTIONS)} placeholder="请选择" />
          </Form.Item>
          <Form.Item label="年龄" name="age" rules={[required]}>
            <InputNumber className="w-full" min={16} max={100} precision={0} />
          </Form.Item>
          <Form.Item label="手机号码" name="mobile" rules={[required]}>
            <Input />
          </Form.Item>
          <Form.Item label="集团月报表人员分类" name="group_classification" rules={[required]}>
            <Select options={toOptions(GROUP_CLASSIFICATION_OPTIONS)} placeholder="请选择" />
          </Form.Item>
        </div>
      </Form>
    </Drawer>
  )
}
