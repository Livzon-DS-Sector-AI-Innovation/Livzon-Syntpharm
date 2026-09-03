'use client'

import { useEffect, useState } from 'react'
import {
  Button,
  DatePicker,
  Descriptions,
  Form,
  Input,
  Modal,
  Radio,
  Select,
  Space,
  Tag,
  TimePicker,
  message,
} from 'antd'
import { EditOutlined, CloseOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  fetchDepartments,
  fetchNewDepartments,
  fetchEmployees,
  fetchNewEmployees,
} from '@/lib/api/client/hr'
import { createTrainingSession, updateTrainingSession, sendTrainingSessionSelectTasksAction } from '@/actions/hr'
import type { TrainingSessionExtended as TrainingSession, TrainingSessionCreateInput, TrainingSessionUpdateInput, Employee } from '@/types/hr'

const TRAINING_METHODS = [
  { value: '面授', label: '面授' },
  { value: '函授', label: '函授' },
  { value: '远程教育', label: '远程教育' },
  { value: '自学', label: '自学' },
  { value: '其他', label: '其他' },
]

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'default' },
  notified: { label: '已通知', color: 'blue' },
  selecting: { label: '选择中', color: 'orange' },
  confirmed: { label: '已确认', color: 'cyan' },
  evaluated: { label: '已评估', color: 'purple' },
  archived: { label: '已归档', color: 'green' },
}

interface TrainingSessionDetailModalProps {
  open: boolean
  record: TrainingSession | null
  onClose: () => void
  onUpdated: () => void
  startEditing?: boolean
}

