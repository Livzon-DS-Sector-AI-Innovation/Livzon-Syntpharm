'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Button, Empty, Flex, Spin, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { fetchReportGenDocumentBlob } from '@/lib/api/client/research/report-gen'
import {
  APPENDED_ITEM_KINDS,
  fieldStateMeta,
  type ReportGenFieldItem,
  type ReportGenOutline,
} from '@/types/research/report-gen'
import { useDocxPreview } from './useDocxPreview'

interface Props {
  jobId: string
  data?: ReportGenOutline
  selectedKey: string | null
  onSelect: (item: ReportGenFieldItem) => void
  /** 文档换版（编辑保存后）时递增，触发重新拉取与重渲 */
  documentVersion?: number
}

interface MarkResult {
  hits: number
  total: number
  domParagraphs: number
  /** 段落数与成品对不上时是否走了按内容对齐（docx-preview 会拆分页符段落） */
  aligned: boolean
}

// 参考资料不写进文档，也就没有可标记的 DOM，不能算「文末追加内容」
const APPENDED_KINDS = APPENDED_ITEM_KINDS

function decorate(element: HTMLElement, item: ReportGenFieldItem): void {
  const meta = fieldStateMeta(item.state, item.edit_source)
  element.dataset.posKey = item.key
  element.dataset.posState = item.state
  element.dataset.posBorder = meta.border
  element.dataset.posDashed = meta.dashed ? '1' : '0'
  element.title = `${item.section ? `${item.section} · ` : ''}${item.label} · ${meta.label}`
  if (item.state === 'locked') return
  element.style.cursor = 'pointer'
  element.style.transition = 'background-color 120ms ease'
  if (item.state !== 'blank') element.style.backgroundColor = meta.bg
  element.style.boxShadow = `inset 3px 0 0 ${meta.text}`
  if (meta.dashed) {
    element.style.outline = `1px dashed ${meta.border}`
    element.style.outlineOffset = '1px'
  }
}

/**
 * 取 docx-preview 渲染出的正文块。
 *
 * docx-preview 的结构是「一页一个 `section.docx`，页内正文包在 `article` 里」
 * （见 docx-preview.js 的 `renderSections`：section 按分页切开、每页一个 article），
 * 所以必须遍历**所有**页，只取 article 的直属 p/table：
 * - 只取第一个 section 会漏掉第二页之后的所有位置；
 * - 递归进 table 会把单元格里的段落也当成正文段落，段落下标立刻错位；
 * - article 外的 header/footer/footnote 也要排除，它们不属于正文。
 */
function collectBlocks(root: HTMLElement): HTMLElement[] {
  const pages = Array.from(root.querySelectorAll<HTMLElement>('section.docx'))
  const scopes = pages.length ? pages : [root]
  const blocks: HTMLElement[] = []
  for (const scope of scopes) {
    const articles = Array.from(scope.querySelectorAll<HTMLElement>(':scope > article'))
    const containers = articles.length ? articles : [scope]
    for (const container of containers) {
      for (const child of Array.from(container.children)) {
        if (child.tagName === 'P' || child.tagName === 'TABLE') blocks.push(child as HTMLElement)
      }
    }
  }
  return blocks
}

function clearMarks(container: HTMLElement): void {
  container.querySelectorAll<HTMLElement>('[data-pos-key]').forEach((element) => {
    element.removeAttribute('data-pos-key')
    element.removeAttribute('data-pos-state')
    element.removeAttribute('title')
    element.style.backgroundColor = ''
    element.style.boxShadow = ''
    element.style.outline = ''
    element.style.cursor = ''
  })
}

function normalizeText(text: string): string {
  return text.replace(/\s+/g, '').slice(0, 60)
}

/**
 * DOM 段落 → 成品段落下标。
 *
 * 为什么不直接按下标：docx-preview 会把「只含分页符的段落」拆成两段，DOM 段数比
 * python-docx 多，从分页符开始后面全部错位。这里用段落文本做序列对齐：先按顺序比，
 * 比不中就在后 3 段里找（拆段后的后半段），拆出来的空段与当前空段共享同一个下标。
 * 返回 -1 表示对不上——宁可不标，也不能标到别的段落上。
 */
