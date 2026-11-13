
'use client'

import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter, useParams } from 'next/navigation'
import {
  Button,
  Space,
  Typography,
  App,
  Spin,
  Image,
  Row,
  Col,
  Select,
  Input,
  DatePicker,
  Flex,
  Upload,
  UploadFile,
} from 'antd'

import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  EditOutlined,
  CloseOutlined,
  SaveOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  ToolOutlined,
  CameraOutlined,
  InboxOutlined,
} from '@ant-design/icons'
import { getHazard, updateHazard, uploadRectificationPhoto, getDepartmentLeader, getDepartmentSafetyOfficer } from '@/actions/safety'
import type { HazardReport, HazardReportFormData } from '@/types/safety'
import {
  HAZARD_LEVEL_OPTIONS,
  HAZARD_CATEGORY_OPTIONS,
  LEGACY_HAZARD_CATEGORY_LABELS,
  INSPECTION_CATEGORY_OPTIONS,
  RECTIFICATION_STATUS_OPTIONS,
  INSPECTOR_DEPARTMENT_OPTIONS,
} from '@/types/safety'
import dayjs from 'dayjs'
import PersonnelSelect, { PersonnelMultiSelect } from '@/components/safety/PersonnelSelect'
import { PersonNameWithBadge } from '@/components/safety/PersonMatchBadge'

const { Text } = Typography
const { TextArea } = Input

import { fileProxyUrl } from '@/lib/file-url'

// ── 解析照片 JSON 数组 → 完整 URL ──
// 兼容两种格式：
//   A) 本地路径或 object_key（通过后端代理访问） → 调用 fileProxyUrl
//   B) Bitable attachment 对象 {file_token, name, url?} → 优先用 url
function parsePhotos(photos?: string | null): string[] {
  if (!photos) return []
  let arr: unknown[] = []
  try {
    arr = JSON.parse(photos)
    if (!Array.isArray(arr)) return []
  } catch {
    // 兼容旧格式：逗号分隔的路径字符串
    arr = photos.split(',').map((s) => s.trim()).filter(Boolean)
  }
  return arr
    .map((item): string | null => {
      // 本地路径或 MinIO object_key
      if (typeof item === 'string') {
        if (item.startsWith('http')) return item
        return fileProxyUrl(item)
      }
      // Bitable attachment 对象：优先用预签名 url / tmp_url
      if (typeof item === 'object' && item !== null) {
        const att = item as Record<string, unknown>
        if (typeof att.url === 'string' && att.url) return att.url
        if (typeof att.tmp_url === 'string' && att.tmp_url) return att.tmp_url
        // 无可用 URL：记录 name 供调试，跳过展示
        if (typeof att.name === 'string') {
          console.warn('照片无可用下载链接(file_token):', att.name)
        }
      }
      return null
    })
    .filter((url): url is string => url !== null)
}

// ── 日期格式化 ──
function fmtDate(iso?: string | null, format = 'YYYY-MM-DD HH:mm'): string {
  if (!iso) return '-'
  return dayjs(iso).format(format)
}

// ── 已绑定人员的头像回显：按 UUID 从后端人员引用里取，避免用错误的旧头像 ──
function personAvatarOf(
  persons: { id?: string | null; avatar_url?: string | null }[] | undefined,
  id: string,
): string | undefined {
  return persons?.find((person) => person.id === id)?.avatar_url ?? undefined
}

// ── 隐患等级颜色/标签 ──
function getLevelColor(level: string) {
  const opt = HAZARD_LEVEL_OPTIONS.find((o) => o.value === level)
  return opt?.color || 'default'
}
function getLevelLabel(level: string) {
  const opt = HAZARD_LEVEL_OPTIONS.find((o) => o.value === level)
  return opt?.label || level
}

// ── 隐患类别 label map ──
const HAZARD_CATEGORY_LABEL_MAP: Record<string, string> = { ...LEGACY_HAZARD_CATEGORY_LABELS }
HAZARD_CATEGORY_OPTIONS.forEach((o) => { HAZARD_CATEGORY_LABEL_MAP[o.value] = o.label })

// ═══════════════════════════════════════════════════════════
// 视觉组件 — 参照 equipment 模块设计语言
// ═══════════════════════════════════════════════════════════

/** Status Pill — 参照 equipment/shared-styles.ts statusPill */
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

const pillSuccess = (text: string) => (
  <StatusPill color="#1aae39" bg="#d9f3e1" icon={<CheckCircleOutlined />}>{text}</StatusPill>
)
const pillInfo = (text: string) => (
  <StatusPill color="#0075de" bg="#dcecfa" icon={<ClockCircleOutlined />}>{text}</StatusPill>
)
const pillError = (text: string) => (
  <StatusPill color="#e03131" bg="#fde0ec" icon={<CloseCircleOutlined />}>{text}</StatusPill>
)
const pillNeutral = (text: string) => (
  <StatusPill color="#787671" bg="#f0eeec">{text}</StatusPill>
)
const pillWarning = (text: string) => (
  <StatusPill color="#dd5b00" bg="#ffe8d4" icon={<ExclamationCircleOutlined />}>{text}</StatusPill>
)
const pillProcessing = (text: string) => (
  <StatusPill color="#0075de" bg="#dcecfa" icon={<SyncOutlined spin />}>{text}</StatusPill>
)

