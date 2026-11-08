'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { App } from 'antd'
import { fetchDeliverableTemplateSlots } from '@/lib/api/client/research/deliverable-template'
import { reparseDeliverableTemplateSlots, saveDeliverableTemplateSlots } from '@/actions/research/deliverable-template'
import {
  slotAnchorKey,
  type DocGenSlot,
  type DocGenSlotCandidate,
  type DocGenTemplateSlots,
  type SlotDiffStatus,
} from '@/types/research/deliverable-template-slot'
import type { EditableSlot } from './SlotStructureTable'

/** 一键补齐一次最多补多少个，避免母本上百个空位一次全塞进来 */
const FILL_LIMIT = 60

const SLOT_QUERY_KEY = 'deliverable-template-slots'

const newUid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`

const withUid = (slot: DocGenSlot): EditableSlot => ({ ...slot, uid: newUid() })

const stripUid = (slots: EditableSlot[]): DocGenSlot[] => slots.map(({ uid: _uid, ...rest }) => rest)

const fromCandidate = (candidate: DocGenSlotCandidate): EditableSlot => ({
  uid: newUid(),
  slot_key: candidate.candidate_id,
  label: (candidate.text || candidate.label).slice(0, 20),
  value_type: 'text',
  owner_hint: null,
  hint: null,
  location: candidate.label,
  candidate_id: candidate.candidate_id,
  anchor: null,
  is_enabled: true,
  origin: 'manual',
  edited_fields: [],
})

/**
 * 打开抽屉时取槽位结构。
 *
 * 关闭即丢弃缓存（``gcTime: 0``）：草稿以服务端结构为基准，重开必须重新拉取，
 * 否则会拿着上次的编辑基线继续改，保存时令牌对不上。
 */
export function useTemplateSlotsQuery(open: boolean, templateId: string | null) {
  return useQuery({
    queryKey: [SLOT_QUERY_KEY, templateId],
    queryFn: () => fetchDeliverableTemplateSlots(templateId as string),
    enabled: open && Boolean(templateId),
    staleTime: 0,
    gcTime: 0,
    retry: false,
  })
}

interface Options {
  payload: DocGenTemplateSlots
  templateId: string
  onClose: () => void
  onChanged: () => void
}

/**
 * 槽位结构编辑器的全部状态与请求。
 *
 * 抽屉只负责布局，这样「保存/重识别/未保存拦截」的逻辑可以独立阅读。
 * 初始草稿直接来自 ``payload``（由调用方用 key 保证每次打开都是新挂载），
 * 因此这里不需要取数副作用。
 */
export function useTemplateSlotsEditor({ payload, templateId, onClose, onChanged }: Options) {
  const { message: msgApi, modal } = App.useApp()
  const [slots, setSlots] = useState<EditableSlot[]>(() => (payload.slots ?? []).map(withUid))
  const [savedSnapshot, setSavedSnapshot] = useState(() => JSON.stringify(payload.slots ?? []))
  const [token, setToken] = useState<string | null>(payload.token ?? null)
  /** 母本换版标记：重识别成功后本地失效，不必关抽屉重开 */
  const [stale, setStale] = useState(Boolean(payload.is_stale))
  const [saving, setSaving] = useState(false)
  const [reparsing, setReparsing] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [diffOnly, setDiffOnly] = useState(false)
  const [selectedKeys, setSelectedKeys] = useState<React.Key[]>([])
  const [panelOpen, setPanelOpen] = useState(true)
  /** 重解析会话内的对比基准：AI 本次原始结果 + 重解析前的槽位（不落库） */
  const [aiSlots, setAiSlots] = useState<DocGenSlot[] | null>(null)
  const [beforeReparse, setBeforeReparse] = useState<DocGenSlot[]>([])
  const [stats, setStats] = useState<{ added: number; kept: number; removed: number } | null>(null)

  const busy = saving || reparsing

  const dirty = useMemo(() => JSON.stringify(stripUid(slots)) !== savedSnapshot, [slots, savedSnapshot])

  const duplicateKeys = useMemo(() => {
    const seen = new Set<string>()
    const dup = new Set<string>()
    for (const slot of slots) {
      if (seen.has(slot.slot_key)) dup.add(slot.slot_key)
      seen.add(slot.slot_key)
    }
    return dup
  }, [slots])

  const usedIds = useMemo(
    () => new Set(slots.map((slot) => slot.candidate_id).filter((id): id is string => Boolean(id))),
    [slots],
  )

  /** 会话内 diff：重解析新增 / 保留人工修改 */
  const diffStatus = useMemo(() => {
    const map = new Map<string, SlotDiffStatus | null>()
    if (!aiSlots) return map
    const aiKeys = new Set(aiSlots.map((slot) => slotAnchorKey(slot)))
    const beforeKeys = new Set(beforeReparse.map((slot) => slotAnchorKey(slot)))
    for (const slot of slots) {
      const key = slotAnchorKey(slot)
      if (aiKeys.has(key) && !beforeKeys.has(key)) {
        map.set(slot.uid, 'added')
      } else if (beforeKeys.has(key) && (slot.origin === 'manual' || (slot.edited_fields?.length ?? 0) > 0)) {
        map.set(slot.uid, 'kept')
      }
    }
    return map
  }, [aiSlots, beforeReparse, slots])

  const removedLabels = useMemo(() => {
    if (!aiSlots) return []
    const currentKeys = new Set(slots.map((slot) => slotAnchorKey(slot)))
    return beforeReparse.filter((slot) => !currentKeys.has(slotAnchorKey(slot))).map((slot) => slot.label)
  }, [aiSlots, beforeReparse, slots])

  const visibleSlots = useMemo(() => {
    const word = keyword.trim().toLowerCase()
    return slots.filter((slot) => {
      if (diffOnly && !diffStatus.get(slot.uid)) return false
      if (!word) return true
      return [slot.label, slot.slot_key, slot.location ?? ''].some((field) => field.toLowerCase().includes(word))
    })
  }, [slots, keyword, diffOnly, diffStatus])

  const patch = (uid: string, changes: Partial<DocGenSlot>) =>
    setSlots((prev) => prev.map((slot) => (slot.uid === uid ? { ...slot, ...changes } : slot)))

  const remove = (uid: string) => setSlots((prev) => prev.filter((slot) => slot.uid !== uid))

  const pick = (candidate: DocGenSlotCandidate) => {
    const target = selectedKeys.length === 1 ? slots.find((slot) => slot.uid === String(selectedKeys[0])) : undefined
    if (target) {
      patch(target.uid, { candidate_id: candidate.candidate_id, location: candidate.label })
      msgApi.success(`已换绑到「${candidate.label}」`)
      return
    }
    if (usedIds.has(candidate.candidate_id)) {
      msgApi.warning('这个位置已经有槽位了')
      return
    }
    setSlots((prev) => [...prev, fromCandidate(candidate)])
  }

  const fillUnused = () => {
    const unused = (payload.candidates ?? []).filter((item) => !usedIds.has(item.candidate_id))
    if (unused.length === 0) {
      msgApi.info('母本里的位置都已经有槽位了')
      return
    }
    const picked = unused.slice(0, FILL_LIMIT)
    setSlots((prev) => [...prev, ...picked.map(fromCandidate)])
    msgApi.success(
      `已补充 ${picked.length} 个槽位${unused.length > picked.length ? `，还有 ${unused.length - picked.length} 个请再次点击补齐` : ''}`,
    )
  }

  const batchToggle = (enabled: boolean) => {
    if (selectedKeys.length === 0) {
      msgApi.info('先勾选要操作的槽位')
      return
    }
    const keys = new Set(selectedKeys)
    setSelectedKeys([])
    setSlots((prev) => prev.map((slot) => (keys.has(slot.uid) ? { ...slot, is_enabled: enabled } : slot)))
  }

  const save = async () => {
    setSaving(true)
    try {
      const result = await saveDeliverableTemplateSlots(templateId, stripUid(slots), token)
      setSlots((result.slots ?? []).map(withUid))
      setSavedSnapshot(JSON.stringify(result.slots ?? []))
      setToken(result.token ?? null)
      setAiSlots(null)
      setBeforeReparse([])
      setStats(null)
      setDiffOnly(false)
      msgApi.success('槽位结构已保存，下次生成生效')
      onChanged()
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const reparse = () => {
    if (dirty) {
      // 重识别以库里的结构为基准合并，未保存的修改会被覆盖且无痕迹
      msgApi.warning('有未保存的修改，请先保存再重新识别')
      return
    }
    modal.confirm({
      title: '重新识别槽位结构？',
      content: '会按位置合并：人工改过的字段保留，只补 AI 本次新识别的位置；未被修改且 AI 不再识别的位置会被移除。',
      okText: '开始识别',
      cancelText: '取消',
      onOk: async () => {
        setReparsing(true)
        try {
          const result = await reparseDeliverableTemplateSlots(templateId, token)
          const nextStats = result.stats ?? { added: 0, kept: 0, removed: 0 }
          setBeforeReparse(stripUid(slots))
          setSlots((result.slots ?? []).map(withUid))
          setSavedSnapshot(JSON.stringify(result.slots ?? []))
          setToken(result.token ?? null)
          setAiSlots(result.ai_slots ?? [])
          setStats(nextStats)
          setSelectedKeys([])
          // 重识别写回的 source_key 就是当前母本，过期标记此刻已失效
          setStale(false)
          msgApi.success(`识别完成：新增 ${nextStats.added}、保留 ${nextStats.kept}、移除 ${nextStats.removed}`)
          onChanged()
        } catch (e) {
          msgApi.error(e instanceof Error ? e.message : '重新识别失败')
        } finally {
          setReparsing(false)
        }
      },
    })
  }

  const requestClose = () => {
    if (!dirty) {
      onClose()
      return
    }
    modal.confirm({
      title: '放弃未保存的修改？',
      content: '关闭后本次对槽位名称、位置与启用状态的调整都会丢失。',
      okText: '放弃修改',
      okButtonProps: { danger: true },
      cancelText: '继续编辑',
      onOk: onClose,
    })
  }

  return {
    payload,
    slots: visibleSlots,
    total: slots.length,
    enabledCount: slots.filter((slot) => slot.is_enabled).length,
    isStale: stale,
    token,
    dirty,
    saving,
    reparsing,
    busy,
    keyword,
    setKeyword,
    diffOnly,
    toggleDiff: () => setDiffOnly((prev) => !prev),
    selectedKeys,
    setSelectedKeys,
    panelOpen,
    togglePanel: () => setPanelOpen((prev) => !prev),
    openPanel: () => setPanelOpen(true),
    stats,
    removedLabels,
    usedIds,
    duplicateKeys,
    diffStatus,
    canSave: dirty && !stale && duplicateKeys.size === 0 && !reparsing,
    patch,
    remove,
    pick,
    fillUnused,
    batchToggle,
    save,
    reparse,
    requestClose,
  }
}