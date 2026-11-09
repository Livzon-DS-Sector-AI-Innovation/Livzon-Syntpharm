'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Button, Space, Typography, App, Drawer, Empty, Spin, Divider } from 'antd'
import {
  EditOutlined,
  InboxOutlined,
  DeleteOutlined,
  BankOutlined,
  ClockCircleOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import HazardInspectionForm from './HazardInspectionForm'
import type { InspectionFormValues } from './HazardInspectionForm'
import { createHazard, updateHazard, getHazards, deleteHazard } from '@/actions/safety'
import type { HazardReport, HazardReportFormData } from '@/types/safety'
import dayjs from 'dayjs'

const { Text } = Typography

interface Props {
  variant?: 'page' | 'drawer'
  onDone?: () => void
}

// ═══════════════════════════════════════════════════════════
// 视觉组件
// ═══════════════════════════════════════════════════════════

function StatusPill({
  color,
  bg,
  icon,
  children,
}: {
  color: string
  bg: string
  icon?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 10px',
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        lineHeight: '20px',
        color,
        background: bg,
        whiteSpace: 'nowrap',
      }}
    >
      {icon}
      {children}
    </span>
  )
}

// ═══════════════════════════════════════════════════════════

export default function HazardInspectionFlow({ variant = 'page', onDone }: Props) {
  const router = useRouter()
  const { message } = App.useApp()

  const [submitting, setSubmitting] = useState(false)

  // ── 草稿箱状态 ──
  const [draftDrawerOpen, setDraftDrawerOpen] = useState(false)
  const [drafts, setDrafts] = useState<HazardReport[]>([])
  const [draftsLoading, setDraftsLoading] = useState(false)
  const [draftFormValues, setDraftFormValues] = useState<InspectionFormValues | undefined>()
  const [currentHazard, setCurrentHazard] = useState<HazardReport | null>(null)

  // 加载草稿列表
  // 列表接口目前没有 overall_status 过滤参数，先取最近一页再按草稿态筛选
  const loadDrafts = useCallback(async () => {
    setDraftsLoading(true)
    try {
      const res = await getHazards({ page: 1, page_size: 100 })
      if (res.code === 200) {
        setDrafts(res.data.filter((h) => h.overall_status === 'draft'))
      }
    } catch {
      // 草稿加载非关键路径，失败时静默降级为空白列表
    } finally {
      setDraftsLoading(false)
    }
  }, [])

  // ── 表单值 → 后端载荷（登记字段统一在此收敛，避免多处漏字段）──
  const buildPayload = (values: InspectionFormValues): HazardReportFormData =>
    ({
      inspection_name: values.inspection_name,
      inspection_category: values.inspection_category,
      hazard_level: values.hazard_level,
      hazard_category: values.hazard_category,
      discovered_by: values.discovered_by,
      discovered_by_name: values.discovered_by_name,
      inspector_department: values.inspector_department,
      department: values.department,
      discovered_at: values.discovered_at,
      deadline: values.deadline,
      description: values.description,
      capa_measures: values.capa_measures,
      rectification_responsible_person_ids: values.rectification_responsible_person_ids,
      rectification_responsible_person_names: values.rectification_responsible_person_names,
    }) as HazardReportFormData

  /** 登记成功后统一跳转详情（抽屉变体先关闭抽屉） */
  const goToDetail = (hazardId: string) => {
    if (variant === 'drawer' && onDone) {
      onDone()
    }
    router.push(`/safety/hazard/${hazardId}`)
  }

  // ── 正式登记：创建/更新记录后直接进详情，不再触发 AI 分析 ──
  const handleSubmit = async (values: InspectionFormValues) => {
    setSubmitting(true)
    try {
      const payload = { ...buildPayload(values), overall_status: 'completed' } as HazardReportFormData
      let hazard: HazardReport

      if (currentHazard) {
        const updateRes = await updateHazard(currentHazard.id, payload)
        if (updateRes.code !== 200) {
          message.error(updateRes.message || '更新失败')
          return
        }
        hazard = updateRes.data as HazardReport
      } else {
        const createRes = await createHazard({ hazard_no: '', ...payload } as HazardReportFormData)
        if (createRes.code !== 200) {
          message.error(createRes.message || '创建失败')
          return
        }
        hazard = createRes.data as HazardReport
      }

      message.success('隐患已登记')
      goToDetail(hazard.id)
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : '请重试'
      message.error(`提交失败：${errMsg}`)
    } finally {
      setSubmitting(false)
    }
  }

  // ── 保存草稿 ──
  const handleSaveDraft = async (values: InspectionFormValues) => {
    setSubmitting(true)
    try {
      if (currentHazard) {
        const updateRes = await updateHazard(currentHazard.id, {
          ...buildPayload(values),
          overall_status: 'draft',
        })
        if (updateRes.code !== 200) {
          message.error(updateRes.message || '保存草稿失败')
          return
        }
      } else {
        const createRes = await createHazard({
          hazard_no: '',
          ...buildPayload(values),
          overall_status: 'draft',
        } as HazardReportFormData)
        if (createRes.code !== 200) {
          message.error(createRes.message || '保存草稿失败')
          return
        }
      }

      message.success('草稿已保存')
      await loadDrafts()
      setCurrentHazard(null)
      setDraftFormValues(undefined)
    } catch {
      message.error('保存草稿失败')
    } finally {
      setSubmitting(false)
    }
  }

  // ── 从草稿继续登记 ──
  const handleContinueDraft = (draft: HazardReport) => {
    setDraftFormValues({
      inspection_name: draft.inspection_name ?? undefined,
      // 检查类别已收窄为单选：历史多选草稿取第一个值回显
      inspection_category: Array.isArray(draft.inspection_category)
        ? draft.inspection_category[0]
        : (draft.inspection_category ?? undefined),
      hazard_level: draft.hazard_level ?? undefined,
      hazard_category: draft.hazard_category ?? undefined,
      discovered_by: draft.discovered_by ?? undefined,
      discovered_by_name: draft.discovered_by_name ?? undefined,
      inspector_department: Array.isArray(draft.inspector_department)
        ? draft.inspector_department
        : draft.inspector_department
          ? draft.inspector_department.split(/[,，]/).filter(Boolean)
          : undefined,
      department: draft.department ?? undefined,
      discovered_at: draft.discovered_at,
      deadline: draft.deadline ?? undefined,
      description: draft.description,
      capa_measures: draft.capa_measures ?? undefined,
      rectification_responsible_person_ids: draft.rectification_responsible_person_ids ?? undefined,
      rectification_responsible_person_names: draft.rectification_responsible_person_names ?? undefined,
    })
    setCurrentHazard(draft)
    setDraftDrawerOpen(false)
  }

  // ── 删除草稿 ──
  const handleDeleteDraft = async (id: string) => {
    try {
      const res = await deleteHazard(id)
      if (res.code === 200) {
        message.success('草稿已删除')
        await loadDrafts()
      } else {
        message.error(res.message || '删除失败')
      }
    } catch {
      message.error('删除失败')
    }
  }

  const content = (
    <>
      <HazardInspectionForm
        key={currentHazard?.id || 'new'}
        initialValues={draftFormValues}
        loading={submitting}
        onSubmit={handleSubmit}
        onSaveDraft={handleSaveDraft}
      />

      {/* ── 草稿箱抽屉 ── */}
      <Drawer
        title={
          <Space>
            <InboxOutlined />
            <span>草稿箱</span>
            {drafts.length > 0 && (
              <StatusPill color="#0075de" bg="#dcecfa">{String(drafts.length)}</StatusPill>
            )}
          </Space>
        }
        open={draftDrawerOpen}
        onClose={() => setDraftDrawerOpen(false)}
        styles={{ body: { padding: '16px 24px' } }}
        size={420}
      >
        {draftsLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
          </div>
        ) : drafts.length === 0 ? (
          <Empty description="暂无草稿记录" />
        ) : (
          <div>
            {drafts.map((draft, idx) => (
              <div key={draft.id}>
                {idx > 0 && <Divider style={{ margin: '8px 0' }} />}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    padding: '4px 0',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Space style={{ marginBottom: 4 }}>
                      <Text strong style={{ fontSize: 13 }}>
                        {draft.hazard_no || '未编号'}
                      </Text>
                      {draft.inspection_category && (
                        <StatusPill color="#5d5b54" bg="#f0eeec">{draft.inspection_category}</StatusPill>
                      )}
                    </Space>
                    <div style={{ fontSize: 12 }}>
                      {draft.department && (
                        <Text type="secondary" style={{ display: 'block' }}>
                          <BankOutlined style={{ marginRight: 4 }} />
                          {draft.department}
                        </Text>
                      )}
                      <Text type="secondary" style={{ display: 'block' }}>
                        <ClockCircleOutlined style={{ marginRight: 4 }} />
                        {draft.created_at
                          ? dayjs(draft.created_at).format('YYYY-MM-DD HH:mm')
                          : '-'}
                      </Text>
                    </div>
                  </div>
                  <Space style={{ flexShrink: 0, marginLeft: 12 }}>
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleContinueDraft(draft)}
                    >
                      继续登记
                    </Button>
                    <Button
                      type="link"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleDeleteDraft(draft.id)}
                    />
                  </Space>
                </div>
              </div>
            ))}
          </div>
        )}
      </Drawer>
    </>
  )

  // ── Page variant: wrap with page container + header ──
  if (variant === 'page') {
    return (
      <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 600, margin: 0, color: '#1a1a1a' }}>
                隐患登记
              </h1>
              <Text style={{ color: '#5d5b54' }}>登记隐患信息并提交台账</Text>
            </div>
            <Space>
              <Button icon={<InboxOutlined />} onClick={() => { loadDrafts(); setDraftDrawerOpen(true) }}>
                草稿箱
                {drafts.length > 0 && (
                  <StatusPill color="#0075de" bg="#dcecfa">{String(drafts.length)}</StatusPill>
                )}
              </Button>
            </Space>
          </div>
        </div>
        {content}
      </div>
    )
  }

  // ── Drawer variant: minimal container (drawer provides padding) ──
  return (
    <div>
      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <SearchOutlined style={{ color: '#5645d4', fontSize: 18 }} />
          <span style={{ fontSize: 16, fontWeight: 600, color: '#1a1a1a' }}>隐患登记</span>
        </div>
        <Button icon={<InboxOutlined />} onClick={() => { loadDrafts(); setDraftDrawerOpen(true) }}>
          草稿箱
          {drafts.length > 0 && (
            <StatusPill color="#0075de" bg="#dcecfa">{String(drafts.length)}</StatusPill>
          )}
        </Button>
      </div>
      {content}
    </div>
  )
}