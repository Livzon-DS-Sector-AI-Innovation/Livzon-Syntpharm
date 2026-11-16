'use client'

import { memo, useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Button, Empty, Flex, Spin, Tooltip } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { fetchReportGenDocumentBlob } from '@/lib/api/client/research/report-gen'
import {
  APPENDED_ITEM_KINDS,
  fieldStateMeta,
  positionLocateText,
  type ReportGenFieldItem,
  type ReportGenOutline,
} from '@/types/research/report-gen'
import { useDocxPreview } from './useDocxPreview'

interface Props {
  jobId: string
  data?: ReportGenOutline
  /**
   * 任务是否已有成品文档。
   *
   * 由任务状态决定，不能用清单里的 has_document：清单只随轮次变化，任务刚完成时
   * 拿到的还是完成前那一份（has_document=false），会把预览一直卡在空态，只能刷新整页。
   */
  hasDocument?: boolean
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
 * 表格 → 虚拟网格：按 ``colspan`` / ``rowspan`` 占位，把每个单元格放回它在网格里的列号。
 *
 * 直接拿 ``row.children`` 的下标当列号，一遇合并单元格就会从这一格开始整体错位：
 * 后端（python-docx）的 ``t{表}r{行}c{列}`` 是网格坐标，合并区按其首个网格位置记一个 key，
 * 两边必须用同一套坐标，否则高亮和「点哪改哪」会落到隔壁格。
 */
function buildVirtualGrid(table: HTMLElement): (HTMLElement | null)[][] {
  const grid: (HTMLElement | null)[][] = []
  const rows = Array.from(table.querySelectorAll('tr'))
  rows.forEach((row, rowIndex) => {
    const line: (HTMLElement | null)[] = (grid[rowIndex] ??= [])
    let col = 0
    for (const node of Array.from(row.children)) {
      if (node.tagName !== 'TD' && node.tagName !== 'TH') continue
      const cell = node as HTMLTableCellElement
      while (line[col]) col += 1
      const colSpan = Math.max(cell.colSpan || 1, 1)
      const rowSpan = Math.max(cell.rowSpan || 1, 1)
      for (let dr = 0; dr < rowSpan; dr += 1) {
        const target: (HTMLElement | null)[] = (grid[rowIndex + dr] ??= [])
        for (let dc = 0; dc < colSpan; dc += 1) target[col + dc] = cell
      }
      col += colSpan
    }
  })
  return grid
}

/**
 * 给渲染出的 DOM 打位置标记。
 *
 * 表格按下标对应 `document.tables`（表格数量与顺序不会被分页符改变）；
 * 段落按对齐结果对应 `document.paragraphs`，表格内的 `<p>` 一律不计入。
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
    const grid = buildVirtualGrid(table)
    grid.forEach((line, rowIndex) => {
      line.forEach((cell, colIndex) => {
        // 合并单元格在网格里会出现多次：只在首次出现的坐标打标记，
        // 与后端「按底层 w:tc 去重、key 取首个网格坐标」的规则一致
        if (!cell || cell.dataset.posKey) return
        const key = `${prefix}r${rowIndex}c${colIndex}`
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
    })
  })

  return { hits, total, domParagraphs: paragraphs.length, aligned }
}

/**
 * 选中态：描边加粗并滚到预览区中间；取消时按原语义恢复虚线框。
 *
 * 只滚预览自己的滚动容器，不用 `scrollIntoView`：后者会连带把整页滚走，
 * 标题、工具条被顶出视口后整个预览看起来像「没了」。
 */
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
  const scroller = target.closest<HTMLElement>('[data-docx-scroll]')
  if (!scroller) return
  const targetRect = target.getBoundingClientRect()
  const scrollerRect = scroller.getBoundingClientRect()
  const top =
    scroller.scrollTop + (targetRect.top - scrollerRect.top) - (scroller.clientHeight - targetRect.height) / 2
  scroller.scrollTo({ top: Math.max(top, 0), behavior: 'smooth' })
}

/**
 * 内嵌文档预览：左侧「点哪改哪」的落点。
 *
 * 仍用 docx-preview 渲染（不转 PDF）：PDF 里没有可点击的元素，段落与表格也就无法
 * 与清单里的位置一一对应。标记是叠加层，不改动文档本身的排版。
 */
export const ReportGenPreviewPane = memo(function ReportGenPreviewPane({
  jobId,
  data,
  hasDocument,
  selectedKey,
  onSelect,
  documentVersion = 0,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  // 记录「哪一份 blob 渲染进了哪个容器节点」：容器节点被 React 换掉时也必须重渲，
  // 只比 blob 的话新节点会一直是空白
  const renderedRef = useRef<{ blob: Blob; container: HTMLElement } | null>(null)
  const { renderDocx, loading, error } = useDocxPreview()
  const [marks, setMarks] = useState<MarkResult | null>(null)

  const documentReady = hasDocument ?? !!data?.has_document

  const {
    data: blob,
    isFetching,
    error: blobError,
    refetch,
  } = useQuery({
    queryKey: ['report-gen-document', jobId, documentVersion],
    queryFn: () => fetchReportGenDocumentBlob(jobId),
    enabled: documentReady,
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
    // 有文档就先把文档渲染出来，清单还没到（或还是完成前那一份）不影响出稿
    if (!container || !blob) return
    let cancelled = false
    // 清单变化（刷新/编辑）时只重标，不重新下载重渲：docx-preview 重渲一次有明显闪烁
    const needRender = renderedRef.current?.blob !== blob || renderedRef.current?.container !== container
    void (async () => {
      if (needRender) {
        // 只有渲染成功才记账：失败时下次重渲染还会再试，不会一直停在空白
        const rendered = await renderDocx(blob, container)
        if (rendered) renderedRef.current = { blob, container }
      }
      if (cancelled) return
      setMarks(data ? applyMarks(container, data) : null)
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

  if (!documentReady) {
    return (
      <Flex align="center" justify="center" style={{ height: '100%', minHeight: 320, background: '#FAFBFC' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={data ? '生成完成后，这里会显示可以对照的文档' : '正在读取文档结构'}
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
          <span>{positionLocateText(marks)}</span>
          {appendedCount > 0 && <span>· 文末另有 {appendedCount} 处补充内容</span>}
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
          message={`有 ${missCount} 处版式较复杂，预览里没能高亮，请在右侧清单里点选`}
        />
      )}
      {(error || (blobError && !blob)) && (
        <Alert
          type="error"
          showIcon
          banner
          message="文档预览没能打开"
          description={
            <Tooltip title={error ?? (blobError instanceof Error ? blobError.message : '文档下载失败')}>
              <span style={{ fontSize: 12 }}>
                可以先点右上角「重新加载」重试，或直接下载 Word 文档查看；改动不受影响。
              </span>
            </Tooltip>
          }
        />
      )}

      <div
        data-docx-scroll
        style={{ position: 'relative', flex: 1, minHeight: 0, overflow: 'auto', padding: '16px 8px 40px' }}
      >
        {(loading || (isFetching && !blob)) && (
          <Flex align="center" justify="center" style={{ position: 'absolute', inset: 0, zIndex: 2 }}>
            <Spin tip="正在加载文档预览" />
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
})