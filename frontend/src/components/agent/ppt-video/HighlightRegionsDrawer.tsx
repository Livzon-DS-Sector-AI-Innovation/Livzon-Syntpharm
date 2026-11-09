'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  App,
  Button,
  ColorPicker,
  Drawer,
  Empty,
  Segmented,
  Select,
  Slider,
  Space,
  Spin,
  Switch,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { DeleteOutlined, HighlightOutlined } from '@ant-design/icons'

import { fetchSlideRegions } from '@/lib/api/client/agent'
import {
  REGION_MODE_OPTIONS,
  type HighlightRect,
  type HighlightRegionItem,
  type HighlightRegionsPayload,
  type HighlightSentenceItem,
  type RegionMode,
  type SlideItem,
  type SlideRegionsResponse,
} from '@/types/agent/ppt-video'

const { Text } = Typography

const RECT_PREFIX = 'rect:'
const MIN_RECT_SIDE = 0.02
const DEFAULT_FILL_ALPHA = 90
const FALLBACK_PAGE_WIDTH = 1920
const FALLBACK_PAGE_HEIGHT = 1080

interface Props {
  open: boolean
  projectId: string
  slide: SlideItem
  /** 当前草案（父组件持有，跟随「保存本页」一起提交） */
  value: HighlightRegionsPayload | null
  onClose: () => void
  onChange: (next: HighlightRegionsPayload | null) => void
}

const clamp01 = (value: number) => Math.min(1, Math.max(0, value))

const round4 = (value: number) => Math.round(value * 10000) / 10000

const isManual = (id: string) => id.startsWith(RECT_PREFIX)

/**
 * 单页高亮区域设置：页图上点选元素 → 选三态；解析不出的地方手绘矩形兜底。
 *
 * 只改本页草案，真正落库走 SlideEditor 的「保存本页」——避免这里单独保存把讲稿等
 * 其它字段一起覆盖回去。
 */
