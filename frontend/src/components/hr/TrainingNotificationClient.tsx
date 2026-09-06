'use client'
import { useSearchParams } from "next/navigation"

import { useEffect, useState } from 'react'
import type { SubMenuItem } from '@/lib/menu-config'
import { App,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Select,
  Space,
  TimePicker
} from 'antd'
import {
  DownloadOutlined,
  BellOutlined,
  FileExcelOutlined,
  BookOutlined,
  SendOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useQuery } from '@tanstack/react-query'
import {
  fetchDepartments,
  fetchEmployees,
  fetchTrainingLedgerPages,
  } from '@/lib/api/client/hr'
import { createTrainingLedger, createTrainingLedgerPage, sendTrainingNotification, generateTrainingNotification, generateTrainingSignInSheet, generateTrainingEvaluation } from '@/actions/hr'
import { moduleMenus } from '@/lib/menu-config'
import type { Employee } from '@/types/hr'

const TRAINING_METHODS = [
  { value: '面授', label: '面授' },
  { value: '自学', label: '自学' },
]

const ASSESSMENT_METHODS = [
  { value: '笔试', label: '笔试' },
  { value: '问答', label: '问答' },
]

const _TD_LABEL = {
  border: '1px solid #1f2937',
  padding: '8px'
} as React.CSSProperties

/** Check whether an employee already has a dedicated training-ledger menu page (static + DB). */
async function getExistingLedgerNumbers(): Promise<Set<string>> {
  const numbers = new Set<string>()
  const hr = moduleMenus.find((m) => m.key === 'hr')
  const training = hr?.children?.find((c) => c.key === 'training')
  const trainingLedger = training?.children?.find((c) => c.key === 'training-ledger')

  function collectChildren(items: SubMenuItem[] | undefined) {
    items?.forEach((c) => {
      const match = c.path?.match(/employee_number=(\d+)/)
      if (match) numbers.add(match[1])
      if (c.children) collectChildren(c.children)
    })
  }
  if (trainingLedger?.path) {
    const match = trainingLedger.path.match(/employee_number=(\d+)/)
    if (match) numbers.add(match[1])
  }
  collectChildren(trainingLedger?.children)

  try {
    const res = await fetchTrainingLedgerPages()
    ;(res.data || []).forEach((p) => numbers.add(p.employee_number))
  } catch {
    // ignore
  }
  return numbers
}

