'use client'

import { useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { App } from 'antd'
import {
  fetchDeliverableTemplateSlots,
  streamReparseDeliverableTemplateSlots,
} from '@/lib/api/client/research/deliverable-template'
import { revalidateDeliverableTemplates, saveDeliverableTemplateSlots } from '@/actions/research/deliverable-template'
import type { components } from '@/types/generated/schema'
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

/** 重解析的可见进度：阶段 + 已用时长 + 思考增量，避免只转一个圈 */
export interface ReparseProgress {
  /** 当前阶段的人类可读描述 */
  stage: string
  /** 已等待秒数 */
  elapsedSeconds: number
  /** 后端按候选规模给的粗估秒数；0 表示还没拿到 */
  estimateSeconds: number
  /** 模型思考增量（部分模型不透传，此时为空） */
  thinking: string
  /** 模型已输出的正文字符数，用来证明「还在动」 */
  contentChars: number
}

const PHASE_LABELS: Record<string, string> = {
  start: '正在准备分析',
  read: '正在读模板文件，整理可填位置',
  cached: '复用上次的分析结果',
  align: '正在合并填充项',
}

type DocGenSlotsReparseData = components['schemas']['DocGenTemplateSlotsReparseData']

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
  /** 重解析的可见进度；null 表示当前没在分析 */
  const [reparseProgress, setReparseProgress] = useState<ReparseProgress | null>(null)
  /** 思考增量刷新很密（每帧一次），先攒在 ref 里，由计时器统一渲染 */
  const thinkingRef = useRef('')
  const contentCharsRef = useRef(0)

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
      msgApi.success(`已改为写入「${candidate.label}」`)
      return
    }
    if (usedIds.has(candidate.candidate_id)) {
      msgApi.warning('这个位置已经被别的填充项用了')
      return
    }
    setSlots((prev) => [...prev, fromCandidate(candidate)])
  }

  const fillUnused = () => {
    const unused = (payload.candidates ?? []).filter((item) => !usedIds.has(item.candidate_id))
    if (unused.length === 0) {
      msgApi.info('模板文件里的位置都已经有对应填充项了')
      return
    }
    const picked = unused.slice(0, FILL_LIMIT)
    setSlots((prev) => [...prev, ...picked.map(fromCandidate)])
    msgApi.success(
      `已补充 ${picked.length} 个填充项${unused.length > picked.length ? `，还有 ${unused.length - picked.length} 个，再点一次继续补齐` : ''}`,
    )
  }

  const batchToggle = (enabled: boolean) => {
    if (selectedKeys.length === 0) {
      msgApi.info('先勾选要操作的填充项')
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
      msgApi.success('填充项已保存，下次生成报告时生效')
      onChanged()
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '保存失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  const reparse = () => {
    if (dirty) {
      // 重识别以库里的结构为基准合并，未保存的修改会被覆盖且无痕迹
      msgApi.warning('有还没保存的修改，请先保存，再重新分析')
      return
    }
    modal.confirm({
      title: '重新分析结构？',
      content:
        '系统会重新读一遍模板文件：你手工改过的填充项会保留，只补上这次新找到的位置；没改过、这次又找不到的会被移除。分析结果需要点「保存」才生效。',
      okText: '开始分析',
      cancelText: '取消',
      onOk: async () => {
        setReparsing(true)
        thinkingRef.current = ''
        contentCharsRef.current = 0
        const startedAt = Date.now()
        setReparseProgress({
          stage: PHASE_LABELS.start,
          elapsedSeconds: 0,
          estimateSeconds: 0,
          thinking: '',
          contentChars: 0,
        })
        // 500ms 一次而不是每帧一次：思考增量可能每秒几十帧，逐帧 setState 会拖慢抽屉
        const timer = window.setInterval(() => {
          setReparseProgress((prev) =>
            prev
              ? {
                  ...prev,
                  elapsedSeconds: Math.round((Date.now() - startedAt) / 1000),
                  thinking: thinkingRef.current,
                  contentChars: contentCharsRef.current,
                }
              : prev,
          )
        }, 500)
        // 回调里赋值，用对象持有以避开 TS 的控制流收窄（否则 result 会被判成 never）
        const outcome: { result: DocGenSlotsReparseData | null; failure: string | null } = {
          result: null,
          failure: null,
        }
        try {
          await streamReparseDeliverableTemplateSlots(templateId, token, (event) => {
            if (event.type === 'reasoning') {
              thinkingRef.current += event.text
              return
            }
            if (event.type === 'content') {
              contentCharsRef.current += event.text.length
              return
            }
            if (event.type === 'error') {
              outcome.failure = event.message
              return
            }
            if (event.type === 'result') {
              outcome.result = event.data
              return
            }
            if (event.type === 'candidates') {
              setReparseProgress((prev) =>
                prev
                  ? {
                      ...prev,
                      stage: `已找到 ${event.candidate_count} 个可填位置，正在交给模型判断`,
                      estimateSeconds: event.estimate_seconds,
                    }
                  : prev,
              )
              return
            }
            if (event.type === 'phase') {
              setReparseProgress((prev) =>
                prev ? { ...prev, stage: PHASE_LABELS[event.phase] ?? event.message ?? prev.stage } : prev,
              )
            }
          })

          if (outcome.failure) throw new Error(outcome.failure)
          const result = outcome.result
          if (!result) throw new Error('分析没有返回结果，请重试')
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
          msgApi.success(`分析完成：新增 ${nextStats.added}、保留 ${nextStats.kept}、移除 ${nextStats.removed}`)
          onChanged()
          // 结果已经由流式接口写库，这里只刷列表缓存；刷失败不该覆盖掉成功提示
          await revalidateDeliverableTemplates().catch(() => undefined)
        } catch (e) {
          msgApi.error(e instanceof Error ? e.message : '重新分析失败，请稍后重试')
        } finally {
          window.clearInterval(timer)
          setReparseProgress(null)
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
      title: '放弃还没保存的修改？',
      content: '关闭后，这次改的填充项名称、写入位置和启用状态都会丢失。',
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
    reparseProgress,
    requestClose,
  }
}