function alignParagraphs(domTexts: string[], docTexts: string[]): number[] {
  const mapping = new Array<number>(domTexts.length).fill(-1)
  let cursor = 0
  for (let index = 0; index < domTexts.length; index += 1) {
    const text = normalizeText(domTexts[index])
    if (cursor < docTexts.length && normalizeText(docTexts[cursor]) === text) {
      mapping[index] = cursor
      cursor += 1
      continue
    }
    let found = -1
    for (let probe = cursor; probe < Math.min(cursor + 3, docTexts.length); probe += 1) {
      if (normalizeText(docTexts[probe]) === text) {
        found = probe
        break
      }
    }
    if (found >= 0) {
      mapping[index] = found
      cursor = found + 1
      continue
    }
    if (!text && cursor < docTexts.length && !normalizeText(docTexts[cursor])) {
      // 分页符拆出来的空段：与当前成品空段共用下标，但游标不前进
      mapping[index] = cursor
    }
  }
  return mapping
}

/**
 * 给渲染出的 DOM 打位置标记。
 *
 * 表格按下标对应 `document.tables`（表格数量与顺序不会被分页符改变）；
 * 段落按对齐结果对应 `document.paragraphs`，表格内的 `<p>` 一律不计入。
 * 合并单元格会让 td 序号与 outline 的 col 错位，命中率要回报给用户看。
 */
function applyMarks(container: HTMLElement, data: ReportGenOutline): MarkResult {
  clearMarks(container)
  const writable = new Map((data.items ?? []).map((item) => [item.key, item]))
  const locked = new Map((data.locked_items ?? []).map((item) => [item.key, item]))
  const blocks = collectBlocks(container)
  const paragraphs = blocks.filter((block) => block.tagName === 'P')
  const tables = blocks.filter((block) => block.tagName === 'TABLE')

  const docTexts = data.document_paragraph_texts ?? []
  const domTexts = paragraphs.map((paragraph) => paragraph.textContent ?? '')
  const aligned = docTexts.length > 0 && docTexts.length !== paragraphs.length
  const indexMap = aligned
    ? alignParagraphs(domTexts, docTexts)
    : paragraphs.map((_, index) => index)

  let hits = 0
  let total = 0

  paragraphs.forEach((element, domIndex) => {
    const paragraphIndex = indexMap[domIndex]
    if (paragraphIndex === undefined || paragraphIndex < 0) return
    const key = `p${paragraphIndex}`
    const item = writable.get(key)
    if (item) {
      total += 1
      hits += 1
      decorate(element, item)
      return
    }
    const lockedItem = locked.get(key)
    if (lockedItem) decorate(element, lockedItem)
  })

  tables.forEach((table, tableIndex) => {
    const prefix = `t${tableIndex}`
    for (const row of Array.from(table.querySelectorAll('tr'))) {
      const cells = Array.from(row.children).filter(
        (cell) => cell.tagName === 'TD' || cell.tagName === 'TH',
      ) as HTMLElement[]
      cells.forEach((cell, colIndex) => {
        const key = `${prefix}r${row.rowIndex}c${colIndex}`
        const item = writable.get(key)
        if (item) {
          total += 1
          hits += 1
          decorate(cell, item)
          return
        }
        const lockedItem = locked.get(key)
        if (lockedItem) decorate(cell, lockedItem)
      })
    }
  })

  return { hits, total, domParagraphs: paragraphs.length, aligned }
}