export default function TrainingSessionDetailModal({
  open,
  record,
  onClose,
  onUpdated,
  startEditing = false,
}: TrainingSessionDetailModalProps) {
  const [form] = Form.useForm()
  const isCreate = !record
  // Create mode or explicit startEditing: begin in edit mode; View mode: start read-only
  const [editing, setEditing] = useState(isCreate || startEditing)
  const [saving, setSaving] = useState(false)
  const [departments, setDepartments] = useState<{ value: string; label: string }[]>([])
  const [_employees, setEmployees] = useState<{ value: string; label: string }[]>([])
  const [nameToNumberMap, setNameToNumberMap] = useState<Record<string, string>>({})
  const [factory, setFactory] = useState<'old' | 'new'>('old')

  // Load departments when factory changes
  useEffect(() => {
    const fetchFn = factory === 'new' ? fetchNewDepartments : fetchDepartments
    fetchFn({ page_size: 100 }).then((res) => {
      const list = (res.data || []).map((d: { name: string }) => ({ value: d.name, label: d.name }))
      setDepartments(list)
    })
  }, [factory])

  // Reset form when modal opens
  useEffect(() => {
    if (!open) return
    if (record) {
      // View/Edit existing record
      const f = (record.factory as 'old' | 'new') || 'old'
      setFactory(f)
      form.setFieldsValue({
        factory: f,
        department: record.department,
        training_date: record.training_date ? dayjs(record.training_date) : undefined,
        subject: record.subject,
        training_time:
          record.training_time_start && record.training_time_end
            ? [dayjs(record.training_time_start, 'HH:mm'), dayjs(record.training_time_end, 'HH:mm')]
            : undefined,
        location: record.location,
        trainer: record.trainer,
        training_method: record.training_method,
        content: record.content,
        trainee_departments: record.trainee_departments || [],
        employee_names: record.employee_names || [],
        issuer_department: record.issuer_department,
        issue_date: record.issue_date ? dayjs(record.issue_date) : undefined,
        remarks: record.remarks,
      })
      setEditing(startEditing)
    } else {
      // Create mode: reset and start in edit mode
      setFactory('old')
      setEmployees([])
      setNameToNumberMap({})
      form.resetFields()
      form.setFieldsValue({
        factory: 'old',
        training_time: [dayjs('08:00', 'HH:mm'), dayjs('12:00', 'HH:mm')],
      })
      setEditing(true)
    }
  }, [open, record, form])

  const _loadEmployees = async (
    depts: string[],
    factoryOverride: 'old' | 'new' = factory,
    preselectNames: string[] = []
  ) => {
    if (!depts || depts.length === 0) {
      setEmployees([])
      setNameToNumberMap({})
      form.setFieldsValue({ employee_names: [] })
      return
    }
    const fetchFn = factoryOverride === 'new' ? fetchNewEmployees : fetchEmployees
    const all: { value: string; label: string }[] = []
    const numberMap: Record<string, string> = {}
    for (const dept of depts) {
      try {
        const res = await fetchFn({ department: dept, page_size: 100 })
        const list = (res.data || []).map((e: Employee) => ({
          value: e.name,
          label: `${e.name} (${e.employee_number || ''})`,
        }))
        all.push(...list)
        for (const e of res.data || []) {
          if (e.name && e.employee_number) {
            numberMap[e.name] = e.employee_number
          }
        }
      } catch {
        // ignore
      }
    }
    const map = new Map(all.map((e) => [e.value, e]))
    const uniqueList = Array.from(map.values())
    setEmployees(uniqueList)
    setNameToNumberMap(numberMap)
    const names = uniqueList.map((e) => e.value)
    if (preselectNames.length > 0) {
      form.setFieldsValue({ employee_names: preselectNames.filter((n) => names.includes(n)) })
    } else {
      form.setFieldsValue({ employee_names: names })
    }
  }

  const handleFactoryChange = (val: 'old' | 'new') => {
    setFactory(val)
    setEmployees([])
    setNameToNumberMap({})
    form.setFieldsValue({
      department: undefined,
      trainee_departments: [],
      employee_names: [],
    })
  }

  const handleEdit = () => setEditing(true)

  const handleCancelEdit = () => {
    if (isCreate) {
      onClose()
      return
    }
    setEditing(false)
    // Reset form to original record values
    if (record) {
      form.setFieldsValue({
        factory: record.factory as 'old' | 'new',
        department: record.department,
        training_date: record.training_date ? dayjs(record.training_date) : undefined,
        subject: record.subject,
        training_time:
          record.training_time_start && record.training_time_end
            ? [dayjs(record.training_time_start, 'HH:mm'), dayjs(record.training_time_end, 'HH:mm')]
            : undefined,
        location: record.location,
        trainer: record.trainer,
        training_method: record.training_method,
        content: record.content,
        trainee_departments: record.trainee_departments || [],
        employee_names: record.employee_names || [],
        issuer_department: record.issuer_department,
        issue_date: record.issue_date ? dayjs(record.issue_date) : undefined,
        remarks: record.remarks,
      })
    }
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (isCreate) {
        const payload: TrainingSessionCreateInput = {
          factory: values.factory || factory,
          department: values.department,
          training_date: values.training_date.format('YYYY-MM-DD'),
          subject: values.subject,
          training_time_start: values.training_time
            ? dayjs(values.training_time[0]).format('HH:mm')
            : undefined,
          training_time_end: values.training_time
            ? dayjs(values.training_time[1]).format('HH:mm')
            : undefined,
          location: values.location,
          trainer: values.trainer,
          training_method: values.training_method,
          content: values.content,
          trainee_departments: values.trainee_departments || [],
          employee_names: values.employee_names || [],
          employee_numbers: (values.employee_names || []).map((n: string) => nameToNumberMap[n]).filter(Boolean),
          issuer_department: values.issuer_department || values.department,
          issue_date: values.issue_date
            ? values.issue_date.format('YYYY-MM-DD')
            : values.training_date.format('YYYY-MM-DD'),
          remarks: values.remarks,
          status: 'draft',
        }
        // 创建培训记录
        const createRes = await createTrainingSession(payload)
        const sessionId = createRes.data?.id
        if (sessionId) {
          // 自动发送选择任务给培训专员（测试阶段默认为李文兆）
          try {
            await sendTrainingSessionSelectTasksAction(sessionId)
            message.success('创建成功，已自动发送选择任务给培训专员')
          } catch (selectErr: unknown) {
            message.warning(`创建成功，但发送选择任务失败：${(selectErr instanceof Error ? selectErr.message : '未知错误')}`)
          }
        } else {
          message.success('创建成功')
        }
      } else {
        const payload: TrainingSessionUpdateInput = {
          department: values.department,
          training_date: values.training_date.format('YYYY-MM-DD'),
          subject: values.subject,
          training_time_start: values.training_time
            ? dayjs(values.training_time[0]).format('HH:mm')
            : undefined,
          training_time_end: values.training_time
            ? dayjs(values.training_time[1]).format('HH:mm')
            : undefined,
          location: values.location,
          trainer: values.trainer,
          training_method: values.training_method,
          content: values.content,
          trainee_departments: values.trainee_departments || [],
          employee_names: values.employee_names || [],
          employee_numbers: (values.employee_names || [])
            .map((name: string) => nameToNumberMap[name])
            .filter(Boolean),
          issuer_department: values.issuer_department || values.department,
          issue_date: values.issue_date
            ? values.issue_date.format('YYYY-MM-DD')
            : values.training_date.format('YYYY-MM-DD'),
          remarks: values.remarks,
        }
        await updateTrainingSession(record!.id, payload)
        message.success('更新成功')
        setEditing(false)
      }
      onUpdated()
      if (isCreate) onClose()
    } catch (err: unknown) {
      message.error((err instanceof Error ? err.message : (isCreate ? '创建失败' : '更新失败')))
    } finally {
      setSaving(false)
    }
  }

  // ─── Title ───
  const titleNode = isCreate ? (
    '新建培训'
  ) : (
    <div className="flex items-center justify-between w-full pr-8">
      <span>
        培训详情
        <Tag color={STATUS_MAP[record?.status || 'draft']?.color} className="ml-2">
          {STATUS_MAP[record?.status || 'draft']?.label}
        </Tag>
      </span>
      {!editing ? (
        <Button type="primary" icon={<EditOutlined />} onClick={handleEdit}>
          编辑
        </Button>
      ) : (
        <Space>
          <Button icon={<CloseOutlined />} onClick={handleCancelEdit}>
            取消编辑
          </Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
            保存
          </Button>
        </Space>
      )}
    </div>
  )

  return (
    <Modal
      title={titleNode}
      open={open}
      onCancel={onClose}
      width={800}
      footer={
        isCreate ? (
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button type="primary" loading={saving} onClick={handleSave}>
              创建
            </Button>
          </Space>
        ) : null
      }
      destroyOnClose
    >
      {/* Read-only Descriptions (view mode, not editing) */}
      {!editing && record && (
        <Descriptions bordered size="small" column={2} className="mb-6">
          <Descriptions.Item label="厂区">
            {record.factory === 'new' ? <Tag color="blue">新厂</Tag> : <Tag>旧厂</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="主办部门">{record.department}</Descriptions.Item>
          <Descriptions.Item label="培训日期">{record.training_date}</Descriptions.Item>
          <Descriptions.Item label="培训主题" span={2}>
            <span className="font-medium">{record.subject}</span>
          </Descriptions.Item>
          <Descriptions.Item label="培训时间">
            {record.training_time_start && record.training_time_end
              ? `${record.training_time_start} ~ ${record.training_time_end}`
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="培训地点">{record.location || '-'}</Descriptions.Item>
          <Descriptions.Item label="培训师">{record.trainer || '-'}</Descriptions.Item>
          <Descriptions.Item label="培训方式">{record.training_method || '-'}</Descriptions.Item>
          <Descriptions.Item label="落款部门">{record.issuer_department || '-'}</Descriptions.Item>
          <Descriptions.Item label="落款日期">{record.issue_date || '-'}</Descriptions.Item>
          <Descriptions.Item label="培训内容" span={2}>
            {record.content || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="受训部门" span={2}>
            {(record.trainee_departments || []).length > 0
              ? record.trainee_departments!.join('、')
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="应出席受训人员" span={2}>
            <div className="flex flex-wrap gap-1">
              {(record.employee_names || []).length > 0
                ? (record.employee_names || []).map((name, idx) => (
                    <Tag key={idx}>{name}</Tag>
                  ))
                : '-'}
            </div>
          </Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{record.remarks || '-'}</Descriptions.Item>
        </Descriptions>
      )}

      {/* Editable form */}
      {editing && (
        <Form form={form} layout="vertical" className="mt-4">
          {/* Factory selector: always visible in create, hidden in edit (read from record) */}
          {isCreate && (
            <Form.Item label="选择厂区">
              <Radio.Group
                value={factory}
                onChange={(e) => handleFactoryChange(e.target.value)}
                options={[
                  { label: '旧厂', value: 'old' },
                  { label: '新厂', value: 'new' },
                ]}
                optionType="button"
              />
            </Form.Item>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
            <Form.Item
              name="department"
              label="主办部门"
              rules={[{ required: true, message: '请选择主办部门' }]}
            >
              <Select showSearch placeholder="选择部门" options={departments} className="w-full" />
            </Form.Item>

            <Form.Item
              name="training_date"
              label="培训日期"
              rules={[{ required: true, message: '请选择培训日期' }]}
            >
              <DatePicker className="w-full" placeholder="选择日期" />
            </Form.Item>

            <Form.Item
              name="subject"
              label="培训主题"
              rules={[{ required: true, message: '请填写培训主题' }]}
              className="md:col-span-2"
            >
              <Input placeholder="请输入培训主题，如：安全生产规范培训" />
            </Form.Item>

            <Form.Item name="training_time" label="培训时间">
              <TimePicker.RangePicker className="w-full" format="HH:mm" />
            </Form.Item>

            <Form.Item name="location" label="培训地点">
              <Input placeholder="请输入培训地点" />
            </Form.Item>

            <Form.Item name="trainer" label="培训师">
              <Input placeholder="请输入培训师姓名" />
            </Form.Item>

            <Form.Item name="training_method" label="培训方式">
              <Select showSearch placeholder="选择培训方式" options={TRAINING_METHODS} className="w-full" />
            </Form.Item>

            <Form.Item name="issuer_department" label="落款部门">
              <Input placeholder="默认为主办部门" />
            </Form.Item>

            <Form.Item name="issue_date" label="落款日期">
              <DatePicker className="w-full" placeholder="默认为培训日期" />
            </Form.Item>

            <Form.Item name="content" label="培训内容" className="md:col-span-2">
              <Input.TextArea rows={3} placeholder="请输入培训内容" />
            </Form.Item>
          </div>

          <Form.Item name="trainee_departments" label="培训人员（受训部门）">
            <Select
              mode="multiple"
              placeholder="选择受训部门（可多选）"
              options={departments}
              className="w-full"
            />
          </Form.Item>

          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="备注" />
          </Form.Item>
        </Form>
      )}
    </Modal>
  )
}
