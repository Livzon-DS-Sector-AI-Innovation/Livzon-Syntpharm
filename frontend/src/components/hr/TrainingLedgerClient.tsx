'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { App,
  Button,
  Card,
  DatePicker,
  Spin,
  Input,
  Select,
  Space,
  Popconfirm
} from 'antd'
import {
  PrinterOutlined,
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  EditOutlined,
  ExportOutlined
} from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { exportTrainingLedger } from '@/lib/api/client/hr'
import dayjs from 'dayjs'
import { Employee, TrainingLedgerRecord } from '@/types/hr'
import {
  fetchEmployeeByNumber,
  fetchEmployees,
  fetchTrainingLedgers,

} from '@/lib/api/client/hr'
import { createTrainingLedger, updateTrainingLedger, deleteTrainingLedger } from '@/actions/hr'

interface TrainingLedgerClientProps {
  employeeNumber: string
}

const METHOD_OPTIONS = ['面授', '函授', '远程教育', '自学', '其他']

export default function TrainingLedgerClient({
  employeeNumber
}: TrainingLedgerClientProps) {
  const router = useRouter()
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<TrainingLedgerRecord>>({})
  const [saving, setSaving] = useState(false)
  const [_searchEmpNo, setSearchEmpNo] = useState(employeeNumber || '')
  const [searching, setSearching] = useState(false)
  const [searchOptions, setSearchOptions] = useState<{value:string, label:string}[]>([])

  const handleEmployeeSearch = async (keyword: string) => {
    if (!keyword || keyword.length < 1) { setSearchOptions([]); return }
    setSearching(true)
    try {
      const res = await fetchEmployees({ keyword, page_size: 20 })
      const emps = res.data || []
      setSearchOptions(emps.map((e: Employee) => ({
        value: e.employee_number,
        label: `${e.employee_number} — ${e.name} (${e.department || ''})`,
      })))
    } catch { setSearchOptions([]) }
    finally { setSearching(false) }
  }

  const { data: employee } = useQuery<Employee | null>({
    queryKey: ['hr-employee-by-number', employeeNumber],
    queryFn: async () => {
      if (!employeeNumber) return null
      const empRes = await fetchEmployeeByNumber(employeeNumber)
      return empRes.data
    },
    enabled: !!employeeNumber,
  })

  const { data: records = [], isLoading: loading } = useQuery<TrainingLedgerRecord[]>({
    queryKey: ['hr-training-ledgers', { employeeNumber, dateFrom, dateTo }],
    queryFn: async () => {
      if (!employeeNumber) return []
      const ledgerRes = await fetchTrainingLedgers({
        employee_number: employeeNumber,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page_size: 100
      })
      return ledgerRes.data || []
    },
    enabled: !!employeeNumber,
  })

  const handlePrint = () => {
    window.print()
  }

  const handleExport = async () => {
    try {
      await exportTrainingLedger(employeeNumber)
      message.success('导出成功')
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '导出失败')
    }
  }

  const handleAdd = () => {
    const newRecord: TrainingLedgerRecord = {
      id: `new-${Date.now()}`,
      employee_number: employeeNumber,
      training_date: dayjs().format('YYYY-MM-DD'),
      training_subject: '',
      training_method: '',
      duration_hours: undefined,
      location: '',
      trainer: '',
      assessment_result: '',
      source_type: 'manual',
      remarks: ''
    }
    queryClient.setQueryData<TrainingLedgerRecord[]>(['hr-training-ledgers', { employeeNumber, dateFrom, dateTo }], (old) => [newRecord, ...(old || [])])
    setEditingId(newRecord.id)
    setEditForm(newRecord)
  }

  const handleEdit = (record: TrainingLedgerRecord) => {
    setEditingId(record.id)
    setEditForm({ ...record })
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditForm({})
    // Remove unsaved new rows
    queryClient.setQueryData<TrainingLedgerRecord[]>(['hr-training-ledgers', { employeeNumber, dateFrom, dateTo }], (old) =>
      (old || []).filter((r) => !r.id.startsWith('new-'))
    )
  }

  const handleSave = async (record: TrainingLedgerRecord) => {
    if (!editForm.training_date || !editForm.training_subject) {
      message.warning('培训日期和培训课程不能为空')
      return
    }
    setSaving(true)
    try {
      const payload = {
        employee_number: employeeNumber,
        training_date: editForm.training_date!,
        training_subject: editForm.training_subject!,
        training_method: editForm.training_method || undefined,
        duration_hours: editForm.duration_hours || undefined,
        location: editForm.location || undefined,
        trainer: editForm.trainer || undefined,
        assessment_result: editForm.assessment_result || undefined,
        source_type: 'manual',
        ledger_type: 'event',
        remarks: editForm.remarks || undefined
      }

      if (record.id.startsWith('new-')) {
        await createTrainingLedger(payload)
      } else {
        await updateTrainingLedger(record.id, payload)
      }
      message.success('保存成功')
      setEditingId(null)
      setEditForm({})
      queryClient.invalidateQueries({ queryKey: ['hr-training-ledgers'] })
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (record: TrainingLedgerRecord) => {
    if (record.id.startsWith('new-')) {
      queryClient.setQueryData<TrainingLedgerRecord[]>(['hr-training-ledgers', { employeeNumber, dateFrom, dateTo }], (old) =>
        (old || []).filter((r) => r.id !== record.id)
      )
      return
    }
    try {
      await deleteTrainingLedger(record.id)
      queryClient.invalidateQueries({ queryKey: ['hr-training-ledgers'] })
      message.success('删除成功')
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spin size="large" description="加载中..." />
      </div>
    )
  }

  return (
    <div className="space-y-6" id="print-area">
      {/* 顶部操作栏 */}
      <div className="flex items-center justify-between no-print">
        <Space>
          <Select
            showSearch
            placeholder="搜索员工"
            value={_searchEmpNo || undefined}
            onChange={(v) => {
              setSearchEmpNo(v)
              router.push(`/hr/training/ledger?employee_number=${v}`)
            }}
            onSearch={handleEmployeeSearch}
            options={searchOptions}
            filterOption={false}
            loading={searching}
            style={{ width: 300 }}
          />
          <Button icon={<PrinterOutlined />} onClick={handlePrint}>
            打印
          </Button>
          <Button icon={<ExportOutlined />} onClick={handleExport}>
            导出Excel
          </Button>
        </Space>
        <Space>
          <DatePicker
            placeholder="开始日期"
            value={dateFrom ? dayjs(dateFrom) : null}
            onChange={(d) => setDateFrom(d ? d.format('YYYY-MM-DD') : null)}
          />
          <DatePicker
            placeholder="结束日期"
            value={dateTo ? dayjs(dateTo) : null}
            onChange={(d) => setDateTo(d ? d.format('YYYY-MM-DD') : null)}
          />
          <Button icon={<PlusOutlined />} onClick={handleAdd}>
            添加记录
          </Button>
        </Space>
      </div>

      {/* 员工信息 */}
      {employee && (
        <Card size="small" className="no-print">
          <div className="flex items-center gap-6 text-sm">
            <span><strong>姓名：</strong>{employee.name}</span>
            <span><strong>工号：</strong>{employee.employee_number}</span>
            <span><strong>部门：</strong>{employee.department}</span>
            <span><strong>职位：</strong>{employee.position}</span>
          </div>
        </Card>
      )}

      {/* 培训记录表格 */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 px-2 py-2 w-12">序号</th>
                <th className="border border-gray-300 px-2 py-2 w-28">培训日期</th>
                <th className="border border-gray-300 px-2 py-2 min-w-[200px]">培训课程</th>
                <th className="border border-gray-300 px-2 py-2 w-24">培训方式</th>
                <th className="border border-gray-300 px-2 py-2 w-28">培训地点</th>
                <th className="border border-gray-300 px-2 py-2 w-28">培训师</th>
                <th className="border border-gray-300 px-2 py-2 w-24">考核结果</th>
                <th className="border border-gray-300 px-2 py-2 w-20">时长(h)</th>
                <th className="border border-gray-300 px-1 py-2 w-20 no-print">操作</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record, index) => {
                const editing = editingId === record.id
                const isBlank = record.id.startsWith('new-') && !editing
                return (
                  <tr key={record.id} className={isBlank ? 'opacity-50' : ''}>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {index + 1}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {editing ? (
                        <DatePicker
                          size="small"
                          value={editForm.training_date ? dayjs(editForm.training_date) : null}
                          onChange={(d) => setEditForm((prev) => ({ ...prev, training_date: d ? d.format('YYYY-MM-DD') : '' }))}
                          className="w-full"
                        />
                      ) : (
                        <span>{record.training_date || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2">
                      {editing ? (
                        <Input
                          size="small"
                          value={editForm.training_subject || ''}
                          onChange={(e) => setEditForm((prev) => ({ ...prev, training_subject: e.target.value }))}
                        />
                      ) : (
                        <span>{record.training_subject || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {editing ? (
                        <Select
                          size="small"
                          value={editForm.training_method || undefined}
                          onChange={(v) => setEditForm((prev) => ({ ...prev, training_method: v }))}
                          options={METHOD_OPTIONS.map((m) => ({ label: m, value: m }))}
                          placeholder="选方式"
                          style={{ width: '100%' }}
                        />
                      ) : (
                        <span>{record.training_method || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2">
                      {editing ? (
                        <Input
                          size="small"
                          value={editForm.location || ''}
                          onChange={(e) => setEditForm((prev) => ({ ...prev, location: e.target.value }))}
                        />
                      ) : (
                        <span>{record.location || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2">
                      {editing ? (
                        <Input
                          size="small"
                          value={editForm.trainer || ''}
                          onChange={(e) => setEditForm((prev) => ({ ...prev, trainer: e.target.value }))}
                        />
                      ) : (
                        <span>{record.trainer || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {editing ? (
                        <Input
                          size="small"
                          value={editForm.assessment_result || ''}
                          onChange={(e) => setEditForm((prev) => ({ ...prev, assessment_result: e.target.value }))}
                        />
                      ) : (
                        <span>{record.assessment_result || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-1 py-1">
                      {editing ? (
                        <Input
                          size="small"
                          type="number"
                          step={0.5}
                          value={editForm.duration_hours ?? ''}
                          onChange={(e) =>
                            setEditForm((prev) => ({
                              ...prev,
                              duration_hours: e.target.value
                                ? parseFloat(e.target.value)
                                : undefined
                            }))
                          }
                        />
                      ) : (
                        <span className="px-1">{
                          record.duration_hours ?? ''
                        }</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-1 py-1 text-center no-print">
                      {isBlank ? null : editing ? (
                        <Space size="small">
                          <Button
                            type="primary"
                            size="small"
                            icon={<SaveOutlined />}
                            loading={saving}
                            onClick={() => handleSave(record)}
                          />
                          <Button
                            size="small"
                            onClick={handleCancel}
                          >
                            取消
                          </Button>
                        </Space>
                      ) : (
                        <Space size="small">
                          <Button
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => handleEdit(record)}
                          />
                          <Popconfirm
                            title="确认删除？"
                            onConfirm={() => handleDelete(record)}
                          >
                            <Button
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                            />
                          </Popconfirm>
                        </Space>
                      )}
                    </td>
                  </tr>
                )
              })}
              {/* 备注 */}
              <tr>
                <td
                  colSpan={7}
                  className="border border-gray-300 px-2 py-2 text-xs text-gray-500"
                >
                  备注：笔试考核设置为满分100分，考试合格线为80分。
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        </Card>

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
          .no-print {
            display: none !important;
          }
          .ant-card {
            border: none !important;
            box-shadow: none !important;
          }
          .ant-card-body {
            padding: 0 !important;
          }
        }
      `}</style>
    </div>
  )
}