/** 选中态：描边加粗并滚到视口中间；取消时按原语义恢复虚线框。 */
function setSelected(container: HTMLElement, key: string | null): void {
  container.querySelectorAll<HTMLElement>('[data-selected="true"]').forEach((element) => {
    element.dataset.selected = 'false'
    element.style.outline = element.dataset.posDashed === '1' ? `1px dashed ${element.dataset.posBorder}` : ''
    element.style.outlineOffset = '1px'
  })
  if (!key) return
  const target = container.querySelector<HTMLElement>(`[data-pos-key="${key}"]`)
  if (!target) return
  target.dataset.selected = 'true'
  target.style.outline = '2px solid #1677FF'
  target.style.outlineOffset = '2px'
  target.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

/**
 * 内嵌文档预览：左侧「点哪改哪」的落点。
 *
 * 仍用 docx-preview 渲染（不转 PDF）：PDF 里没有可点击的元素，段落与表格也就无法
 * 与清单里的位置一一对应。标记是叠加层，不改动文档本身的排版。
 */
export function ReportGenPreviewPane({ jobId, data, selectedKey, onSelect, documentVersion = 0 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const renderedBlobRef = useRef<Blob | null>(null)
  const { renderDocx, loading, error } = useDocxPreview()
  const [marks, setMarks] = useState<MarkResult | null>(null)

  const { data: blob, isFetching, refetch } = useQuery({
    queryKey: ['report-gen-document', jobId, documentVersion],
    queryFn: () => fetchReportGenDocumentBlob(jobId),
    enabled: !!data?.has_document,
    staleTime: 60_000,
    retry: 1,
  })

  // 清单变化（编辑/刷新）只需要重新打标记，不必重新下载 docx
  const markSignature = useMemo(
    () => (data?.items ?? []).map((item) => `${item.key}:${item.state}:${item.edit_source}`).join('|'),
    [data],
  )

  useEffect(() => {
    const container = containerRef.current
    if (!container || !blob || !data) return
    let cancelled = false
    // 清单变化（刷新/编辑）时只重标，不重新下载重渲：docx-preview 重渲一次有明显闪烁
    const needRender = renderedBlobRef.current !== blob
    void (async () => {
      if (needRender) {
        await renderDocx(blob, container)
        renderedBlobRef.current = blob
      }
      if (cancelled) return
      setMarks(applyMarks(container, data))
    })()
    return () => {
      cancelled = true
    }
    // markSignature 只用于触发重标；标记内容始终取自 data，两者同步
  }, [blob, data, markSignature, renderDocx])

  useEffect(() => {
    if (containerRef.current) setSelected(containerRef.current, selectedKey)
  }, [selectedKey, marks])

  const handleClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const target = (event.target as HTMLElement).closest<HTMLElement>('[data-pos-key]')
    if (!target || !data || !target.dataset.posKey) return
    const key = target.dataset.posKey
    const item =
      data.items?.find((candidate) => candidate.key === key) ??
      data.locked_items?.find((candidate) => candidate.key === key)
    if (item) onSelect(item)
  }

  const missCount = marks ? Math.max(marks.total - marks.hits, 0) : 0
  const appendedCount = (data?.items ?? []).filter((item) => APPENDED_KINDS.includes(item.kind)).length

  if (!data?.has_document) {
    return (
      <Flex align="center" justify="center" style={{ height: '100%', minHeight: 320, background: '#FAFBFC' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={data ? '生成完成后这里显示可对照的文档' : '正在读取文档结构'}
        />
      </Flex>
    )
  }

  return (
    <Flex vertical style={{ height: '100%', minHeight: 0, background: '#F5F7FA' }}>
      <Flex
        align="center"
        justify="space-between"
        gap={8}
        wrap
        style={{ padding: '8px 12px', borderBottom: '1px solid #EDEFF2', background: '#FFFFFF' }}
      >
        <Flex gap={8} align="center" wrap style={{ fontSize: 12, color: '#5A6472' }}>
          <Tag color="processing" style={{ margin: 0 }}>
            可写位置高亮
          </Tag>
          {marks && (
            <span>
              已标记 {marks.hits}/{marks.total} 处
              {marks.aligned ? ' · 已按正文内容对齐' : ''}
              {marks.domParagraphs > 0 ? ` · 正文 ${marks.domParagraphs} 段` : ''}
            </span>
          )}
          {appendedCount > 0 && <span>· 文末另有 {appendedCount} 处追加内容</span>}
        </Flex>
        <Button
          size="small"
          type="text"
          icon={<ReloadOutlined />}
          loading={isFetching || loading}
          onClick={() => void refetch()}
        >
          重新加载
        </Button>
      </Flex>

      {missCount > 0 && (
        <Alert
          type="warning"
          showIcon
          banner
          message={`有 ${missCount} 处位置没能在预览里精准定位（合并单元格或复杂版式），请在右侧清单中点选`}
        />
      )}
      {error && <Alert type="error" showIcon banner message={error} />}

      <div style={{ position: 'relative', flex: 1, minHeight: 0, overflow: 'auto', padding: '16px 8px 40px' }}>
        {(loading || (isFetching && !blob)) && (
          <Flex align="center" justify="center" style={{ position: 'absolute', inset: 0, zIndex: 2 }}>
            <Spin tip="正在渲染文档" />
          </Flex>
        )}
        <div
          ref={containerRef}
          onClick={handleClick}
          style={{
            maxWidth: 860,
            margin: '0 auto',
            background: '#FFFFFF',
            boxShadow: '0 2px 12px rgba(31, 35, 41, 0.08)',
            borderRadius: 4,
            overflow: 'hidden',
          }}
        />
      </div>
    </Flex>
  )
}