/** 阶段编号圆点 */
function StageDot({ num, active }: { num: number; active: boolean }) {
  return (
    <div
      style={{
        width: 28,
        height: 28,
        borderRadius: '50%',
        background: active ? '#5645d4' : '#c8c4be',
        color: '#ffffff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 13,
        fontWeight: 700,
        flexShrink: 0,
        transition: 'background 0.3s ease',
      }}
    >
      {num}
    </div>
  )
}

/** 阶段连接竖线 */
function StageConnector() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
      <div style={{ width: 2, height: 20, background: '#ede9e4', borderRadius: 1 }} />
    </div>
  )
}

/** Stage Card — 左侧 accent bar + hover 动效 */
function StageCard({
  accentColor,
  bgColor,
  children,
}: {
  accentColor: string
  bgColor?: string
  children: React.ReactNode
}) {
  return (
    <div
      style={{
        position: 'relative',
        background: bgColor || '#ffffff',
        borderRadius: 12,
        border: '1px solid #e5e3df',
        borderLeft: `4px solid ${accentColor}`,
        overflow: 'hidden',
        transition: 'all 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#c8c4be'
        e.currentTarget.style.boxShadow = 'rgba(15,15,15,0.06) 0px 2px 8px 0px'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#e5e3df'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      <div style={{ padding: '20px 24px' }}>{children}</div>
    </div>
  )
}

/** Stage Header — 图标 + 标题 + 状态 pill + 右侧操作 */
function StageHeader({
  icon,
  title,
  statusPill: sp,
  extra,
}: {
  icon: React.ReactNode
  title: string
  statusPill?: React.ReactNode
  extra?: React.ReactNode
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 20,
        paddingBottom: 16,
        borderBottom: '1px solid #ede9e4',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ color: '#5645d4', fontSize: 18, display: 'inline-flex' }}>{icon}</span>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a' }}>{title}</span>
        {sp}
      </div>
      {extra}
    </div>
  )
}

/** 字段块标题 */
function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 13, color: '#5d5b54' }}>
      {children}
    </Text>
  )
}

/** 带线框的字段值容器 */
function FieldTile({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        border: '1px solid #e5e3df',
        borderRadius: 8,
        padding: '10px 14px',
        background: '#fafaf9',
        minHeight: 40,
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 4,
      }}
    >
      {children}
    </div>
  )
}