export default function HighlightRegionsDrawer({ open, projectId, slide, value, onClose, onChange }: Props) {
  const { message } = App.useApp()
  const [regions, setRegions] = useState<HighlightRegionItem[]>(value?.regions ?? [])
  const [sentences, setSentences] = useState<HighlightSentenceItem[]>(value?.sentences ?? [])
  const [data, setData] = useState<SlideRegionsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [drawing, setDrawing] = useState(false)
  const [showAllFrames, setShowAllFrames] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [draftRect, setDraftRect] = useState<HighlightRect | null>(null)

  const canvasRef = useRef<HTMLDivElement | null>(null)
  const dragStart = useRef<{ x: number; y: number } | null>(null)

  // 打开时取一次区域清单（元素坐标 + 服务端切好的句子）；取不到就只留手绘能力
  useEffect(() => {
    if (!open) return
    let cancelled = false
    void (async () => {
      setLoading(true)
      try {
        const response = await fetchSlideRegions(projectId, slide.slide_uid)
        if (!cancelled) setData(response)
      } catch (error) {
        console.warn('区域清单加载失败:', error)
        if (!cancelled) message.warning('页内元素解析失败，仍可手绘区域')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, projectId, slide.slide_uid, message])

  const pageWidth = data?.page_width || FALLBACK_PAGE_WIDTH
  const pageHeight = data?.page_height || FALLBACK_PAGE_HEIGHT
  const elements = data?.items ?? []

  const commit = (nextRegions: HighlightRegionItem[], nextSentences: HighlightSentenceItem[]) => {
    setRegions(nextRegions)
    setSentences(nextSentences)
    onChange(
      nextRegions.length || nextSentences.length ? { regions: nextRegions, sentences: nextSentences } : null,
    )
  }

  const ruleOf = (id: string) => regions.find((item) => item.id === id)

  const patchRegion = (id: string, changes: Partial<HighlightRegionItem>) => {
    commit(
      regions.map((item) => (item.id === id ? { ...item, ...changes } : item)),
      sentences,
    )
  }

  const removeRegion = (id: string) => {
    commit(
      regions.filter((item) => item.id !== id),
      // 句子规则里引用了被删区域就一并清掉，免得留下指向空气的规则
      sentences.map((item) => ({
        ...item,
        targets: (item.targets ?? []).filter((target) => target !== id),
        mute: (item.mute ?? []).filter((target) => target !== id),
      })),
    )
    if (selectedId === id) setSelectedId(null)
  }

  /** 点选元素：未配置过的先按「文字变色」加进来，符合「点了就是想让它亮」的直觉 */
  const selectElement = (elementId: string) => {
    setSelectedId(elementId)
    if (!ruleOf(elementId)) {
      commit([...regions, { id: elementId, mode: 'text' }], sentences)
    }
  }

  const nextRectId = () => {
    const used = regions
      .filter((item) => isManual(item.id))
      .map((item) => Number(item.id.slice(RECT_PREFIX.length)))
      .filter((value) => Number.isFinite(value))
    return `${RECT_PREFIX}${used.length ? Math.max(...used) + 1 : 0}`
  }

  const pointerPos = (event: React.PointerEvent<HTMLDivElement>) => {
    const box = canvasRef.current?.getBoundingClientRect()
    if (!box || !box.width || !box.height) return null
    return {
      x: clamp01((event.clientX - box.left) / box.width),
      y: clamp01((event.clientY - box.top) / box.height),
    }
  }

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!drawing) return
    const pos = pointerPos(event)
    if (!pos) return
    event.currentTarget.setPointerCapture(event.pointerId)
    dragStart.current = pos
    setDraftRect({ x: pos.x, y: pos.y, w: 0, h: 0 })
  }

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const start = dragStart.current
    if (!start) return
    const pos = pointerPos(event)
    if (!pos) return
    setDraftRect({
      x: Math.min(start.x, pos.x),
      y: Math.min(start.y, pos.y),
      w: Math.abs(pos.x - start.x),
      h: Math.abs(pos.y - start.y),
    })
  }

  const handlePointerUp = () => {
    const start = dragStart.current
    dragStart.current = null
    const rect = draftRect
    setDraftRect(null)
    if (!start || !rect) return
    if (rect.w < MIN_RECT_SIDE || rect.h < MIN_RECT_SIDE) {
      message.info('框选太小，按住拖出一块区域再松手')
      return
    }
    const id = nextRectId()
    const rounded: HighlightRect = {
      x: round4(rect.x),
      y: round4(rect.y),
      w: round4(rect.w),
      h: round4(rect.h),
    }
    commit(
      [
        ...regions,
        // 记下画框时的页图指纹：页图重出后算出的坐标若对不上，前端能提示复核
        { id, mode: 'area', fill_alpha: DEFAULT_FILL_ALPHA, rect: rounded, shape_sha: data?.image_sha256 ?? undefined },
      ],
      sentences,
    )
    setSelectedId(id)
    setDrawing(false)
  }

  /** 元素框的显示位置：EMU 坐标按页面尺寸换算成百分比，换分辨率不会偏 */
  const frameStyle = (item: { left: number; top: number; width: number; height: number }) => ({
    left: `${(item.left / pageWidth) * 100}%`,
    top: `${(item.top / pageHeight) * 100}%`,
    width: `${(item.width / pageWidth) * 100}%`,
    height: `${(item.height / pageHeight) * 100}%`,
  })

  const rectStyle = (rect: HighlightRect) => ({
    left: `${rect.x * 100}%`,
    top: `${rect.y * 100}%`,
    width: `${rect.w * 100}%`,
    height: `${rect.h * 100}%`,
  })

  const elementLabel = (id: string) => {
    if (isManual(id)) {
      const index = regions.filter((item) => isManual(item.id)).findIndex((item) => item.id === id)
      return index >= 0 ? `手绘区域 ${index + 1}` : '手绘区域'
    }
    const element = elements.find((item) => item.element_id === id)
    return element ? `${element.label}：${element.text || '（无文字）'}` : `元素 ${id}`
  }

  const regionOptions = useMemo(
    () => [
      ...elements.map((element) => ({
        value: element.element_id,
        label: `${element.label}：${element.text || '（无文字）'}`,
      })),
      ...regions
        .filter((item) => isManual(item.id))
        .map((item) => ({ value: item.id, label: elementLabel(item.id) })),
    ],
    // elementLabel 依赖 regions，二者同源
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [elements, regions],
  )

  /** 句级规则：保留两端非空的字段，两边都空就删掉这条规则 */
  const updateSentence = (text: string, field: 'targets' | 'mute', next: string[]) => {
    const existing = sentences.find((item) => item.text === text)
    const merged: HighlightSentenceItem = {
      text,
      targets: field === 'targets' ? next : (existing?.targets ?? []),
      mute: field === 'mute' ? next : (existing?.mute ?? []),
    }
    const rest = sentences.filter((item) => item.text !== text)
    const usable = (merged.targets?.length ?? 0) || (merged.mute?.length ?? 0)
    commit(regions, usable ? [...rest, merged] : rest)
  }

  /** 后端算出的「这句会亮什么」：兜底命中的句子要标出来，方便复核后关掉 */
  const hintOf = (text: string) => (data?.sentence_hints ?? []).find((hint) => hint.text === text)

  const FALLBACK_LABEL: Record<string, string> = {
    guess: '兜底：本页最相近的元素',
    page: '兜底：整页淡底',
  }

  /** 这句彻底不亮：`mute=["*"]` 是后端约定的整句静音标记，连兜底也不压 */
  const muteSentence = (text: string) => {
    const rest = sentences.filter((item) => item.text !== text)
    commit(regions, [...rest, { text, targets: [], mute: ['*'] }])
  }

  /** 手绘框绑定了画框时的页图指纹；页图变了（重出/换版）就提示人工复核坐标 */
  const isStaleRect = (item: HighlightRegionItem) =>
    Boolean(item.shape_sha && data?.image_sha256 && item.shape_sha !== data.image_sha256)

  const frameClass = (id: string) => {
    const rule = ruleOf(id)
    const selected = selectedId === id
    if (selected) return 'border-2 border-solid border-white ring-2 ring-[#5645D4]'
    if (!rule) return 'border border-dashed border-[#5645D4]/40 hover:border-[#5645D4]'
    if (rule.mode === 'off') return 'border border-dashed border-[#A4A097]'
    if (rule.mode === 'area') return 'border border-solid border-[#5645D4]'
    return 'border border-solid border-[#5645D4]/70'
  }

  const areaFill = (id: string) => {
    const rule = ruleOf(id)
    if (!rule || rule.mode !== 'area') return undefined
    return rule.color ? `${rule.color}55` : 'rgba(86, 69, 212, 0.35)'
  }

  const regionTab = (
    <div className="flex flex-col gap-3">
      <Space size={12} wrap>
        <Space size={6}>
          <Switch size="small" checked={drawing} onChange={setDrawing} />
          <Text className="!text-[12px]">手绘区域（在图上拖一个框）</Text>
        </Space>
        <Space size={6}>
          <Switch size="small" checked={showAllFrames} onChange={setShowAllFrames} />
          <Text className="!text-[12px]">显示全部可点选元素</Text>
        </Space>
        {regions.length > 0 && (
          <Button size="small" type="text" danger onClick={() => commit([], sentences)}>
            清空区域
          </Button>
        )}
      </Space>

      <div
        ref={canvasRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        className={`relative w-full overflow-hidden rounded-lg bg-black select-none ${
          drawing ? 'cursor-crosshair' : 'cursor-default'
        }`}
        style={{ aspectRatio: `${pageWidth} / ${pageHeight}` }}
      >
        {slide.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={slide.image_url}
            alt={`第 ${slide.slide_no} 页`}
            decoding="async"
            draggable={false}
            className="pointer-events-none h-full w-full object-contain"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <Text className="!text-[#A4A097]">页面图尚未生成，只能先手绘区域</Text>
          </div>
        )}

        {/* 未配置元素的淡框：仅作可点提示，避免整页元素压住配置框 */}
        {showAllFrames &&
          elements.map((element) =>
            ruleOf(element.element_id) ? null : (
              <button
                key={element.element_id}
                type="button"
                title={`${element.label}：${element.text || '（无文字）'}`}
                onClick={() => selectElement(element.element_id)}
                className={`absolute ${frameClass(element.element_id)} rounded-[2px] bg-transparent`}
                style={frameStyle(element)}
              />
            ),
          )}

        {/* 已配置区域：元素 + 手绘 */}
        {regions.map((item) => {
          const element = elements.find((candidate) => candidate.element_id === item.id)
          const style = element ? frameStyle(element) : item.rect ? rectStyle(item.rect) : null
          if (!style) return null
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelectedId(item.id)}
              title={elementLabel(item.id)}
              className={`absolute ${frameClass(item.id)} rounded-[2px]`}
              style={{ ...style, background: areaFill(item.id) }}
            />
          )
        })}

        {draftRect && (
          <div
            className="pointer-events-none absolute border-2 border-dashed border-[#FF3B30] bg-[#FF3B30]/20"
            style={rectStyle(draftRect)}
          />
        )}
      </div>

      {regions.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <span className="text-[12px] text-[#A4A097]">
              还没配置区域：默认按讲稿自动判定，点上面的元素或手绘一块即可覆盖
            </span>
          }
        />
      ) : (
        <div className="flex max-h-[320px] flex-col gap-2 overflow-y-auto">
          {regions.map((item) => (
            <div
              key={item.id}
              className={`flex flex-wrap items-center gap-2 rounded-lg border p-2 ${
                selectedId === item.id ? 'border-[#5645D4] bg-[#5645D4]/[0.04]' : 'border-[#E5E3DF] bg-white'
              }`}
            >
              <Tag color={isManual(item.id) ? 'gold' : 'blue'} className="!m-0">
                {isManual(item.id) ? '手绘' : '元素'}
              </Tag>
              <Text className="!max-w-[200px] !text-[12px]" ellipsis={{ tooltip: elementLabel(item.id) }}>
                {elementLabel(item.id)}
              </Text>
              {isStaleRect(item) && (
                <Tag color="warning" className="!m-0">
                  坐标待复核
                </Tag>
              )}
              <Segmented
                size="small"
                value={item.mode}
                options={REGION_MODE_OPTIONS}
                onChange={(next) => patchRegion(item.id, { mode: next as RegionMode })}
              />
              {item.mode === 'area' && (
                <>
                  <ColorPicker
                    size="small"
                    value={item.color ?? '#FF3B30'}
                    onChange={(color) => patchRegion(item.id, { color: color.toHexString().toUpperCase() })}
                  />
                  <Slider
                    className="!w-[110px]"
                    min={0}
                    max={255}
                    value={item.fill_alpha ?? DEFAULT_FILL_ALPHA}
                    onChange={(next) => patchRegion(item.id, { fill_alpha: next })}
                    tooltip={{ formatter: (value) => `底色 ${Math.round(((value ?? 0) / 255) * 100)}%` }}
                  />
                </>
              )}
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => removeRegion(item.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const sentenceTab = (
    <div className="flex flex-col gap-2">
      <Text className="!text-[12px] text-[#A4A097]">
        逐句微调只改「这句讲哪些区域 / 这句哪些区域不亮」，不改颜色；留空即按讲稿自动判定。
        标「兜底」的句子是系统自己猜的，确认不对就点「这句不亮」。
      </Text>
      {(data?.sentences ?? []).length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本页还没有讲稿，先写讲稿再逐句微调" />
      ) : (
        <div className="flex max-h-[520px] flex-col gap-2 overflow-y-auto">
          {(data?.sentences ?? []).map((sentence) => {
            const rule = sentences.find((item) => item.text === sentence)
            const hint = hintOf(sentence)
            const isFallback = hint?.fallback === 'guess' || hint?.fallback === 'page'
            const mutedWhole = (rule?.mute ?? []).includes('*')
            return (
              <div key={sentence} className="rounded-lg border border-[#E5E3DF] bg-white p-2">
                <Space size={6} wrap>
                  <Text className="!text-[12px]">{sentence}</Text>
                  {isFallback && (
                    <Tag color="warning" className="!m-0 !text-[11px]">
                      {FALLBACK_LABEL[hint?.fallback ?? ''] ?? '兜底'}
                    </Tag>
                  )}
                  {mutedWhole && (
                    <Tag className="!m-0 !text-[11px]">这句已设为不亮</Tag>
                  )}
                  {isFallback && !mutedWhole && (
                    <Button size="small" type="link" onClick={() => muteSentence(sentence)}>
                      这句不亮
                    </Button>
                  )}
                </Space>
                <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
                  <Select
                    mode="multiple"
                    size="small"
                    allowClear
                    maxTagCount="responsive"
                    placeholder="这句讲哪些区域（留空=自动）"
                    value={rule?.targets ?? []}
                    options={regionOptions}
                    onChange={(next) => updateSentence(sentence, 'targets', next)}
                  />
                  <Select
                    mode="multiple"
                    size="small"
                    allowClear
                    maxTagCount="responsive"
                    placeholder="这句哪些区域不亮"
                    value={(rule?.mute ?? []).filter((id) => id !== '*')}
                    options={regionOptions}
                    onChange={(next) => updateSentence(sentence, 'mute', next)}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )

  return (
    <Drawer
      title={
        <span>
          <HighlightOutlined className="text-[#5645D4]" /> 高亮区域 · 第 {slide.slide_no} 页
        </span>
      }
      width="min(960px, 100vw)"
      open={open}
      onClose={onClose}
      destroyOnHidden
      styles={{
        header: { borderBottom: '1px solid #e5e3df', padding: '16px 24px' },
        body: { padding: '16px 24px', background: '#FCFCFB' },
      }}
      footer={
        <Space className="w-full justify-end">
          <Button onClick={onClose}>关闭</Button>
        </Space>
      }
    >
      <Alert
        type="info"
        showIcon
        className="!mb-3"
        message="改完记得保存"
        description="这里只是草稿，回到编辑区点「保存本页」才会生效。系统按页面上的实际位置计算高亮；换过页面图的页，手画的框可能偏，需要再核一次。"
      />
      <Spin spinning={loading}>
        <Tabs
          size="small"
          items={[
            { key: 'regions', label: `区域（${regions.length}）`, children: regionTab },
            { key: 'sentences', label: `按句微调（${sentences.length}）`, children: sentenceTab },
          ]}
        />
      </Spin>
    </Drawer>
  )
}