export default function TrainingNotificationClient() {
  const { message, modal } = App.useApp()
  const [form] = Form.useForm()
  const [nameToNumberMap, setNameToNumberMap] = useState<Record<string, string>>({})
  const [submittingWord, setSubmittingWord] = useState(false)
  const [submittingExcel, setSubmittingExcel] = useState(false)
  const [_submittingEval, setSubmittingEval] = useState(false)
  const [addingToLedger, setAddingToLedger] = useState(false)
  const [sendingNotify, setSendingNotify] = useState(false)
  const [trainerDept, setTrainerDept] = useState<string | undefined>(() => {
    const dept = searchParams.get('dept')
    return dept ? decodeURIComponent(dept) : undefined
  })

  const searchParams = useSearchParams()

  const { data: departments = [] } = useQuery<{ value: string; label: string }[]>({
    queryKey: ['hr-departments-options'],
    queryFn: async () => {
      const res = await fetchDepartments({ page_size: 100 })
      return (res.data || []).map((d: { name: string }) => ({ value: d.name, label: d.name }))
    },
  })

  const { data: trainerEmployees = [] } = useQuery<{ value: string; label: string }[]>({
    queryKey: ['hr-trainer-employees', { trainerDept }],
    queryFn: async () => {
      if (!trainerDept) return []
      const res = await fetchEmployees({ department: trainerDept, page_size: 200 })
      return (res.data || []).map((e: Employee) => ({
        value: e.name,
        label: `${e.name} (${e.employee_number || ''})`,
      }))
    },
    enabled: !!trainerDept,
  })

  // 从年度计划跳转过来时，自动填入
  useEffect(() => {
    const subject = searchParams.get('subject')
    const method = searchParams.get('method')
    if (subject) {
      form.setFieldsValue({
        subject: decodeURIComponent(subject),
        training_method: method ? decodeURIComponent(method) : undefined,
        assessment_method: searchParams.get('assessment') ? decodeURIComponent(searchParams.get('assessment')!) : undefined,
      })
    }
  }, [searchParams, form])

  const loadEmployees = async (depts: string[]) => {
    if (!depts || depts.length === 0) {
      setNameToNumberMap({})
      form.setFieldsValue({ employee_names: [] })
      return
    }
    const all: { value: string; label: string }[] = []
    const numberMap: Record<string, string> = {}
    for (const dept of depts) {
      try {
        const res = await fetchEmployees({ department: dept, page_size: 100 })
        const list = (res.data || []).map((e: Employee) => ({
          value: e.name,
          label: `${e.name} (${e.employee_number || ''})`
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
    setNameToNumberMap(numberMap)
    const names = uniqueList.map((e) => e.value)
    form.setFieldsValue({ employee_names: names })
  }

  const handleExportWord = async () => {
    const values = await form.validateFields()
    const traineeDepts: string[] = values.trainee_departments || []

    setSubmittingWord(true)
    try {
      const payload = {
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
        assessment_method: values.assessment_method,
        content: values.content,
        trainee_names: traineeDepts,
        issuer_department: values.issuer_department || values.department,
        issue_date: values.issue_date ? values.issue_date.format('YYYY-MM-DD') : values.training_date.format('YYYY-MM-DD'),
      }
      await generateTrainingNotification(payload)
      message.success('培训通知已生成')
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '生成失败')
    } finally {
      setSubmittingWord(false)
    }
  }

  const handleExportExcel = async () => {
    const values = await form.validateFields()
    const traineeDepts: string[] = values.trainee_departments || []

    setSubmittingExcel(true)
    try {
      const payload = {
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
        trainee_names: traineeDepts,
      }
      await generateTrainingSignInSheet(payload)
      message.success('签到表已生成')
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '生成失败')
    } finally {
      setSubmittingExcel(false)
    }
  }

  const handleExportEval = async () => {
    const values = await form.validateFields()
    const traineeDepts: string[] = values.trainee_departments || []

    setSubmittingEval(true)
    try {
      const payload = {
        department: values.department,
        training_date: values.training_date.format('YYYY-MM-DD'),
        subject: values.subject,
        training_time_start: values.training_time
          ? dayjs(values.training_time[0]).format('HH:mm')
          : undefined,
        training_time_end: values.training_time
          ? dayjs(values.training_time[1]).format('HH:mm')
          : undefined,
        trainer: values.trainer,
        training_method: values.training_method,
        assessment_method: values.assessment_method,
        content: values.content,
        trainee_names: traineeDepts,
      }
      await generateTrainingEvaluation(payload)
      message.success('效果评估表已生成')
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '生成失败')
    } finally {
      setSubmittingEval(false)
    }
  }

  const handleSendNotification = async () => {
    const values = await form.validateFields()
    const traineeDepts: string[] = values.trainee_departments || []
    const employeeNames: string[] = values.employee_names || []

    if (employeeNames.length === 0) {
      message.warning('请至少选择一名受训人员')
      return
    }

    setSendingNotify(true)
    try {
      const payload = {
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
        trainee_names: traineeDepts,
        employee_numbers: employeeNames.map((name: string) => nameToNumberMap[name] || ""),
        issuer_department: values.issuer_department || values.department,
        issue_date: values.issue_date ? values.issue_date.format('YYYY-MM-DD') : values.training_date.format('YYYY-MM-DD'),
      }
      await sendTrainingNotification(payload)
      message.success('培训通知已发送')
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '发送失败')
    } finally {
      setSendingNotify(false)
    }
  }

  const handleAddToLedger = async () => {
    const values = await form.validateFields()
    const employeeNames: string[] = values.employee_names || []

    if (employeeNames.length === 0) {
      message.warning('请至少选择一名受训人员')
      return
    }

    setAddingToLedger(true)
    try {
      const existingNumbers = await getExistingLedgerNumbers()
      const newEmployees: string[] = []
      const existingEmployees: string[] = []

      for (const name of employeeNames) {
        const number = nameToNumberMap[name]
        if (!number) {
          existingEmployees.push(name)
          continue
        }
        if (existingNumbers.has(number)) {
          existingEmployees.push(name)
        } else {
          newEmployees.push(name)
        }
      }

      if (existingEmployees.length > 0) {
        modal.confirm({
          title: '以下员工已有培训台账',
          content: existingEmployees.join('、') + '\n是否继续为其他员工创建台账？',
          onOk: async () => {
            await createLedgerForNewEmployees(newEmployees, values)
          },
        })
      } else {
        await createLedgerForNewEmployees(newEmployees, values)
      }
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '操作失败')
    } finally {
      setAddingToLedger(false)
    }
  }

  const createLedgerForNewEmployees = async (newEmployees: string[], values: any) => {
    if (newEmployees.length === 0) {
      message.info('没有需要创建台账的员工')
      return
    }

    for (const name of newEmployees) {
      const number = nameToNumberMap[name]
      if (!number) continue
      try {
        await createTrainingLedgerPage({
          employee_number: number,
          employee_name: name,
        })
        await createTrainingLedger({
          employee_number: number,
          training_date: values.training_date.format('YYYY-MM-DD'),
          training_subject: values.subject,
          training_method: values.training_method,
          duration_hours: values.training_time
            ? dayjs(values.training_time[1]).diff(dayjs(values.training_time[0]), 'hour', true)
            : undefined,
          location: values.location,
          trainer: values.trainer,
          assessment_result: values.assessment_method,
          remarks: values.content,
          source_type: "notification",
          ledger_type: "event",
        })
      } catch (err: unknown) {
        message.error(`为 ${name} 创建台账失败: ${err instanceof Error ? err.message : '未知错误'}`)
      }
    }
    message.success(`已为 ${newEmployees.length} 名员工创建培训台账`)
  }

  const formValues = form.getFieldsValue()
  const traineeDepts: string[] = formValues?.trainee_departments || []
  const hasBasicInfo = formValues?.department && formValues?.training_date && formValues?.subject

  return (
    <div className="space-y-6">
      <Card title="培训通知信息">
        <Form form={form} layout="vertical" className="max-w-4xl">
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
              <Input placeholder="请输入培训主题" />
            </Form.Item>

            <Form.Item name="training_time" label="培训时间">
              <TimePicker.RangePicker className="w-full" format="HH:mm" />
            </Form.Item>

            <Form.Item name="location" label="培训地点">
              <Input placeholder="请输入培训地点" />
            </Form.Item>

            <Form.Item name="trainer" label="培训师">
              <Select
                showSearch
                placeholder="选择培训师"
                options={trainerEmployees}
                className="w-full"
                onChange={(value) => {
                  const dept = departments.find(d => d.value === form.getFieldValue('department'))
                  if (dept) setTrainerDept(dept.value)
                }}
              />
            </Form.Item>

            <Form.Item name="training_method" label="培训方式">
              <Select showSearch placeholder="选择培训方式" options={TRAINING_METHODS} className="w-full" />
            </Form.Item>

            <Form.Item name="assessment_method" label="考核方式">
              <Select showSearch placeholder="选择考核方式" options={ASSESSMENT_METHODS} className="w-full" />
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

          <Form.Item
            name="trainee_departments"
            label="受训部门"
            rules={[{ required: true, message: '请选择受训部门' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择受训部门（可多选）"
              options={departments}
              className="w-full"
              onChange={(values) => loadEmployees(values)}
            />
          </Form.Item>

          <Form.Item
            name="employee_names"
            label="受训人员"
            rules={[{ required: true, message: '请选择受训人员' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择受训人员（可多选）"
              options={[]}
              className="w-full"
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<BellOutlined />}
                onClick={handleSendNotification}
                loading={sendingNotify}
              >
                发送通知
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportWord}
                loading={submittingWord}
              >
                导出通知(Word)
              </Button>
              <Button
                icon={<FileExcelOutlined />}
                onClick={handleExportExcel}
                loading={submittingExcel}
              >
                导出签到表(Excel)
              </Button>
              <Button
                icon={<BookOutlined />}
                onClick={handleExportEval}
              >
                导出评估表
              </Button>
              <Button
                icon={<SendOutlined />}
                onClick={handleAddToLedger}
                loading={addingToLedger}
              >
                添加到培训台账
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {!hasBasicInfo && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <BellOutlined className="text-5xl mb-4" />
          <p>填写主办部门、培训日期和培训主题后预览培训通知、签到表和效果评估表</p>
        </div>
      )}

      <style jsx global>{`
        @media print {
          body * {
            visibility: hidden;
          }
          #print-area,
          #print-area * {
            visibility: visible;
          }
          #print-area {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
          }
          .ant-card-head {
            border-bottom: 1px solid #000 !important;
          }
        }
      `}</style>
    </div>
  )
}

// Stub component for EvaluationPreview
interface EvaluationPreviewProps {
  topicStr?: string
  dateStr?: string
  trainingMethodValue?: string
  trainerValue?: string
  assessmentMethodValue?: string
  deptValue?: string
  traineeDepts?: string[]
  previewNames?: string[]
  evalDurationHours?: string | number
  data?: Record<string, unknown>
}

function EvaluationPreview(props: EvaluationPreviewProps) {
  return <div>Evaluation Preview</div>
}
