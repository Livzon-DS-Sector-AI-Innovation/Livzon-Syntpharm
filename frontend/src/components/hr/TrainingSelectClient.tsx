'use client'

import { useEffect, useState } from 'react'
import { Button, Card, Checkbox, message, Select, Space, Tag } from 'antd'
import {
  CalendarOutlined,
  EnvironmentOutlined,
  UserOutlined,
  TeamOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import {
  fetchDepartments,
  fetchNewDepartments,
  fetchEmployees,
  fetchNewEmployees,
} from '@/lib/api/client/hr'
import { submitTrainingSelectTaskAction } from '@/actions/hr'

interface TrainingSelectClientProps {
  token: string
  initialData: any
}

export default function TrainingSelectClient({
  token,
  initialData,
}: TrainingSelectClientProps) {
  const [departments, setDepartments] = useState<{ value: string; label: string }[]>([])
  const [employees, setEmployees] = useState<{ value: string; label: string; number: string }[]>([])
  const taskDept = initialData?.department || ''
  const [selectedDepts, setSelectedDepts] = useState<string[]>(taskDept ? [taskDept] : [])
  const [selectedNumbers, setSelectedNumbers] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [resultData, setResultData] = useState<any>(null)

  const factory = initialData?.factory || 'old'
  const isNew = factory === 'new'

  useEffect(() => {
    const fetchFn = isNew ? fetchNewDepartments : fetchDepartments
    fetchFn({ page_size: 100 }).then((res) => {
      const list = (res.data || []).map((d: any) => ({ value: d.name, label: d.name }))
      setDepartments(list)
    })
  }, [isNew])

  // 部门列表加载完成后，自动加载任务对应部门的员工
  useEffect(() => {
    if (departments.length > 0 && taskDept) {
      loadEmployees([taskDept])
    }
  }, [departments, taskDept])

  const loadEmployees = async (depts: string[]) => {
    if (!depts || depts.length === 0) {
      setEmployees([])
      setSelectedNumbers([])
      return
    }
    setLoading(true)
    const fetchFn = isNew ? fetchNewEmployees : fetchEmployees
    const all: { value: string; label: string; number: string }[] = []
    for (const dept of depts) {
      try {
        const res = await fetchFn({ department: dept, page_size: 100 })
        const list = (res.data || []).map((e: any) => ({
          value: e.employee_number,
          label: `${e.name} (${e.employee_number || ''})`,
          number: e.employee_number,
        }))
        all.push(...list)
      } catch {
        // ignore
      }
    }
    const map = new Map(all.map((e) => [e.value, e]))
    const uniqueList = Array.from(map.values())
    setEmployees(uniqueList)
    setLoading(false)
  }

  const handleSubmit = async () => {
    if (selectedNumbers.length === 0) {
      message.warning('请至少选择一位受训人员')
      return
    }
    setSubmitting(true)
    try {
      const selectedNames = employees
        .filter((e) => selectedNumbers.includes(e.value))
        .map((e) => e.label.split(' ')[0])
      const res = await submitTrainingSelectTaskAction(token, { selectedNumbers, selectedNames })
      setResultData(res.data)
      setSubmitted(true)
      message.success('选择结果已提交')
    } catch (err: any) {
      message.error(err.message || '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted && resultData) {
    return (
      <Card className="shadow-sm">
        <div className="text-center py-8">
          <CheckCircleOutlined className="text-5xl text-green-500 mb-4" />
          <h2 className="text-xl font-semibold mb-2">选择结果已提交</h2>
          <p className="text-gray-500 mb-6">
            已为 {initialData?.department} 的 {initialData?.training_date} {initialData?.subject} 培训
            选择 {selectedNumbers.length} 位受训人员
          </p>

          <div className="text-left bg-gray-50 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-2">培训信息</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-gray-500">主办部门：</span> {initialData?.department}</div>
              <div><span className="text-gray-500">培训日期：</span> {initialData?.training_date}</div>
              <div><span className="text-gray-500">培训主题：</span> {initialData?.subject}</div>
              <div><span className="text-gray-500">培训地点：</span> {initialData?.location || '待定'}</div>
              <div><span className="text-gray-500">培训师：</span> {initialData?.trainer || '待定'}</div>
              <div><span className="text-gray-500">培训方式：</span> {initialData?.training_method || '待定'}</div>
            </div>
          </div>

          <div className="text-left">
            <h3 className="font-semibold mb-2">已选择的受训人员（{selectedNumbers.length}人）</h3>
            <div className="flex flex-wrap gap-2">
              {employees
                .filter((e) => selectedNumbers.includes(e.value))
                .map((e) => (
                  <Tag key={e.value} color="blue">
                    {e.label}
                  </Tag>
                ))}
            </div>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card className="shadow-sm">
        <h1 className="text-lg font-semibold mb-4">选择受训人员</h1>

        <div className="bg-gray-50 rounded-lg p-4 mb-4 text-sm space-y-1">
          <div className="flex items-center gap-2">
            <CalendarOutlined className="text-gray-400" />
            <span>
              <span className="text-gray-500">培训日期：</span> {initialData?.training_date}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <TeamOutlined className="text-gray-400" />
            <span>
              <span className="text-gray-500">主办部门：</span> {initialData?.department}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <UserOutlined className="text-gray-400" />
            <span>
              <span className="text-gray-500">培训主题：</span> {initialData?.subject}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <EnvironmentOutlined className="text-gray-400" />
            <span>
              <span className="text-gray-500">培训地点：</span> {initialData?.location || '待定'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <UserOutlined className="text-gray-400" />
            <span>
              <span className="text-gray-500">培训师：</span> {initialData?.trainer || '待定'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <UserOutlined className="text-gray-400" />
            <span>
              <span className="text-gray-500">培训方式：</span> {initialData?.training_method || '待定'}
            </span>
          </div>
        </div>
      </Card>

      <Card className="shadow-sm">
        <h2 className="font-semibold mb-3">选择受训部门</h2>
        <Select
          mode="multiple"
          placeholder="选择受训部门（可多选）"
          options={departments}
          value={selectedDepts}
          className="w-full"
          onChange={(value: string[]) => {
            setSelectedDepts(value)
            loadEmployees(value)
          }}
          loading={loading}
        />
      </Card>

      <Card className="shadow-sm">
        <h2 className="font-semibold mb-3">选择受训人员（{selectedNumbers.length}人）</h2>
        {employees.length > 0 ? (
          <Checkbox.Group
            className="w-full"
            value={selectedNumbers}
            onChange={(value) => setSelectedNumbers(value as string[])}
          >
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {employees.map((emp) => (
                <Checkbox key={emp.value} value={emp.value}>
                  {emp.label}
                </Checkbox>
              ))}
            </div>
          </Checkbox.Group>
        ) : (
          <p className="text-gray-400">请先选择受训部门加载人员</p>
        )}
      </Card>

      <div className="flex justify-center">
        <Button
          type="primary"
          size="large"
          onClick={handleSubmit}
          loading={submitting}
          disabled={selectedNumbers.length === 0}
        >
          提交选择结果
        </Button>
      </div>
    </div>
  )
}
