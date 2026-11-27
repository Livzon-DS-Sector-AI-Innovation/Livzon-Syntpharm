'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { QcBatchRow, QcItem, QcLevel } from '@/types/qc-report'
import { QC_EMPTY, QC_LEVEL_LABEL, QC_LEVEL_STYLE } from '@/types/qc-report'

interface TipState {
  item: QcItem
  batchNo: string
  actual: string | null
  level: QcLevel
  /** 被悬停单元格的视口矩形：浮层贴格子定位，鼠标在格内移动不会漂移 */
  anchorRect: { top: number; bottom: number; left: number }
}

interface Props {
  items: QcItem[]
  batches: QcBatchRow[]
}

const SOURCE_LABEL: Record<string, string> = {
  excel: '结果表',
  docx: '标准表',
  none: '人工留空',
  mixed: '两份文件（各层分别取用）',
}

interface HeaderGroup {
  members: QcItem[]
  span: number
}

function groupItems(items: QcItem[]): HeaderGroup[] {
  const groups: HeaderGroup[] = []
  for (const item of items) {
    const key = item.column_group_start ?? item.sort_order
    const last = groups[groups.length - 1]
    const lastKey = last ? (last.members[0].column_group_start ?? last.members[0].sort_order) : null
    if (last && lastKey === key) {
      last.members.push(item)
      last.span += 1
    } else {
      groups.push({ members: [item], span: 1 })
    }
  }
  return groups
}

function colLetter(index: number): string {
  let n = index
  let text = ''
  while (n > 0) {
    text = String.fromCharCode(65 + ((n - 1) % 26)) + text
    n = Math.floor((n - 1) / 26)
  }
  return text
}

/** 批号列固定宽度，其余列按项目名长度分档，避免长名挤、短名浪费。 */
const BATCH_COL_WIDTH = 150

function columnWidth(item: QcItem): number {
  const length = [...item.item_name.replace(/\n/g, '')].length
  if (length <= 4) return 76
  if (length <= 6) return 96
  if (length <= 9) return 116
  return 136
}

const STICKY_HEAD = { background: 'linear-gradient(180deg,#F6F5FE,#F1EFFD)' }

