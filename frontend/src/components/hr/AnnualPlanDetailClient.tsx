'use client'
import { SendOutlined } from "@ant-design/icons"

import { useState } from 'react'
import { App,
  Button,
  Card,
  Input,
  InputNumber,
  DatePicker,
  Select,
  Spin,
  Space,
  Popconfirm
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  EditOutlined,
  ArrowLeftOutlined,
  DownloadOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnnualTrainingPlan, AnnualTrainingPlanItem } from '@/types/hr'
import { fetchPlanItems } from '@/lib/api/client/hr'
import { apiGet } from '@/lib/api/client'
import { batchUpdatePlanItems, deleteAnnualPlanItem } from '@/actions/hr'

interface AnnualPlanDetailClientProps {
  planId: string
  plan: AnnualTrainingPlan | null
}

const MONTH_OPTIONS = Array.from({length:12}, (_,i) => `${i+1}月`)

export default function AnnualPlanDetailClient({
  planId,
  plan
}: AnnualPlanDetailClientProps) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<AnnualTrainingPlanItem>>({})

  const { data: items = [], isLoading: loading } = useQuery<AnnualTrainingPlanItem[]>({
    queryKey: ['hr-plan-items', planId],
    queryFn: async () => {
      const res = await fetchPlanItems(planId)
      return res.data || []
    },
  })

  const { data: _deptList = [] } = useQuery<string[]>({
    queryKey: ['hr-departments-list'],
    queryFn: async () => {
      const d = await apiGet<{name: string}[]>('/api/v1/hr/departments?page_size=100')
      return d.map((x: {name: string}) => x.name)
    },
  })

  const { data: _trainerList = [] } = useQuery<string[]>({
    queryKey: ['hr-trainers-list'],
    queryFn: async () => {
      const d = await apiGet<{name: string}[]>('/api/v1/hr/trainers?page_size=200')
      return d.map((x: {name: string}) => x.name)
    },
  })

  const handleExport = async () => {
    try {
      const res = await fetch(`/api/v1/hr/annual-training-plans/${planId}/export`)
      if (!res.ok) throw new Error('导出失败')
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const contentDisposition = res.headers.get('content-disposition')
      const filename = contentDisposition?.match(/filename\*?=utf-8''(.+)/)?.[1] || contentDisposition?.match(/filename="(.+)"/)?.[1] || '年度培训计划.xlsx'
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '导出失败')
    }
  }

  const handleAdd = () => {
    const newItem: AnnualTrainingPlanItem = {
      id: `new-${Date.now()}`,
      plan_id: planId,
      month: '',
      trainee_count: undefined,
      duration_hours: undefined,
      content_and_textbook: '',
      target_audience: '',
      position_and_count: '',
      training_method: '',
      training_hours: undefined,
      confirmer: '',
      confirm_date: '',
      remarks: '',
      tracking_status: '',
      sort_order: items.length
    }
    queryClient.setQueryData<AnnualTrainingPlanItem[]>(['hr-plan-items', planId], (old) => [...(old || []), newItem])
    setEditingId(newItem.id)
    setEditForm(newItem)
  }

  const handleEdit = (item: AnnualTrainingPlanItem) => {
    setEditingId(item.id)
    setEditForm({ ...item })
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditForm({})
    queryClient.setQueryData<AnnualTrainingPlanItem[]>(['hr-plan-items', planId], (old) => 
      (old || []).filter((i) => !i.id.startsWith('new-'))
    )
  }

  const updateField = (field: string, value: unknown) => {
    setEditForm((prev) => ({ ...prev, [field]: value }))
  }

  const _updateItem = (id: string, field: string, value: unknown) => {
    queryClient.setQueryData<AnnualTrainingPlanItem[]>(['hr-plan-items', planId], (old) =>
      (old || []).map((item) => item.id === id ? { ...item, [field]: value } : item)
    )
  }

  const removeItem = (id: string) => {
    queryClient.setQueryData<AnnualTrainingPlanItem[]>(['hr-plan-items', planId], (old) =>
      (old || []).filter((item) => item.id !== id)
    )
  }

  const handleSaveAll = async () => {
    if (items.length === 0) {
      message.warning('请先添加明细')
      return
    }

    const payloadItems = items.map((item) => ({
      month: item.month || undefined,
      trainee_count: item.trainee_count || undefined,
      duration_hours: item.duration_hours || undefined,
      content_and_textbook: item.content_and_textbook || undefined,
      target_audience: item.target_audience || undefined,
      position_and_count: item.position_and_count || undefined,
      training_method: item.training_method || undefined,
      training_hours: item.training_hours || undefined,
      confirmer: item.confirmer || undefined,
      confirm_date: item.confirm_date || undefined,
      remarks: item.remarks || undefined,
      tracking_status: item.tracking_status || undefined,
      sort_order: item.sort_order
    }))

    setSaving(true)
    try {
      await batchUpdatePlanItems(planId, { items: payloadItems })
      message.success('保存成功')
      setEditingId(null)
      setEditForm({})
      queryClient.invalidateQueries({ queryKey: ['hr-plan-items', planId] })
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (item: AnnualTrainingPlanItem) => {
    if (item.id.startsWith('new-')) {
      removeItem(item.id)
      return
    }
    try {
      await deleteAnnualPlanItem(planId, item.id)
      queryClient.invalidateQueries({ queryKey: ['hr-plan-items', planId] })
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
        <Link href="/hr/training/annual-plan">
          <Button icon={<ArrowLeftOutlined />}>返回列表</Button>
        </Link>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出Excel
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSaveAll}
            loading={saving}
          >
            保存
          </Button>
          <Button icon={<PlusOutlined />} onClick={handleAdd}>
            添加明细
          </Button>
        </Space>
      </div>

      {/* 计划基本信息 */}
      {plan && (
        <Card size="small" className="no-print">
          <div className="flex items-center gap-6 text-sm">
            <span><strong>年度：</strong>{plan.year}</span>
            <span><strong>部门：</strong>{plan.department}</span>
            <span><strong>状态：</strong>{plan.status}</span>
          </div>
        </Card>
      )}

      {/* 明细表格 */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 px-2 py-2 w-12">序号</th>
                <th className="border border-gray-300 px-2 py-2 w-20">月份</th>
                <th className="border border-gray-300 px-2 py-2 w-20">受训人次</th>
                <th className="border border-gray-300 px-2 py-2 w-20">培训时长(h)</th>
                <th className="border border-gray-300 px-2 py-2 min-w-[200px]">培训内容及教材</th>
                <th className="border border-gray-300 px-2 py-2 w-32">培训对象</th>
                <th className="border border-gray-300 px-2 py-2 w-32">岗位及人数</th>
                <th className="border border-gray-300 px-2 py-2 w-24">培训方式</th>
                <th className="border border-gray-300 px-2 py-2 w-20">培训课时</th>
                <th className="border border-gray-300 px-2 py-2 w-32">确认人/日期</th>
                <th className="border border-gray-300 px-2 py-2 w-20">跟踪状态</th>
                <th className="border border-gray-300 px-2 py-2 min-w-[120px]">备注</th>
                <th className="border border-gray-300 px-1 py-2 w-20 no-print">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                const editing = editingId === item.id
                const isBlank = item.id.startsWith('new-') && !editing
                return (
                  <tr key={item.id} className={isBlank ? 'opacity-50' : ''}>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {index + 1}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {editing ? (
                        <Select
                          size="small"
                          value={editForm.month || undefined}
                          onChange={(v) => updateField('month', v)}
                          options={MONTH_OPTIONS.map((m) => ({ label: m, value: m }))}
                          placeholder="月"
                          style={{ width: '100%' }}
                        />
                      ) : (
                        <span>{item.month || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {editing ? (
                        <InputNumber
                          size="small"
                          value={editForm.trainee_count ?? ''}
                          onChange={(v) => updateField('trainee_count', v)}
                          min={0}
                          style={{ width: '100%' }}
                        />
                      ) : (
                        <span className="px-1">{item.trainee_count ?? ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {editing ? (
                        <InputNumber
                          size="small"
                          value={editForm.duration_hours ?? ''}
                          onChange={(v) => updateField('duration_hours', v)}
                          min={0}
                          step={0.5}
                          style={{ width: '100%' }}
                        />
                      ) : (
                        <span className="px-1">{item.duration_hours ?? ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2">
                      {editing ? (
                        <Input
                          size="small"
                          value={editForm.content_and_textbook || ''}
                          onChange={(e) => updateField('content_and_textbook', e.target.value)}
                        />
                      ) : (
                        <span>{item.content_and_textbook || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2">
                      {editing ? (
                        <Input
                          size="small"
                          value={editForm.target_audience || ''}
                          onChange={(e) => updateField('target_audience', e.target.value)}
                        />
                      ) : (
                        <span>{item.target_audience || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2">
                      {editing ? (
                        <Input
                          size="small"
                          value={editForm.position_and_count || ''}
                          onChange={(e) => updateField('position_and_count', e.target.value)}
                        />
                      ) : (
                        <span>{item.position_and_count || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {editing ? (
                        <Select
                          size="small"
                          value={editForm.training_method || undefined}
                          onChange={(v) => updateField('training_method', v)}
                          options={['面授', '函授', '远程教育', '自学', '其他'].map((m) => ({ label: m, value: m }))}
                          placeholder="选方式"
                          style={{ width: '100%' }}
                        />
                      ) : (
                        <span>{item.training_method || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center">
                      {editing ? (
                        <InputNumber
                          size="small"
                          value={editForm.training_hours ?? ''}
                          onChange={(v) => updateField('training_hours', v)}
                          min={0}
                          step={0.5}
                          style={{ width: '100%' }}
                        />
                      ) : (
                        <span className="px-1">{item.training_hours ?? ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 text-center" style={{ lineHeight: '1.6' }}>
                      {editing ? (
                        <>
                          <div className="flex flex-col gap-1">
                            <Input
                              size="small"
                              value={editForm.confirmer || ''}
                              onChange={(e) => updateField('confirmer', e.target.value)}
                              placeholder="确认人"
                            />
                            <DatePicker
                              size="small"
                              className="w-full"
                              placeholder="日期"
                              value={editForm.confirm_date ? dayjs(editForm.confirm_date) : null}
                              onChange={(d) => updateField('confirm_date', d ? d.format('YYYY-MM-DD') : '')}
                            />
                          </div>
                        </>
                      ) : (
                        <span>
                          {item.confirmer || ''}
                          {item.confirmer && item.confirm_date ? ' / ' : ''}
                          {item.confirm_date || ''}
                        </span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 align-top text-center" style={{ lineHeight: '1.6' }}>
                      {(() => {
                        const s = (item as AnnualTrainingPlanItem & { training_status?: string }).training_status || '—'
                        const colors: Record<string, string> = {'已评估': '#52c41a', '已通知': '#1677ff', '未开始': '#999'}
                        return <span style={{ color: colors[s] || '#999', fontWeight: 500, fontSize: 12 }}>{s}</span>
                      })()}
                    </td>
                    <td className="border border-gray-300 px-2 py-2 align-top" style={{ wordBreak: 'break-word', lineHeight: '1.6' }}>
                      {editing ? (
                        <Input
                          size="small"
                          value={editForm.remarks || ''}
                          onChange={(e) => updateField('remarks', e.target.value)}
                        />
                      ) : (
                        <span>{item.remarks || ''}</span>
                      )}
                    </td>
                    <td className="border border-gray-300 px-1 py-2 text-center align-top no-print">
                      {isBlank ? null : editing ? (
                        <Space size="small" orientation="vertical" className="w-full">
                          <Button
                            size="small"
                            onClick={handleCancel}
                          >
                            取消
                          </Button>
                        </Space>
                      ) : (
                        <Space size="small" orientation="vertical" className="w-full">
                          <Button
                            size="small"
                            type="primary"
                            icon={<SendOutlined />}
                            onClick={() => {
                              const params = new URLSearchParams()
                              params.set('subject', item.content_and_textbook || '')
                              params.set('method', item.training_method || '')
                              params.set('dept', plan?.department || '')
                              params.set('assessment', item.training_method || '')
                              window.open(`/hr/training/notification?${params.toString()}`, '_blank')
                            }}
                          />
                          <Button
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => handleEdit(item)}
                          />
                          <Popconfirm
                            title="确认删除？"
                            onConfirm={() => handleDelete(item)}
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
              {/* 底部签名行 */}
              <tr>
                <td colSpan={5} className="border border-gray-300 px-3 py-3 text-sm">
                  制表人/日期：
                </td>
                <td colSpan={5} className="border border-gray-300 px-3 py-3 text-sm">
                  部门负责人/日期：
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
