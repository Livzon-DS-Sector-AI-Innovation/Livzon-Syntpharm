'use client'

import { useState, useCallback } from 'react'
import { Button, Card, Form, Input, Modal, Popconfirm, Radio, Select, Space, Table, Tag, Tabs, message } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, SyncOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { TrainingTeam, TrainingTeamCreateInput, TrainingTeamUpdateInput, TrainingSpecialist, Employee } from '@/types/hr'
import {
  fetchTrainingSpecialists,
  fetchTrainingTeams,
  fetchDepartments,
  fetchNewDepartments,
  fetchEmployees,
  fetchNewEmployees,
} from '@/lib/api/client/hr'
import {
  upsertTrainingSpecialistAction,
  deleteTrainingSpecialistAction,
  createTrainingTeamAction,
  updateTrainingTeamAction,
  deleteTrainingTeamAction,
  syncTrainingSpecialistsFeishuOpenIds,
} from '@/actions/hr'

export default function TrainingSpecialistsClient() {
  const queryClient = useQueryClient()
  // ── Specialist state ──
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<TrainingSpecialist | null>(null)
  const [form] = Form.useForm()
  const [factory, setFactory] = useState<'old' | 'new'>('old')
  const [employees, setEmployees] = useState<{ value: string; label: string; number: string }[]>([])
  const [saving, setSaving] = useState(false)

  // ── Team state ──
  const [teamModalOpen, setTeamModalOpen] = useState(false)
  const [editingTeam, setEditingTeam] = useState<TrainingTeam | null>(null)
  const [teamForm] = Form.useForm()
  const [teamFactory, setTeamFactory] = useState<'old' | 'new'>('old')
  const [teamSpecialists, setTeamSpecialists] = useState<{ value: string; label: string; department: string; number: string }[]>([])
  const [teamEmployees, setTeamEmployees] = useState<{ value: string; label: string; number: string }[]>([])
  const [teamSaving, setTeamSaving] = useState(false)
  const [_teamDept, setTeamDept] = useState('')

  const { data: data = [], isLoading: loading, refetch: loadData } = useQuery<TrainingSpecialist[]>({
    queryKey: ['hr-training-specialists'],
    queryFn: async () => {
      const res = await fetchTrainingSpecialists()
      return res.data || []
    },
  })

  const { data: departments = [] } = useQuery<{ value: string; label: string }[]>({
    queryKey: ['hr-departments-options', { factory }],
    queryFn: async () => {
      const fn = factory === 'new' ? fetchNewDepartments : fetchDepartments
      const res = await fn({ page_size: 200 })
      return (res.data || []).map((d: { name: string }) => ({ value: d.name, label: d.name }))
    },
  })

  const { data: teams = [], isLoading: teamsLoading, refetch: loadTeams } = useQuery<TrainingTeam[]>({
    queryKey: ['hr-training-teams', { teamFactory }],
    queryFn: async () => {
      const res = await fetchTrainingTeams(teamFactory)
      return res.data || []
    },
  })

  const handleSyncOpenIds = async () => {
    try {
      const json = await syncTrainingSpecialistsFeishuOpenIds()
      if (json.code === 200) {
        message.success(`同步完成: ${json.data.synced} 人已更新, ${json.data.failed} 人未找到`)
        queryClient.invalidateQueries({ queryKey: ['hr-training-specialists'] })
      } else {
        message.error(json.message || '同步失败')
      }
    } catch (err: unknown) {
      message.error('同步失败: ' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  const loadEmployees = async (dept: string) => {
    if (!dept) { setEmployees([]); return }
    const fn = factory === 'new' ? fetchNewEmployees : fetchEmployees
    try {
      const res = await fn({ department: dept, page_size: 200 })
      const list = (res.data || []).map((e: Employee) => ({
        value: e.name,
        label: `${e.name} (${e.employee_number})`,
        number: e.employee_number,
      }))
      setEmployees(list)
    } catch { /* ignore */ }
  }

  const loadEmployeesForEdit = async (dept: string, f: 'old' | 'new') => {
    const fn = f === 'new' ? fetchNewEmployees : fetchEmployees
    try {
      const res = await fn({ department: dept, page_size: 200 })
      const list = (res.data || []).map((e: Employee) => ({
        value: e.name,
        label: `${e.name} (${e.employee_number})`,
        number: e.employee_number,
      }))
      setEmployees(list)
    } catch { /* ignore */ }
  }

  const handleAdd = () => {
    setEditingRecord(null)
    setFactory('old')
    form.resetFields()
    form.setFieldsValue({ factory: 'old' })
    setEmployees([])
    setModalOpen(true)
  }

  const handleEdit = (record: TrainingSpecialist) => {
    setEditingRecord(record)
    const f = (record.factory as 'old' | 'new') || 'old'
    setFactory(f)
    form.setFieldsValue({
      factory: f,
      department: record.department,
      employee_name: record.employee_name,
      employee_number: record.employee_number,
    })
    setEmployees([{ value: record.employee_name || "", label: `${record.employee_name || ""} (${record.employee_number || ""})`, number: record.employee_number || "" }])
    setModalOpen(true)
    loadEmployeesForEdit(record.department || "", f)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteTrainingSpecialistAction(id)
      message.success('已删除')
      queryClient.invalidateQueries({ queryKey: ['hr-training-specialists'] })
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await upsertTrainingSpecialistAction({
        id: editingRecord?.id,
        factory,
        department: values.department,
        employee_name: values.employee_name,
        employee_number: values.employee_number,
      })
      message.success(editingRecord ? '已更新' : '已添加')
      setModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['hr-training-specialists'] })
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleTeamFactoryChange = (value: 'old' | 'new') => {
    setTeamFactory(value)
    queryClient.invalidateQueries({ queryKey: ['hr-training-teams'] })
  }

  const handleTeamAdd = () => {
    setEditingTeam(null)
    setTeamFactory('old')
    teamForm.resetFields()
    teamForm.setFieldsValue({ factory: 'old', employee_names: [], employee_numbers: [] })
    setTeamEmployees([])
    setTeamModalOpen(true)
    loadTeamSpecialists()
  }

  const handleTeamEdit = (record: TrainingTeam) => {
    setEditingTeam(record)
    const f = (record.factory as 'old' | 'new') || 'old'
    setTeamFactory(f)
    teamForm.setFieldsValue({
      factory: f,
      name: record.name,
      specialist_employee_number: record.specialist_employee_number,
      specialist_name: record.specialist_name,
      department: record.department,
      employee_names: record.employee_names || [],
      employee_numbers: record.employee_numbers || [],
    })
    setTeamModalOpen(true)
    loadTeamSpecialists()
    loadTeamEmployees(record.department || '')
  }

  const loadTeamSpecialists = async () => {
    try {
      const res = await fetchTrainingSpecialists()
      const list = (res.data || []).map((s: TrainingSpecialist) => ({
        value: s.employee_number || '',
        label: `${s.employee_name} (${s.employee_number})`,
        department: s.department || '',
        number: s.employee_number || '',
      }))
      setTeamSpecialists(list)
    } catch { /* ignore */ }
  }

  const loadTeamEmployees = async (dept: string) => {
    if (!dept) { setTeamEmployees([]); return }
    const fn = teamFactory === 'new' ? fetchNewEmployees : fetchEmployees
    try {
      const res = await fn({ department: dept, page_size: 200 })
      const list = (res.data || []).map((e: Employee) => ({
        value: e.name,
        label: `${e.name} (${e.employee_number})`,
        number: e.employee_number,
      }))
      setTeamEmployees(list)
    } catch { /* ignore */ }
  }

  const handleTeamSpecialistChange = async (employeeNumber: string) => {
    const spec = teamSpecialists.find(s => s.value === employeeNumber)
    if (spec) {
      teamForm.setFieldsValue({ specialist_name: spec.label.split(' ')[0], department: spec.department })
      setTeamDept(spec.department)
      await loadTeamEmployees(spec.department)
    }
  }

  const handleTeamDelete = async (id: string) => {
    try {
      await deleteTrainingTeamAction(id)
      message.success('已删除')
      queryClient.invalidateQueries({ queryKey: ['hr-training-teams'] })
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleTeamSave = async () => {
    const values = await teamForm.validateFields()
    setTeamSaving(true)
    try {
      const payload: TrainingTeamCreateInput | TrainingTeamUpdateInput = {
        factory: teamFactory,
        name: values.name,
        specialist_employee_number: values.specialist_employee_number,
        
        department: values.department,
        employee_numbers: values.employee_numbers || [],
      }
      if (editingTeam) {
        await updateTrainingTeamAction(editingTeam.id, payload as TrainingTeamUpdateInput)
        message.success('已更新')
      } else {
        await createTrainingTeamAction(payload as TrainingTeamCreateInput)
        message.success('已添加')
      }
      setTeamModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['hr-training-teams'] })
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setTeamSaving(false)
    }
  }

  const specialistColumns = [
    { title: '厂区', dataIndex: 'factory', key: 'factory', width: 80, render: (f: string) => f === 'new' ? '新厂' : '旧厂' },
    { title: '部门', dataIndex: 'department', key: 'department', width: 150 },
    { title: '姓名', dataIndex: 'employee_name', key: 'employee_name', width: 120 },
    { title: '工号', dataIndex: 'employee_number', key: 'employee_number', width: 120 },
    { title: '飞书 Open ID', dataIndex: 'feishu_open_id', key: 'feishu_open_id', ellipsis: true, render: (v: string) => v || <span className="text-gray-400">未同步</span> },
    {
      title: '操作', key: 'action', width: 150,
      render: (_: unknown, record: TrainingSpecialist) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id!)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const teamColumns = [
    { title: '班组名称', dataIndex: 'name', key: 'name', width: 150 },
    { title: '培训专员', dataIndex: 'specialist_name', key: 'specialist_name', width: 120 },
    { title: '所属部门', dataIndex: 'department', key: 'department', width: 150 },
    { title: '受训人员', dataIndex: 'employee_names', key: 'employee_names', ellipsis: true, render: (names: string[]) => (names || []).join('、') },
    {
      title: '操作', key: 'action', width: 150,
      render: (_: unknown, record: TrainingTeam) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleTeamEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleTeamDelete(record.id!)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const tabItems = [
    {
      key: 'specialists',
      label: '培训专员列表',
      children: (
        <>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">培训专员列表</h2>
            <Space>
              <Button icon={<SyncOutlined />} onClick={handleSyncOpenIds}>同步飞书 Open ID</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增培训专员</Button>
            </Space>
          </div>
          <Table rowKey="id" columns={specialistColumns} dataSource={data} loading={loading} pagination={false} />

          <Modal title={editingRecord ? '编辑培训专员' : '新增培训专员'} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSave} confirmLoading={saving} destroyOnClose>
            <Form form={form} layout="vertical" className="mt-4" initialValues={{ factory: 'old' }}>
              <Form.Item label="厂区" name="factory" rules={[{ required: true }]}>
                <Radio.Group onChange={(e) => { setFactory(e.target.value); form.setFieldsValue({ department: undefined, employee_name: undefined, employee_number: undefined }); setEmployees([]) }} optionType="button"
                  options={[{ label: '旧厂', value: 'old' }, { label: '新厂', value: 'new' }]}
                  disabled={!!editingRecord} />
              </Form.Item>
              <Form.Item label="部门" name="department" rules={[{ required: true, message: '请选择部门' }]}>
                <Select showSearch placeholder="选择部门" options={departments}
                  onChange={(dept: string) => { form.setFieldsValue({ employee_name: undefined, employee_number: undefined }); loadEmployees(dept) }} />
              </Form.Item>
              <Form.Item label="培训专员" name="employee_name" rules={[{ required: true, message: '请选择人员' }]}>
                <Select showSearch placeholder="先选部门，再选人员" options={employees} filterOption={(input, option) => (option?.label ?? '').includes(input)}
                  notFoundContent={employees.length === 0 ? '请先选择部门' : '无匹配人员'}
                  onChange={(name: string) => {
                    const emp = employees.find(e => e.value === name)
                    if (emp) form.setFieldsValue({ employee_number: emp.number })
                  }} />
              </Form.Item>
              <Form.Item name="employee_number" hidden><Input /></Form.Item>
            </Form>
          </Modal>
        </>
      ),
    },
    {
      key: 'teams',
      label: '自定义受训班组',
      children: (
        <>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">受训班组列表</h2>
            <Space>
              <Radio.Group value={teamFactory} onChange={(e) => { handleTeamFactoryChange(e.target.value) }} optionType="button"
                options={[{ label: '旧厂', value: 'old' }, { label: '新厂', value: 'new' }]} />
              <Button type="primary" icon={<PlusOutlined />} onClick={handleTeamAdd}>新增班组</Button>
            </Space>
          </div>
          <Table rowKey="id" columns={teamColumns} dataSource={teams} loading={teamsLoading} pagination={false} />

          <Modal title={editingTeam ? '编辑受训班组' : '新增受训班组'} open={teamModalOpen} onCancel={() => setTeamModalOpen(false)} onOk={handleTeamSave} confirmLoading={teamSaving} destroyOnClose width={600}>
            <Form form={teamForm} layout="vertical" className="mt-4" initialValues={{ factory: 'old', employee_names: [], employee_numbers: [] }}>
              <Form.Item label="厂区" name="factory" rules={[{ required: true }]}>
                <Radio.Group onChange={(e) => handleTeamFactoryChange(e.target.value)} optionType="button"
                  options={[{ label: '旧厂', value: 'old' }, { label: '新厂', value: 'new' }]}
                  disabled={!!editingTeam} />
              </Form.Item>
              <Form.Item label="班组名称" name="name" rules={[{ required: true, message: '请输入班组名称' }]}>
                <Input placeholder="如：提取车间班组A" />
              </Form.Item>
              <Form.Item label="培训专员" name="specialist_employee_number" rules={[{ required: true, message: '请选择培训专员' }]}>
                <Select showSearch placeholder="选择培训专员" options={teamSpecialists}
                  filterOption={(input, option) => (option?.label ?? '').includes(input)}
                  onChange={handleTeamSpecialistChange} />
              </Form.Item>
              <Form.Item name="specialist_name" hidden><Input /></Form.Item>
              <Form.Item label="所属部门" name="department" rules={[{ required: true, message: '请先选择培训专员' }]}>
                <Select showSearch placeholder="选择培训专员后自动填入" options={departments} disabled />
              </Form.Item>
              <Form.Item label="受训人员" name="employee_names" rules={[{ required: true, message: '请选择受训人员', type: 'array', min: 1 }]}>
                <Select mode="multiple" showSearch placeholder="选择受训人员（可多选）" options={teamEmployees}
                  filterOption={(input, option) => (option?.label ?? '').includes(input)}
                  onChange={(names: string[]) => {
                    const nums = names.map(n => teamEmployees.find(e => e.value === n)?.number || '').filter(Boolean)
                    teamForm.setFieldsValue({ employee_numbers: nums })
                  }} />
              </Form.Item>
              <Form.Item name="employee_numbers" hidden><Input /></Form.Item>
            </Form>
          </Modal>
        </>
      ),
    },
  ]

  return (
    <Card>
      <Tabs items={tabItems} defaultActiveKey="specialists" onChange={(key) => {
        if (key === 'teams') loadTeams()
        if (key === 'specialists') loadData()
      }} />
    </Card>
  )
}