export function QcReportTable({ items, batches }: Props) {
  const [tip, setTip] = useState<TipState | null>(null)
  const groups = groupItems(items)
  const hasSubHeader = items.some((item) => Boolean(item.sub_label))
  const totalWidth = BATCH_COL_WIDTH + items.reduce((sum, item) => sum + columnWidth(item), 0)

  const topBarRef = useRef<HTMLDivElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  const syncing = useRef(false)
  const [tableWidth, setTableWidth] = useState(0)
  const tipRef = useRef<HTMLDivElement>(null)
  // 关闭加一点延迟：鼠标在相邻单元格之间移动时不会一闪一灭。
  // 真正的「离开」判定挂在整块表格容器上，鼠标停在下方留白处浮层仍然保留。
  const closeTimer = useRef<number | null>(null)

  function cancelClose() {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current)
      closeTimer.current = null
    }
  }

  function scheduleClose() {
    cancelClose()
    closeTimer.current = window.setTimeout(() => setTip(null), 120)
  }

  useEffect(() => cancelClose, [])

  // 浮层按真实尺寸贴边：下方放不下就翻到鼠标上方，左右也不越界。
  // 直接写 el.style 而不 setState，避免级联渲染；初始坐标用锚点兜底。
  useLayoutEffect(() => {
    const element = tipRef.current
    if (!element || !tip) return
    const rect = element.getBoundingClientRect()
    const margin = 10
    const { anchorRect } = tip

    // 水平：与单元格左边缘对齐，右侧放不下则整体左推，最后夹在视口内
    let left = anchorRect.left
    if (left + rect.width > window.innerWidth - margin) {
      left = window.innerWidth - rect.width - margin
    }
    left = Math.max(margin, left)

    // 垂直：优先贴在格子下方 8px；放不下翻到上方；都放不下就贴底
    let top = anchorRect.bottom + 8
    if (top + rect.height > window.innerHeight - margin) {
      const above = anchorRect.top - rect.height - 8
      top = above >= margin ? above : Math.max(margin, window.innerHeight - rect.height - margin)
    }

    element.style.left = `${left}px`
    element.style.top = `${top}px`
  }, [tip])

  useEffect(() => {
    const element = bodyRef.current
    if (!element) return
    const measure = () => setTableWidth(element.scrollWidth)
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    measure()
    return () => observer.disconnect()
  }, [items.length])

  function handleTopScroll() {
    if (syncing.current || !bodyRef.current || !topBarRef.current) return
    syncing.current = true
    bodyRef.current.scrollLeft = topBarRef.current.scrollLeft
    requestAnimationFrame(() => {
      syncing.current = false
    })
  }

  function handleBodyScroll() {
    if (syncing.current || !bodyRef.current || !topBarRef.current) return
    syncing.current = true
    topBarRef.current.scrollLeft = bodyRef.current.scrollLeft
    requestAnimationFrame(() => {
      syncing.current = false
    })
  }

  function showTip(event: React.MouseEvent, item: QcItem, batch: QcBatchRow) {
    const actual = batch.values[item.id] ?? null
    const level = (batch.levels[item.id] ?? 'pending') as QcLevel
    const rect = event.currentTarget.getBoundingClientRect()
    setTip({
      item,
      batchNo: batch.batch_no,
      actual,
      level,
      anchorRect: { top: rect.top, bottom: rect.bottom, left: rect.left },
    })
  }

  return (
    <>
      <div
        onMouseLeave={scheduleClose}
        style={{ minHeight: 'min(520px, calc(100vh - 300px))' }}
      >
        <div
          ref={topBarRef}
          onScroll={handleTopScroll}
          className="h-3 overflow-x-auto [&::-webkit-scrollbar]:h-2.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-[#DCDAF1] [&::-webkit-scrollbar-track]:bg-transparent"
          aria-hidden
        >
          <div style={{ width: tableWidth || undefined, height: 1 }} />
        </div>

        <div
          ref={bodyRef}
          onScroll={handleBodyScroll}
          className="overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
        <table
          className="qc-table table-fixed border-separate border-spacing-0 text-[13px]"
          style={{ width: totalWidth }}
        >
          <colgroup>
            <col style={{ width: BATCH_COL_WIDTH }} />
            {items.map((item) => (
              <col key={item.id} style={{ width: columnWidth(item) }} />
            ))}
          </colgroup>

          <thead>
            <tr>
              <th
                rowSpan={hasSubHeader ? 2 : 1}
                className="text-center"
                style={{
                  position: 'sticky',
                  left: 0,
                  top: 0,
                  zIndex: 7,
                  background: '#F3F1FD',
                  boxShadow: '2px 0 6px -2px rgba(31,41,55,.08)',
                }}
              >
                批号
              </th>

              {groups.map((group) => {
                const head = group.members[0]
                const range =
                  group.span > 1
                    ? `${colLetter(head.sort_order)}–${colLetter(group.members[group.span - 1].sort_order)}`
                    : colLetter(head.sort_order)
                const title = [
                  head.item_name,
                  `列 ${range}`,
                  `法定：${head.legal_text ?? QC_EMPTY}`,
                  `内控：${head.internal_text ?? QC_EMPTY}`,
                  `3σ：${head.sigma_text ?? QC_EMPTY}`,
                ].join('\n')
                const baseClass = 'text-center border-b border-l border-[#E4E1F5] px-2'

                if (group.span > 1) {
                  return (
                    <th key={`g-${head.id}`} colSpan={group.span} title={title} className={baseClass} style={STICKY_HEAD}>
                      <span className="block truncate leading-tight">{head.item_name}</span>
                    </th>
                  )
                }
                return (
                  <th
                    key={`g-${head.id}`}
                    rowSpan={hasSubHeader ? 2 : 1}
                    title={title}
                    className={baseClass}
                    style={STICKY_HEAD}
                  >
                    <span className="block truncate leading-tight">{head.item_name}</span>
                  </th>
                )
              })}
            </tr>

            {hasSubHeader && (
              <tr>
                {groups
                  .filter((group) => group.span > 1)
                  .flatMap((group) =>
                    group.members.map((member) => (
                      <th
                        key={`s-${member.id}`}
                        title={`${member.item_name} ${colLetter(member.sort_order)}\n法定：${member.legal_text ?? QC_EMPTY}`}
                        className="border-b border-l border-[#E4E1F5] px-1 text-center text-[11px] font-medium"
                        style={{ ...STICKY_HEAD, color: '#8B87B0', height: 28 }}
                      >
                        <span className="block truncate leading-tight">{member.sub_label ?? ''}</span>
                      </th>
                    )),
                  )}
              </tr>
            )}
          </thead>

          <tbody>
            {batches.map((batch, rowIndex) => {
              const railLevel = batch.level as QcLevel
              const rail =
                railLevel === 'skip' || railLevel === 'pending'
                  ? 'transparent'
                  : QC_LEVEL_STYLE[railLevel].dot

              return (
                <tr
                  key={batch.id}
                  className="group"
                  style={{ animationDelay: `${Math.min(rowIndex * 25, 300)}ms` }}
                >
                  <td
                    className="qc-batch text-center text-[13px]"
                    style={{
                      position: 'sticky',
                      left: 0,
                      zIndex: 2,
                      background: '#fff',
                      boxShadow: `inset 3px 0 0 ${rail}, 2px 0 6px -2px rgba(31,41,55,.08)`,
                    }}
                  >
                    <span className="block truncate">{batch.batch_no}</span>
                  </td>

                  {items.map((item) => {
                    const actual = batch.values[item.id] ?? null
                    const level = (batch.levels[item.id] ?? 'pending') as QcLevel
                    const empty = actual === null || actual === ''
                    const tinted = level === 'oos' || level === 'internal' || level === 'trend'
                    const tone = QC_LEVEL_STYLE[level]

                    return (
                      <td
                        key={item.id}
                        onMouseEnter={(event) => {
                          cancelClose()
                          showTip(event, item, batch)
                        }}
                        className="cursor-default px-1 text-center"
                      >
                        {empty ? (
                          <span className="text-[12px] italic text-[var(--ink-3)]">{QC_EMPTY}</span>
                        ) : tinted ? (
                          <span
                            className="qc-cell max-w-full"
                            style={{
                              backgroundColor: tone.bg,
                              color: tone.text,
                              borderColor: tone.border,
                            }}
                          >
                            <span className="qc-num truncate font-bold">{actual}</span>
                          </span>
                        ) : (
                          <span className="qc-num block truncate text-[var(--ink)]">{actual}</span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
        </div>
      </div>

      {tip &&
        typeof document !== 'undefined' &&
        createPortal(
        <div
          ref={tipRef}
          className="pointer-events-none fixed z-[80] w-[320px] rounded-xl border border-[var(--hairline)] bg-white px-3 py-2.5 shadow-[0_12px_32px_rgba(31,41,55,0.14)]"
          style={{
            left: tip.anchorRect.left,
            top: tip.anchorRect.bottom + 8,
            maxHeight: 'calc(100vh - 40px)',
            overflowY: 'auto',
          }}
        >
          <p className="flex items-center justify-between text-[12px] font-semibold text-[var(--ink)]">
            <span className="truncate">{tip.item.item_name.replace(/\n/g, '')}</span>
            <span
              className="qc-pill ml-2 shrink-0 px-2 py-[2px]"
              style={{
                color: QC_LEVEL_STYLE[tip.level].text,
                backgroundColor: QC_LEVEL_STYLE[tip.level].bg,
                borderColor: QC_LEVEL_STYLE[tip.level].border,
              }}
            >
              <span className="sq" style={{ backgroundColor: QC_LEVEL_STYLE[tip.level].dot }} />
              {QC_LEVEL_LABEL[tip.level]}
            </span>
          </p>
          <p className="mt-0.5 text-[11px] text-[var(--ink-3)]">
            列 {colLetter(tip.item.sort_order)}
            {tip.item.sub_label ? ` · ${tip.item.sub_label}` : ''}
            {tip.item.standard_item_name && tip.item.standard_item_name !== tip.item.item_name
              ? ` · 标准表对应「${tip.item.standard_item_name}」`
              : ''}
            {tip.item.standard_source
              ? ` · 标准取自${SOURCE_LABEL[tip.item.standard_source] ?? tip.item.standard_source}`
              : ''}
          </p>
          <dl className="mt-1.5 space-y-1 text-[12px]">
            <div className="flex gap-2">
              <dt className="w-[64px] shrink-0 text-[var(--ink-3)]">法定标准</dt>
              <dd className="flex-1 break-all text-[var(--ink)]">{tip.item.legal_text ?? QC_EMPTY}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-[64px] shrink-0 text-[var(--ink-3)]">内控标准</dt>
              <dd className="flex-1 break-all text-[var(--ink)]">{tip.item.internal_text ?? QC_EMPTY}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-[64px] shrink-0 text-[var(--ink-3)]">3σ 标准</dt>
              <dd className="flex-1 break-all text-[var(--ink)]">{tip.item.sigma_text ?? QC_EMPTY}</dd>
            </div>
            <div className="flex gap-2 border-t border-[var(--hairline)] pt-1">
              <dt className="w-[64px] shrink-0 text-[var(--ink-3)]">本格数值</dt>
              <dd className="qc-num flex-1 text-[var(--ink)]">
                {tip.actual === null || tip.actual === '' ? QC_EMPTY : tip.actual}
                <span className="ml-1 font-sans text-[11px] text-[var(--ink-3)]">· {tip.batchNo}</span>
              </dd>
            </div>
          </dl>
        </div>,
          document.body,
        )}
    </>
  )
}