/** 通用文本块 */
function TextBlock({
  style,
  children,
}: {
  style?: React.CSSProperties
  children: React.ReactNode
}) {
  return (
    <div
      style={{
        background: '#fafaf9',
        padding: 12,
        borderRadius: 8,
        fontSize: 14,
        lineHeight: 1.7,
        whiteSpace: 'pre-wrap',
        border: '1px solid #ede9e4',
        color: '#37352f',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/** 照片画廊 */
function PhotoGallery({ photos: urls }: { photos: string[] }) {
  if (urls.length === 0) return null
  return (
    <Image.PreviewGroup>
      <Flex gap={10} wrap="wrap">
        {urls.map((url, i) => (
          <div
            key={i}
            style={{
              borderRadius: 10,
              overflow: 'hidden',
              border: '1px solid #ede9e4',
              transition: 'transform 0.2s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.04)' }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)' }}
          >
            <Image
              src={url}
              alt={`照片 ${i + 1}`}
              width={130}
              height={130}
              style={{ objectFit: 'cover', display: 'block' }}
              preview={true}
            />
          </div>
        ))}
      </Flex>
    </Image.PreviewGroup>
  )
}

/** 编辑按钮（actionLink 风格） */
function EditButton({
  editing,
  loading,
  onEdit,
  onCancel,
  onSave,
}: {
  editing: boolean
  loading: boolean
  onEdit: () => void
  onCancel: () => void
  onSave: () => void
}) {
  if (editing) {
    return (
      <Space size={8}>
        <Button size="small" icon={<CloseOutlined />} onClick={onCancel}>取消</Button>
        <Button size="small" type="primary" icon={<SaveOutlined />} loading={loading} onClick={onSave}>保存</Button>
      </Space>
    )
  }
  return (
    <Button
      size="small"
      icon={<EditOutlined />}
      onClick={onEdit}
      style={{
        color: '#0075de',
        fontSize: 13,
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        border: 'none',
        padding: '4px 8px',
        borderRadius: 6,
        background: 'transparent',
      }}
    >
      编辑
    </Button>
  )
}

/** 表单字段编辑器 */
function FieldEditor({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <Text style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 500, color: '#5d5b54' }}>
        {label}
      </Text>
      {children}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════

export default function HazardLedgerDetailPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const { message } = App.useApp()


  // 编辑状态
  const [editSection, setEditSection] = useState<'registration' | 'rectification' | null>(null)
  const [edits, setEdits] = useState<Partial<Record<string, string | string[]>>>({})
  const [saving, setSaving] = useState(false)

  // 整改后照片（编辑态暂存，保存时统一上传）
  const [replyFiles, setReplyFiles] = useState<UploadFile[]>([])
  const [_leaderLoading, setLeaderLoading] = useState(false)

  const queryClient = useQueryClient()

  const { data: record, isLoading: loading, refetch: _refetch } = useQuery({
    queryKey: ['safety-hazard', id],
    queryFn: async () => {
      const response = await getHazard(id)
      if (response.code === 200) {
        return response.data as HazardReport
      }
      return null
    },
    enabled: !!id,
  })

  // 部门配置的分管安全员：隐患未单独指定时作为默认值回退
  const { data: departmentSafetyOfficer } = useQuery({
    queryKey: ['safety-hazard-officer', record?.department],
    queryFn: async () => {
      if (!record?.department) return null
      try {
        const soRes = await getDepartmentSafetyOfficer(record.department)
        if (soRes.code === 200 && soRes.data?.safety_officer_name) {
          return {
            name: soRes.data.safety_officer_name,
            id: soRes.data.safety_officer_id ?? null,
          }
        }
      } catch {
        // silent
      }
      return null
    },
    enabled: !!record?.department,
  })
  const safetyOfficerName =
    record?.safety_officer_name ?? record?.safety_officer_person?.name ?? departmentSafetyOfficer?.name ?? null

  // 加载失败时提示并退回台账（渲染期不能有副作用：message / router.push 必须在 effect 内）
  useEffect(() => {
    if (!loading && !record && id) {
      message.error('加载失败')
      router.push('/safety/hazard-ledger')
    }
  }, [loading, record, id, router, message])

  const fieldVal = (field: string): string => {
    const rec = record as Record<string, unknown> | null
    const raw = editSection && field in edits ? (edits[field] ?? rec?.[field]) : rec?.[field]
    return typeof raw === 'string' ? raw : ''
  }

  /** 数组字段取值（整改负责人 UUID 列表；旧数据是单个 uuid 字符串时也能兼容） */
  const fieldIds = (field: string): string[] => {
    const rec = record as Record<string, unknown> | null
    const raw = editSection && field in edits ? (edits[field] ?? rec?.[field]) : rec?.[field]
    if (Array.isArray(raw)) return raw.filter((item): item is string => typeof item === 'string')
    if (typeof raw === 'string' && raw) return [raw]
    return []
  }

  const handleEdit = (section: 'registration' | 'rectification') => {
    setEditSection(section)
    // 读时唯一匹配会把用户 UUID 解析到 person ref 上，编辑态先同步进来，
    // 避免「已关联但输入框空白、仍提示待确认」
    const discoveredId = record?.discovered_by_person?.id ?? record?.discovered_by
    const responsiblePersons = record?.rectification_responsible_persons ?? []
    const allResponsibleResolved =
      responsiblePersons.length > 0 && responsiblePersons.every((person) => Boolean(person.id))
    const responsibleIds = allResponsibleResolved
      ? responsiblePersons.map((person) => person.id as string)
      : []
    // 分管安全员：优先用本条隐患已保存的值，历史数据回退部门配置
    const officerId =
      record?.safety_officer_id ?? record?.safety_officer_person?.id ?? departmentSafetyOfficer?.id ?? null
    const officerName =
      record?.safety_officer_name ?? record?.safety_officer_person?.name ?? departmentSafetyOfficer?.name ?? null
    setEdits({
      ...(officerName
        ? {
            safety_officer_name: officerName,
            ...(officerId ? { safety_officer_id: officerId } : {}),
          }
        : {}),
      ...(discoveredId
        ? {
            discovered_by: discoveredId,
            discovered_by_name:
              record?.discovered_by_name ?? record?.discovered_by_person?.name ?? undefined,
          }
        : {}),
      ...(responsibleIds.length > 0
        ? {
            rectification_responsible_person_ids: responsibleIds,
            rectification_responsible_person_names: responsiblePersons
              .map((person) => person.name)
              .filter(Boolean)
              .join(','),
            rectification_responsible_person: responsibleIds[0],
            rectification_responsible_person_name:
              record?.rectification_responsible_person_name ??
              responsiblePersons[0]?.name ??
              undefined,
          }
        : {}),
    })
  }
  const handleCancelEdit = () => {
    setEditSection(null)
    setEdits({})
  }

  const handleDepartmentChange = async (dept: string) => {
    setEdits((p) => ({ ...p, department: dept }))
    if (!dept) return
    setLeaderLoading(true)
    try {
      const res = await getDepartmentLeader(dept)
      if (res.code === 200 && res.data?.leader_name) {
        const name: string = res.data.leader_name
        const leaderId: string | null = res.data.leader_id || null
        setEdits((p) => ({
          ...p,
          rectification_responsible_person: leaderId || '',
          rectification_responsible_person_name: name,
        }))
      }
      // 同步获取安全员
      try {
        const soRes = await getDepartmentSafetyOfficer(dept)
        if (soRes.code === 200 && soRes.data?.safety_officer_name) {
          const officerName = soRes.data.safety_officer_name
          const officerId = soRes.data.safety_officer_id || null
          setEdits((p) => ({
            ...p,
            safety_officer_name: officerName,
            ...(officerId ? { safety_officer_id: officerId } : {}),
          }))
        }
      } catch {
        // 部门未配置安全员时保持用户手动选择
      }
    } catch {
      // silently ignore — user can search manually
    } finally {
      setLeaderLoading(false)
    }
  }

  const handleSave = async () => {
    if (Object.keys(edits).length === 0) { setEditSection(null); return }
    setSaving(true)
    try {
      const res = await updateHazard(id, edits as unknown as Partial<HazardReportFormData>)
      if (res.code === 200) {
        message.success('修改已保存')
        queryClient.invalidateQueries({ queryKey: ['safety-hazard'] })
        setEditSection(null)
        setEdits({})
      } else {
        message.error(res.message || '保存失败')
      }
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Spin size="large" />
      </div>
    )
  }
  if (!record) return null

  // ── 状态判定 ──
  const rStatus = record.rectification_status

  // ── 整改回复保存：普通字段编辑，保存即生效（不触发审批流转）──
  const handleSaveRectification = async () => {
    const pendingFiles = replyFiles.filter((f) => f.originFileObj)
    if (Object.keys(edits).length === 0 && pendingFiles.length === 0) {
      setEditSection(null)
      return
    }

    setSaving(true)
    try {
      // 逐张上传新增照片：后端接口内部会把路径 append 到 rectification_photos，
      // 这里不能再回写整段照片数组，否则会用旧快照覆盖掉刚上传的结果。
      for (const file of pendingFiles) {
        const uploadRes = await uploadRectificationPhoto(id, file.originFileObj as File)
        if (uploadRes.code !== 200) {
          throw new Error(uploadRes.message || '照片上传失败')
        }
      }

      if (Object.keys(edits).length === 0) {
        message.success('照片已上传')
        queryClient.invalidateQueries({ queryKey: ['safety-hazard'] })
        setEditSection(null)
        setEdits({})
        setReplyFiles([])
        return
      }

      const res = await updateHazard(id, edits as unknown as Partial<HazardReportFormData>)
      if (res.code === 200) {
        message.success('修改已保存')
        queryClient.invalidateQueries({ queryKey: ['safety-hazard'] })
        setEditSection(null)
        setEdits({})
        setReplyFiles([])
      } else {
        message.error(res.message || '保存失败')
      }
    } catch (err) {
      message.error(err instanceof Error && err.message ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  // ── 整改状态 pill ──
  const makeRectificationPill = () => {
    const label = RECTIFICATION_STATUS_OPTIONS.find((o) => o.value === (rStatus || 'pending'))?.label || '待整改'
    if (rStatus === 'completed' || rStatus === 'closed') return pillSuccess(label)
    if (rStatus === 'rejected') return pillError(label)
    if (rStatus === 'replied' || rStatus === 'level1_approved' || rStatus === 'level2_approved')
      return pillInfo(label)
    if (rStatus === 'ai_reviewing') return pillProcessing(label)
    if (rStatus === 'in_progress') return pillWarning(label)
    return pillNeutral(label)
  }
  const rectificationPill = makeRectificationPill()

  // ── 关闭状态（复用 status 字段：open / closed）──
  const closeStatusPill =
    record.status === 'closed'
      ? pillSuccess(`已关闭${record.closed_at ? ` · ${fmtDate(record.closed_at, 'YYYY-MM-DD')}` : ''}`)
      : pillNeutral('未关闭')

  // ── 阶段状态 pill ──
  const stage1Pill = pillSuccess('已完成')
  const stage2Pill = record.rectification_reply ? pillSuccess('已回复') : pillNeutral('待回复')

  // 整改期限 = 检查日期 + 2 个月（不可更改）
  const deadlineDefault = record.discovered_at
    ? dayjs(record.discovered_at).add(2, 'month').format('YYYY-MM-DD')
    : '-'

  const photos = {
    defect: parsePhotos(record.defect_photos),
    rectification: parsePhotos(record.rectification_photos),
  }

  // ── 隐患级别 pill ──
  const levelPillColor = getLevelColor(record.hazard_level)
  const levelPill = (() => {
    const c = levelPillColor === 'red' ? '#e03131' : levelPillColor === 'orange' ? '#dd5b00' : '#5645d4'
    const b = levelPillColor === 'red' ? '#fde0ec' : levelPillColor === 'orange' ? '#ffe8d4' : '#e6e0f5'
    return <StatusPill color={c} bg={b}>{getLevelLabel(record.hazard_level)}</StatusPill>
  })()

  return (
    <div style={{ padding: '20px 24px', maxWidth: 1100, margin: '0 auto' }}>
      {/* ═══════ 页面头部（Equipment 风格）═══════ */}
      <div style={{ marginBottom: 28 }}>
        <button
          type="button"
          onClick={() => router.push('/safety/hazard-ledger')}
          style={{
            color: '#0075de', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 4,
            background: 'transparent', border: 'none', padding: 0,
            lineHeight: '22px', marginBottom: 12,
          }}
        >
          <ArrowLeftOutlined />返回台账
        </button>

        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0, lineHeight: 1.3 }}>
              隐患台账详情
            </h1>
            <p style={{ fontSize: 14, color: '#787671', margin: '4px 0 0', lineHeight: 1.5 }}>
              编号 {record.hazard_no}
              <span style={{ color: '#c8c4be', margin: '0 8px' }}>·</span>
              {fmtDate(record.discovered_at, 'YYYY-MM-DD')}
            </p>
          </div>
          <Space size={8}>
            {levelPill}
            {rectificationPill}
            {closeStatusPill}
          </Space>
        </div>
      </div>

      {/* ═══════ 两阶段纵轴布局 ═══════ */}

      {/* ── ① 隐患登记 ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 28 }}>
          <StageDot num={1} active />
          <StageConnector />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <StageCard accentColor="#5d5b54">
            <StageHeader
              icon={<FileTextOutlined />}
              title="隐患登记"
              statusPill={stage1Pill}
              extra={<EditButton editing={editSection === 'registration'} loading={saving} onEdit={() => handleEdit('registration')} onCancel={handleCancelEdit} onSave={handleSave} />}
            />

            {editSection === 'registration' ? (
              <Row gutter={[16, 12]}>
                <Col span={8}>
                  <FieldEditor label="检查日期">
                    <DatePicker showTime style={{ width: '100%' }}
                      value={fieldVal('discovered_at') ? dayjs(fieldVal('discovered_at')) : null}
                      onChange={(d) => setEdits((p) => ({ ...p, discovered_at: d?.toISOString() || '' }))} />
                  </FieldEditor>
                </Col>
                <Col span={8}>
                  <FieldEditor label="审批人">
                    <PersonnelSelect
                      value={fieldVal('discovered_by') || null}
                      label={fieldVal('discovered_by_name')}
                      avatarSrc={
                        fieldVal('discovered_by') === record.discovered_by_person?.id ||
                        fieldVal('discovered_by') === record.discovered_by
                          ? record.discovered_by_person?.avatar_url
                          : undefined
                      }
                      placeholder="搜索姓名/账号绑定系统用户"
                      onChange={(p) => {
                        if (!p) return
                        setEdits((prev) => ({
                          ...prev,
                          discovered_by: p.id,
                          discovered_by_name: p.name,
                        }))
                      }}
                    />
                  </FieldEditor>
                  {record.discovered_by_person?.pending && !fieldVal('discovered_by') ? (
                    <Text style={{ fontSize: 12, color: '#b45309' }}>
                      待确认：同名多人或查无此人，请选择实际人员
                    </Text>
                  ) : null}
                </Col>
                <Col span={8}>
                  <FieldEditor label="整改负责人">
                    <PersonnelMultiSelect
                      value={
                        fieldIds('rectification_responsible_person_ids').length > 0
                          ? fieldIds('rectification_responsible_person_ids')
                          : fieldIds('rectification_responsible_person')
                      }
                      labels={(fieldVal('rectification_responsible_person_names') || fieldVal('rectification_responsible_person_name') || '')
                        .split(/[,，]/)
                        .map((n) => n.trim())
                        .filter(Boolean)}
                      avatarSrcs={(fieldIds('rectification_responsible_person_ids').length > 0
                        ? fieldIds('rectification_responsible_person_ids')
                        : fieldIds('rectification_responsible_person')
                      ).map((id) => personAvatarOf(record.rectification_responsible_persons, id))}
                      onChange={(persons) => {
                        setEdits((prev) => ({
                          ...prev,
                          rectification_responsible_person_ids: persons.map((p) => p.id),
                          rectification_responsible_person_names: persons.map((p) => p.name).join(','),
                          rectification_responsible_person: persons[0]?.id,
                          rectification_responsible_person_name: persons[0]?.name,
                        }))
                      }}
                    />
                  </FieldEditor>
                  {(() => {
                    // 读时未全部唯一命中的负责人保留「待确认」；全部命中时编辑态已回填 ids
                    const persons = record.rectification_responsible_persons ?? []
                    const hasPending = persons.length > 0 ? persons.some((person) => person.pending) : true
                    const hasNames = Boolean(
                      fieldVal('rectification_responsible_person_names') ||
                        fieldVal('rectification_responsible_person_name'),
                    )
                    if (!hasPending || !hasNames || fieldIds('rectification_responsible_person_ids').length > 0) {
                      return null
                    }
                    return (
                      <Text style={{ fontSize: 12, color: '#b45309' }}>
                        待确认：同名多人或查无此人，请选择实际人员
                      </Text>
                    )
                  })()}
                </Col>
                <Col span={8}>
                  <FieldEditor label="检查名称">
                    <Input
                      value={fieldVal('inspection_name')}
                      onChange={(e) => setEdits((p) => ({ ...p, inspection_name: e.target.value }))}
                      placeholder="请输入检查名称"
                    />
                  </FieldEditor>
                </Col>
                <Col span={8}>
                  <FieldEditor label="隐患等级">
                    <Select style={{ width: '100%' }}
                      value={fieldVal('hazard_level') || undefined}
                      onChange={(v) => setEdits((p) => ({ ...p, hazard_level: v }))}
                      options={HAZARD_LEVEL_OPTIONS.map((o) => ({ value: o.value, label: o.label }))} />
                  </FieldEditor>
                </Col>
                <Col span={8}>
                  <FieldEditor label="隐患类别">
                    <Select style={{ width: '100%' }}
                      value={fieldVal('hazard_category') || undefined}
                      onChange={(v) => setEdits((p) => ({ ...p, hazard_category: v }))}
                      options={Array.from(
                        new Set([
                          ...HAZARD_CATEGORY_OPTIONS.map((o) => o.value),
                          ...(fieldVal('hazard_category') ? [fieldVal('hazard_category') as string] : []),
                        ])
                      ).map((value) => ({ value, label: HAZARD_CATEGORY_LABEL_MAP[value] || value }))} />
                  </FieldEditor>
                </Col>
                <Col span={8}>
                  <FieldEditor label="检查类别">
                    <Select style={{ width: '100%' }}
                      value={fieldVal('inspection_category')}
                      onChange={(v) => setEdits((p) => ({ ...p, inspection_category: v }))}
                      options={INSPECTION_CATEGORY_OPTIONS.map((o) => ({ value: o.value, label: o.label }))} />
                  </FieldEditor>
                </Col>
                <Col span={8}>
                  <FieldEditor label="责任部门">
                    <Select
                      showSearch
                      allowClear
                      style={{ width: '100%' }}
                      placeholder="请选择责任部门"
                      value={fieldVal('department') || undefined}
                      onChange={(v) => handleDepartmentChange(v || '')}
                      options={INSPECTOR_DEPARTMENT_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
                      filterOption={(input, option) =>
                        (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                      }
                    />
                  </FieldEditor>
                </Col>
                <Col span={8}>
                  <FieldLabel>目标完成日期</FieldLabel>
                  <FieldTile>
                    <Text style={{ fontSize: 14, fontWeight: 500 }}>
                      {record.deadline ? fmtDate(record.deadline, 'YYYY-MM-DD') : deadlineDefault}
                    </Text>
                  </FieldTile>
                </Col>
                <Col span={24}>
                  <FieldEditor label="缺陷项描述">
                    <TextArea rows={3} value={fieldVal('description')}
                      onChange={(e) => setEdits((p) => ({ ...p, description: e.target.value }))} />
                  </FieldEditor>
                </Col>
                <Col span={24}>
                  <FieldEditor label="纠正预防措施（CAPA）">
                    <TextArea rows={3}
                      value={fieldVal('capa_measures')}
                      onChange={(e) => setEdits((p) => ({ ...p, capa_measures: e.target.value }))}
                      placeholder="针对该隐患制定的纠正与预防措施，如完善制度、增加巡检频次、加装防护设施等" />
                  </FieldEditor>
                </Col>
              </Row>
            ) : (
              <>
                <Row gutter={[20, 20]}>
                  <Col span={8}>
                    <FieldLabel>检查日期</FieldLabel>
                    <FieldTile>
                      <Text style={{ fontSize: 14 }}>{fmtDate(record.discovered_at, 'YYYY-MM-DD')}</Text>
                    </FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>审批人</FieldLabel>
                    <FieldTile>
                      <PersonNameWithBadge
                        name={record.discovered_by_person?.name ?? record.discovered_by_name}
                        src={record.discovered_by_person?.avatar_url}
                        pending={record.discovered_by_person?.pending}
                        bound={record.discovered_by_person?.id ?? record.discovered_by}
                        fontSize={14}
                        avatarSize={22}
                      />
                    </FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>整改负责人</FieldLabel>
                    <FieldTile>
                      {(() => {
                        // 优先用后端解析好的人员引用（含头像），历史返回无该字段时走姓名快照兜底
                        const persons = record.rectification_responsible_persons ?? []
                        if (persons.length > 0) {
                          return (
                            <Space size={6} wrap>
                              {persons.map((person, index) => (
                                <PersonNameWithBadge
                                  key={`${person.id ?? person.name ?? 'person'}-${index}`}
                                  name={person.name}
                                  src={person.avatar_url}
                                  pending={person.pending}
                                  bound={person.id}
                                  fontSize={14}
                                  avatarSize={22}
                                />
                              ))}
                            </Space>
                          )
                        }
                        const names = (record.rectification_responsible_person_names || record.rectification_responsible_person_name || '')
                          .split(/[,，]/)
                          .map((n) => n.trim())
                          .filter(Boolean)
                        if (names.length === 0) return <Text style={{ fontSize: 14, color: '#a4a097' }}>-</Text>
                        const ids = Array.isArray(record.rectification_responsible_person_ids)
                          ? record.rectification_responsible_person_ids
                          : []
                        return (
                          <Space size={4} wrap>
                            {names.map((name, index) => (
                              <PersonNameWithBadge
                                key={`${name}-${index}`}
                                name={name}
                                bound={ids[index] || (names.length === 1 ? record.rectification_responsible_person : null)}
                                fontSize={14}
                                avatarSize={22}
                              />
                            ))}
                          </Space>
                        )
                      })()}
                    </FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>目标完成日期</FieldLabel>
                    <FieldTile>
                      {record.deadline ? (
                        <span>
                          <span style={{ fontSize: 14, color: dayjs(record.deadline).isBefore(dayjs()) ? '#e03131' : '#1a1a1a', fontWeight: dayjs(record.deadline).isBefore(dayjs()) ? 600 : 400 }}>
                            {fmtDate(record.deadline, 'YYYY-MM-DD')}
                          </span>
                          {dayjs(record.deadline).isBefore(dayjs()) && (
                            <StatusPill color="#e03131" bg="#fde0ec" icon={<ExclamationCircleOutlined />}>已逾期</StatusPill>
                          )}
                        </span>
                      ) : (
                        <Text style={{ fontSize: 14, color: '#5d5b54' }}>{deadlineDefault}</Text>
                      )}
                    </FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>检查类别</FieldLabel>
                    <FieldTile>
                      {record.inspection_category
                        ? record.inspection_category.split(/[,，]/).filter(Boolean).map((c, i) => (
                          <StatusPill key={i} color="#5d5b54" bg="#f0eeec">{c.trim()}</StatusPill>))
                        : <Text style={{ fontSize: 14, color: '#a4a097' }}>-</Text>}
                    </FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>责任部门</FieldLabel>
                    <FieldTile>
                      <Text style={{ fontSize: 14 }}>{record.department || '-'}</Text>
                    </FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>隐患等级</FieldLabel>
                    <FieldTile>{levelPill}</FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>隐患类别</FieldLabel>
                    <FieldTile>
                      {record.hazard_category
                        ? (
                          <StatusPill color="#5d5b54" bg="#f0eeec">
                            {HAZARD_CATEGORY_LABEL_MAP[record.hazard_category] || record.hazard_category}
                          </StatusPill>
                        )
                        : <Text style={{ fontSize: 14, color: '#a4a097' }}>-</Text>}
                    </FieldTile>
                  </Col>
                </Row>

                {record.inspection_name && (
                  <div style={{ marginTop: 16 }}>
                    <FieldLabel>检查名称</FieldLabel>
                    <FieldTile>
                      <Text style={{ fontSize: 14 }}>{record.inspection_name}</Text>
                    </FieldTile>
                  </div>
                )}

                {record.description && (
                  <div style={{ marginTop: 16 }}>
                    <FieldLabel>缺陷项描述</FieldLabel>
                    <TextBlock>{record.description}</TextBlock>
                  </div>
                )}

                <div style={{ marginTop: 16 }}>
                  <FieldLabel><EditOutlined style={{ marginRight: 4 }} />纠正预防措施（CAPA）</FieldLabel>
                  <FieldTile>
                    <Text style={{ fontSize: 14 }}>{record.capa_measures || '-'}</Text>
                  </FieldTile>
                </div>

                {photos.defect.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <FieldLabel><CameraOutlined style={{ marginRight: 4 }} />证据（整改前照片）</FieldLabel>
                    <PhotoGallery photos={photos.defect} />
                  </div>
                )}
              </>
            )}
          </StageCard>
        </div>
      </div>

      {/* ── ② 整改回复 ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 28 }}>
          <StageDot num={2} active />
          <StageConnector />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <StageCard accentColor="#0075de">
            <StageHeader
              icon={<ToolOutlined />}
              title="整改回复"
              statusPill={stage2Pill}
              extra={
                <EditButton editing={editSection === 'rectification'} loading={saving} onEdit={() => handleEdit('rectification')} onCancel={handleCancelEdit} onSave={handleSaveRectification} />
              }
            />

            {editSection === 'rectification' ? (
              <>
                <Row gutter={[16, 12]}>
                  <Col span={8}>
                    <FieldEditor label="进度说明">
                      <TextArea rows={2}
                        value={fieldVal('rectification_progress_note')}
                        onChange={(e) => setEdits((p) => ({ ...p, rectification_progress_note: e.target.value }))}
                        placeholder="补充当前整改进度说明" />
                    </FieldEditor>
                  </Col>
                  <Col span={8}>
                    <FieldEditor label="分管安全员">
                      <PersonnelSelect
                        value={fieldVal('safety_officer_id') || null}
                        label={fieldVal('safety_officer_name')}
                        avatarSrc={
                          fieldVal('safety_officer_id') === record.safety_officer_person?.id
                            ? record.safety_officer_person?.avatar_url
                            : undefined
                        }
                        placeholder="搜索姓名选择分管安全员"
                        onChange={(p) => {
                          setEdits((prev) => ({
                            ...prev,
                            safety_officer_id: p?.id ?? '',
                            safety_officer_name: p?.name ?? '',
                          }))
                        }}
                      />
                    </FieldEditor>
                  </Col>
                  <Col span={8}>
                    <FieldEditor label="整改完成时间">
                      <DatePicker style={{ width: '100%' }}
                        value={fieldVal('actual_completion_date') ? dayjs(fieldVal('actual_completion_date')) : null}
                        onChange={(d) => setEdits((p) => ({ ...p, actual_completion_date: d?.toISOString() || '' }))} />
                    </FieldEditor>
                  </Col>
                </Row>

                <FieldEditor label="整改回复">
                  <TextArea rows={4}
                    value={fieldVal('rectification_reply')}
                    onChange={(e) => setEdits((p) => ({ ...p, rectification_reply: e.target.value }))}
                    placeholder="请详细描述整改过程、实施情况及完成情况" />
                </FieldEditor>

                {/* 整改照片上传 */}
                <div style={{ marginTop: 8 }}>
                  <FieldLabel><CameraOutlined style={{ marginRight: 4 }} />整改后照片</FieldLabel>

                  {/* 已落库的整改后照片：编辑态只读展示，保存时只追加、不覆盖 */}
                  {photos.rectification.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <Text type="secondary" style={{ fontSize: 12, display: 'inline-block', marginBottom: 6 }}>
                        已上传 {photos.rectification.length} 张
                      </Text>
                      <PhotoGallery photos={photos.rectification} />
                    </div>
                  )}

                  <Upload.Dragger
                    multiple
                    fileList={replyFiles}
                    beforeUpload={() => false}
                    accept="image/*"
                    listType="picture-card"
                    onChange={(info) => setReplyFiles(info.fileList)}
                    style={{ marginBottom: 8 }}
                  >
                    <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                    <p className="ant-upload-text">点击或拖拽图片到此区域上传</p>
                    <p className="ant-upload-hint">可继续追加整改后照片（保存时统一上传）</p>
                  </Upload.Dragger>
                </div>
              </>
            ) : (
              <>
                <Row gutter={[16, 12]}>
                  <Col span={8}>
                    <FieldLabel>进度说明</FieldLabel>
                    <FieldTile>
                      <Text style={{ fontSize: 14, color: record.rectification_progress_note ? '#1a1a1a' : '#a4a097' }}>
                        {record.rectification_progress_note || '-'}
                      </Text>
                    </FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>分管安全员</FieldLabel>
                    <FieldTile>
                      {safetyOfficerName ? (
                        <PersonNameWithBadge
                          name={safetyOfficerName}
                          src={record.safety_officer_person?.avatar_url}
                          pending={record.safety_officer_person?.pending}
                          bound={record.safety_officer_person?.id ?? record.safety_officer_id}
                          fontSize={14}
                          avatarSize={22}
                        />
                      ) : (
                        <Text style={{ fontSize: 14, color: '#a4a097' }}>-</Text>
                      )}
                    </FieldTile>
                  </Col>
                  <Col span={8}>
                    <FieldLabel>整改完成时间</FieldLabel>
                    <FieldTile>
                      <Text style={{ fontSize: 14 }}>{fmtDate(record.actual_completion_date, 'YYYY-MM-DD')}</Text>
                    </FieldTile>
                  </Col>
                </Row>

                <div style={{ marginTop: 16 }}>
                  <FieldLabel><EditOutlined style={{ marginRight: 4 }} />整改回复</FieldLabel>
                  <FieldTile>
                    <Text style={{ fontSize: 14 }}>{record.rectification_reply || '-'}</Text>
                  </FieldTile>
                </div>

                <div style={{ marginTop: 16 }}>
                  <FieldLabel><CameraOutlined style={{ marginRight: 4 }} />整改后照片</FieldLabel>
                  {photos.rectification.length > 0 ? (
                    <PhotoGallery photos={photos.rectification} />
                  ) : (
                    <FieldTile>
                      <Text style={{ fontSize: 14, color: '#a4a097' }}>暂无照片</Text>
                    </FieldTile>
                  )}
                </div>

              </>
            )}
          </StageCard>
        </div>
      </div>
    </div>
  )
}
