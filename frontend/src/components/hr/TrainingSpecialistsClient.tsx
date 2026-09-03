'use client'

import { useEffect, useState, useCallback } from 'react'
import { Button, Card, Form, Input, Modal, Popconfirm, Radio, Select, Space, Table, Tag, Tabs, message } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, SyncOutlined } from '@ant-design/icons'
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
  // ── Specialist state ──
  const [data, setData] = useState<TrainingSpecialist[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<TrainingSpecialist | null>(null)
  const [form] = Form.useForm()
  const [factory, setFactory] = useState<'old' | 'new'>('old')
  const [departments, setDepartments] = useState<{ value: string; label: string }[]>([])
  const [employees, setEmployees] = useState<{ value: string; label: string; number: string }[]>([])
  const [saving, setSaving] = useState(false)

  // ── Team state ──
  const [teams, setTeams] = useState<TrainingTeam[]>([])
  const [teamsLoading, setTeamsLoading] = useState(false)
  const [teamModalOpen, setTeamModalOpen] = useState(false)
  const [editingTeam, setEditingTeam] = useState<TrainingTeam | null>(null)
  const [teamForm] = Form.useForm()
  const [teamFactory, setTeamFactory] = useState<'old' | 'new'>('old')
  const [teamSpecialists, setTeamSpecialists] = useState<{ value: string; label: string; department: string; number: string }[]>([])
  const [teamEmployees, setTeamEmployees] = useState<{ value: string; label: string; number: string }[]>([])
  const [teamSaving, setTeamSaving] = useState(false)
  const [_teamDept, setTeamDept] = useState('')

  const handleSyncOpenIds = async () => {
    try {
      const json = await syncTrainingSpecialistsFeishuOpenIds()
      if (json.code === 200) {
        message.success(`同步完成: ${json.data.synced} 人已更新, ${json.data.failed} 人未找到`)
        loadData()
      } else {
        message.error(json.message || '同步失败')
      }
    } catch (err: unknown) {
      message.error('同步失败: ' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  // ── Specialist helpers ──
  const loadData = async () => {
    setLoading(true)
    try {
      const res = await fetchTrainingSpecialists()
      setData(res.data || [])
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  const loadDepartments = async (f: 'old' | 'new') => {
    const fn = f === 'new' ? fetchNewDepartments : fetchDepartments
    try {
      const res = await fn({ page_size: 200 })
      const list = (res.data || []).map((d: { name: string }) => ({ value: d.name, label: d.name }))
      setDepartments(list)
    } catch { /* ignore */ }
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

  useEffect(() => { loadData() }, [])
  useEffect(() => { loadDepartments(factory) }, [factory])

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

  const handleDelete = async (id: string) => {
    try {
      await deleteTrainingSpecialistAction(id)
      message.success('已删除')
      loadData()
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await upsertTrainingSpecialistAction({
        department: values.department,
        employee_number: values.employee_number,
        employee_name: values.employee_name,
        factory: values.factory,
      })
      message.success('已保存')
      setModalOpen(false)
      loadData()
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleFactoryChange = (f: 'old' | 'new') => {
    setFactory(f)
    setEmployees([])
    form.setFieldsValue({ department: undefined, employee_name: undefined, employee_number: undefined })
  }

  // ── Team helpers ──
  const loadTeams = useCallback(async (f: 'old' | 'new') => {
    setTeamsLoading(true)
    try {
      const res = await fetchTrainingTeams(f)
      setTeams(res.data || [])
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '加载班组失败')
    } finally {
      setTeamsLoading(false)
    }
  }, [])

  const loadTeamSpecialists = async (f: 'old' | 'new') => {
    try {
      const res = await fetchTrainingSpecialists()
      const list = (res.data || [])
        .filter((s: TrainingSpecialist) => s.factory === f)
        .map((s: TrainingSpecialist) => ({
          value: s.employee_number || "",
          label: `${s.employee_name} (${s.department})`,
          department: s.department || "",
          number: s.employee_number || "",
        }))
      setTeamSpecialists(list)
    } catch { /* ignore */ }
  }

  const loadTeamEmployees = async (f: 'old' | 'new') => {
    const fn = f === 'new' ? fetchNewEmployees : fetchEmployees
    try {
      const res = await fn({ page_size: 200 })
      const list = (res.data || []).map((e: Employee) => ({
        value: e.name,
        label: `${e.name} (${e.employee_number})`,
        number: e.employee_number,
      }))
      setTeamEmployees(list)
    } catch (err: unknown) {
      message.error('加载员工列表失败: ' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  const handleTeamAdd = () => {
    setEditingTeam(null)
    setTeamFactory('old')
    setTeamDept('')
    teamForm.resetFields()
    teamForm.setFieldsValue({ factory: 'old', employee_names: [], employee_numbers: [] })
    setTeamEmployees([])
    loadTeamSpecialists('old')
    loadTeamEmployees('old')
    setTeamModalOpen(true)
  }

  const handleTeamEdit = (record: TrainingTeam) => {
    setEditingTeam(record)
    const f = (record.factory as 'old' | 'new') || 'old'
    setTeamFactory(f)
    teamForm.setFieldsValue({
      factory: f,
      name: record.name,
      department: record.department,
      specialist_employee_number: record.specialist_employee_number,
      specialist_name: record.specialist_name,
      employee_names: record.employee_names || [],
      employee_numbers: record.employee_numbers || [],
    })
    loadTeamSpecialists(f)
    setTeamDept(record.department || "")
    loadTeamEmployees(f)
    setTeamModalOpen(true)
  }

  const handleTeamDelete = async (id: string) => {
    try {
      await deleteTrainingTeamAction(id)
      message.success('班组已删除')
      loadTeams(teamFactory)
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleTeamSave = async () => {
    const values = await teamForm.validateFields()
    setTeamSaving(true)
    try {
      if (editingTeam) {
        const payload: TrainingTeamUpdateInput = {
          name: values.name,
          department: values.department,
          specialist_employee_number: values.specialist_employee_number,
          employee_numbers: values.employee_numbers || [],
        }
        await updateTrainingTeamAction(editingTeam.id, payload)
        message.success('班组已更新')
      } else {
        const payload: TrainingTeamCreateInput = {
          name: values.name,
          factory: values.factory,
          department: values.department,
          specialist_employee_number: values.specialist_employee_number,
          employee_numbers: values.employee_numbers || [],
        }
        await createTrainingTeamAction(payload)
        message.success('班组已创建')
      }
      setTeamModalOpen(false)
      loadTeams(values.factory)
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setTeamSaving(false)
    }
  }

  const handleTeamFactoryChange = (f: 'old' | 'new') => {
    setTeamFactory(f)
    setTeamEmployees([])
    setTeamDept('')
    teamForm.setFieldsValue({
      department: undefined,
      specialist_employee_number: undefined,
      specialist_name: undefined,
      employee_names: [],
      employee_numbers: [],
    })
    loadTeamSpecialists(f)
    loadTeamEmployees(f)
  }

  const handleTeamSpecialistChange = (empNumber: string) => {
    const sp = teamSpecialists.find(s => s.value === empNumber)
    if (sp) {
      teamForm.setFieldsValue({
        department: sp.department,
        specialist_name: sp.label.split(' (')[0],
      })
      setTeamDept(sp.department)
      loadTeamEmployees(teamFactory)
    }
  }

  // ── Columns ──
  const specialistColumns = [
    { title: '厂区', dataIndex: 'factory', width: 80, render: (v: string) => v === 'new' ? <Tag color="blue">新厂</Tag> : <Tag>旧厂</Tag> },
    { title: '部门', dataIndex: 'department', width: 200 },
    { title: '培训专员', dataIndex: 'employee_name', width: 120 },
    { title: '工号', dataIndex: 'employee_number', width: 120 },
    { title: '飞书 OpenID', dataIndex: 'feishu_open_id', width: 100, render: (v: string) => v ? <Tag color="green">已绑定</Tag> : <Tag color="red">未绑定</Tag> },
    {
      title: '操作', width: 120,
      render: (_: unknown, record: TrainingSpecialist) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const teamColumns = [
    { title: '班组名称', dataIndex: 'name', width: 180 },
    { title: '厂区', dataIndex: 'factory', width: 80, render: (v: string) => v === 'new' ? <Tag color="blue">新厂</Tag> : <Tag>旧厂</Tag> },
    { title: '部门', dataIndex: 'department', width: 150 },
    { title: '培训专员', dataIndex: 'specialist_name', width: 120 },
    { title: '受训人数', dataIndex: 'employee_names', width: 100, render: (v: string[]) => v?.length || 0 },
    {
      title: '操作', width: 120,
      render: (_: unknown, record: TrainingTeam) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleTeamEdit(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleTeamDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const tabItems = [
    {
      key: 'specialists',
      label: '培训专员',
      children: (
        <>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">培训专员列表</h2>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增培训专员</Button>
            <Button icon={<SyncOutlined />} onClick={handleSyncOpenIds}>同步飞书</Button>
          </div>
          <Table rowKey="id" columns={specialistColumns} dataSource={data} loading={loading} pagination={false} />

          <Modal title={editingRecord ? '编辑培训专员' : '新增培训专员'} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSave} confirmLoading={saving} destroyOnClose>
            <Form form={form} layout="vertical" className="mt-4" initialValues={{ factory: 'old' }}>
              <Form.Item label="厂区" name="factory" rules={[{ required: true }]}>
                <Radio.Group onChange={(e) => handleFactoryChange(e.target.value)} optionType="button"
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
              <Radio.Group value={teamFactory} onChange={(e) => { handleTeamFactoryChange(e.target.value); loadTeams(e.target.value) }} optionType="button"
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

  useEffect(() => {
    if (teamFactory) loadTeams(teamFactory)
  }, [teamFactory, loadTeams])

  return (
    <Card>
      <Tabs items={tabItems} defaultActiveKey="specialists" onChange={(key) => {
        if (key === 'teams') loadTeams(teamFactory)
        if (key === 'specialists') loadData()
      }} />
    </Card>
  )
}
