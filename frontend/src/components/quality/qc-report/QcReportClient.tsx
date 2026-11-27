'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { fetchQcBatchesClient, fetchQcStatsClient, qcExportUrl } from '@/lib/api/client/qc-report'
import { QcReportTable } from './QcReportTable'
import { QcBatchEntryModal } from './QcBatchEntryModal'
import type { QcBatchPageData, QcItem, QcLevel, QcStats } from '@/types/qc-report'

interface Props {
  productId: string
  productName: string
  abbr: string
  qualityStandard: string | null
  initialItems: QcItem[]
  initialBatches: QcBatchPageData
  initialStats: QcStats
}

const PAGE_SIZE = 50

interface KpiDef {
  key: keyof QcStats | 'total'
  label: string
  /** 悬浮说明，补足被精简掉的括号内容 */
  hint: string
  level: QcLevel | ''
  /** 卡片配色变体：total / green / yellow / orange / red */
  tone: 'total' | 'green' | 'yellow' | 'orange' | 'red'
  icon: string
}

const KPI_DEFS: KpiDef[] = [
  { key: 'total', label: '在库批次', hint: '全部在库批次', level: '', tone: 'total', icon: '▦' },
  { key: 'normal', label: '正常', hint: '三层限值内', level: 'normal', tone: 'green', icon: '✓' },
  { key: 'trend', label: '超趋势', hint: '超趋势（3σ）', level: 'trend', tone: 'yellow', icon: '∿' },
  { key: 'internal', label: '超内控', hint: '超企业内控标准', level: 'internal', tone: 'orange', icon: '⚠' },
  { key: 'oos', label: '超法定', hint: '超法定标准（OOS）', level: 'oos', tone: 'red', icon: '✕' },
]

const TONE_STYLE: Record<KpiDef['tone'], { background: string; color: string; bar: string }> = {
  total: {
    background: 'linear-gradient(135deg,#EFEDFD,#E4E1FB)',
    color: '#4F46C9',
    bar: 'linear-gradient(90deg,#4F46C9,#7C72F0)',
  },
  green: {
    background: 'linear-gradient(135deg,#E9F7EF,#DCF1E5)',
    color: '#1E8E5A',
    bar: 'linear-gradient(90deg,#1E8E5A,#4CB783)',
  },
  yellow: {
    background: 'linear-gradient(135deg,#FBF6DE,#F7EEC9)',
    color: '#9A7B0A',
    bar: 'linear-gradient(90deg,#C9A227,#E0BC42)',
  },
  orange: {
    background: 'linear-gradient(135deg,#FDF3E7,#FBE9D3)',
    color: '#D97A0B',
    bar: 'linear-gradient(90deg,#D97A0B,#F09A3E)',
  },
  red: {
    background: 'linear-gradient(135deg,#FDECEA,#FBDDD9)',
    color: '#D64545',
    bar: 'linear-gradient(90deg,#D64545,#F06A5E)',
  },
}

/** 数字滚动：550ms 缓出，值变化时重新滚。 */
function CountUp({ value }: { value: number }) {
  const [display, setDisplay] = useState(value)
  const frame = useRef<number | null>(null)

  useEffect(() => {
    const duration = 550
    const startedAt = performance.now()
    const from = 0
    const step = (now: number) => {
      const progress = Math.min((now - startedAt) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(from + (value - from) * eased))
      if (progress < 1) frame.current = requestAnimationFrame(step)
    }
    frame.current = requestAnimationFrame(step)
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current)
    }
  }, [value])

  return <>{display}</>
}

export function QcReportClient({
  productId,
  productName,
  abbr,
  qualityStandard,
  initialItems,
  initialBatches,
  initialStats,
}: Props) {
  const items = initialItems
  const [batchPage, setBatchPage] = useState(initialBatches)
  const [stats, setStats] = useState(initialStats)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [level, setLevel] = useState<QcLevel | ''>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [entryOpen, setEntryOpen] = useState(false)

  /** 翻页 / 筛选 / 新增后统一走这里刷新，不在 effect 里发请求。 */
  async function load(nextPage: number, nextKeyword: string, nextLevel: QcLevel | '') {
    setLoading(true)
    setError(null)
    try {
      const [batchData, statsData] = await Promise.all([
        fetchQcBatchesClient({
          productId,
          page: nextPage,
          page_size: PAGE_SIZE,
          batch_no: nextKeyword || undefined,
          level: nextLevel || undefined,
        }),
        fetchQcStatsClient(productId),
      ])
      setBatchPage(batchData)
      setStats(statsData)
      setPage(nextPage)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '数据加载失败')
    } finally {
      setLoading(false)
    }
  }

  function applyLevel(next: QcLevel | '') {
    setLevel(next)
    void load(1, keyword, next)
  }

  const totalPages = Math.max(1, Math.ceil(batchPage.total / PAGE_SIZE))
  // 品种到底有没有数据，要看全量统计，不能看筛选后的条数
  const hasAnyBatch = stats.total > 0
  const isFiltering = Boolean(keyword || level)

  return (
    <div className="p-6">
      <header className="qc-enter mb-[18px] flex flex-wrap items-end justify-between gap-4">
        <div>
          <nav className="qc-crumb">
            <Link href="/quality/inspection">品种台账</Link>
            <span>/</span>
            {/* 看板开发后把这段换成 <Link href={...} aria-current={当前页 ? 'page' : undefined}> 即可 */}
            <span title="本期未开放" className="cursor-default">
              质量数据看板
            </span>
            <span>/</span>
            <Link href={`/quality/inspection/${productId}`} aria-current="page">
              检验数据报表
            </Link>
          </nav>
          <h1 className="qc-page-title">检验数据报表</h1>
          <p className="qc-sub">
            <b style={{ color: 'var(--ink)', fontWeight: 700 }}>
              {productName}
              {abbr ? `（${abbr}）` : ''}
            </b>
            {' · '}
            {qualityStandard || '未填写质量标准'} · <span className="qc-num">{items.length}</span> 个检验项目 ·{' '}
            <span className="qc-num">{batchPage.total}</span> 批
          </p>
        </div>
        <div className="flex gap-2.5">
          <a
            href={qcExportUrl(productId, { batch_no: keyword || undefined, level: level || undefined })}
            className="qc-btn qc-btn-primary"
          >
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path
                d="M8 2.5v7M5 6.5 8 9.5l3-3M2.5 11.5v1a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-1"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            导出当前结果
          </a>
          <button type="button" onClick={() => setEntryOpen(true)} className="qc-btn">
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M8 3v10M3 8h10" strokeLinecap="round" />
            </svg>
            新增检验批次
          </button>
        </div>
      </header>

      <div
        className="qc-enter mb-4 grid grid-cols-2 gap-2.5 min-[720px]:grid-cols-5"
        style={{ animationDelay: '.05s' }}
      >
        {KPI_DEFS.map((kpi) => {
          const active = level === kpi.level
          const value = kpi.key === 'total' ? stats.total : (stats[kpi.key as keyof QcStats] as number)
          const tone = TONE_STYLE[kpi.tone]
          // 0 分两种：真没数据，和「有数据但这层没有超标」
          const hint =
            (value ?? 0) > 0
              ? kpi.hint
              : stats.total === 0
                ? '尚无批次数据'
                : `当前 ${stats.total} 批中无此等级`
          return (
            <button
              key={kpi.key}
              type="button"
              onClick={() => applyLevel(kpi.level)}
              title={hint}
              className={`qc-mini text-left ${active ? 'on' : ''}`}
              style={{ background: tone.background }}
            >
              <span className="absolute inset-x-0 top-0 h-[3px]" style={{ background: tone.bar }} aria-hidden />
              <span className="mico" aria-hidden>
                <span style={{ color: tone.color, fontSize: 13 }}>{kpi.icon}</span>
              </span>
              <span className="min-w-0">
                <span className="n block" style={{ color: tone.color }}>
                  <CountUp value={value ?? 0} />
                </span>
                <span className="l block truncate">{kpi.label}</span>
              </span>
            </button>
          )
        })}
      </div>

      <div className="qc-filterbar qc-enter mb-4" style={{ animationDelay: '.1s' }}>
        <div className="qc-field">
          <label htmlFor="qc-batch-search">批号</label>
          <input
            id="qc-batch-search"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') void load(1, keyword, level)
            }}
            placeholder="模糊搜索，回车确认"
            className="w-[220px]"
          />
        </div>
        <div className="qc-field">
          <label htmlFor="qc-level-filter">判定等级</label>
          <select
            id="qc-level-filter"
            value={level}
            onChange={(event) => {
              const next = event.target.value as QcLevel | ''
              setLevel(next)
              void load(1, keyword, next)
            }}
          >
            <option value="">全部</option>
            <option value="oos">超法定</option>
            <option value="internal">超内控</option>
            <option value="trend">超趋势</option>
            <option value="normal">正常</option>
            <option value="pending">待检</option>
          </select>
        </div>
        {(keyword || level) && (
          <button
            type="button"
            onClick={() => {
              setKeyword('')
              setLevel('')
              void load(1, '', '')
            }}
            className="qc-btn qc-btn-sm"
          >
            重置
          </button>
        )}
        <span className="qc-num ml-auto self-end pb-2 text-[12px] font-semibold text-[var(--ink-3)]">
          {loading ? '加载中…' : `共 ${batchPage.total} 条 · ${items.length} 个项目列`}
        </span>
      </div>

      {error && (
        <p className="mb-3 rounded-lg border border-[#F5CDC8] bg-[#FDECEA] px-3 py-2 text-[12px] text-[#D64545]">
          {error}
        </p>
      )}

      <section
        className="qc-panel qc-enter overflow-hidden"
        style={{ animationDelay: '.15s' }}
      >
        {batchPage.items.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center px-6 py-16 text-center"
            style={{ minHeight: 'min(520px, calc(100vh - 300px))' }}
          >
            {hasAnyBatch ? (
              <>
                <p className="text-[13px] text-[var(--ink-2)]">当前筛选下没有符合条件的批次</p>
                <p className="mt-1 text-[12px] text-[var(--ink-3)]">
                  本品种共 <span className="qc-num">{stats.total}</span> 批数据，只是没有满足当前条件的记录
                </p>
                {isFiltering && (
                  <button
                    type="button"
                    onClick={() => {
                      setKeyword('')
                      setLevel('')
                      void load(1, '', '')
                    }}
                    className="qc-btn qc-btn-sm mt-3"
                  >
                    清除筛选
                  </button>
                )}
              </>
            ) : (
              <>
                <p className="text-[13px] text-[var(--ink-2)]">还没有检验数据</p>
                <p className="mt-1 text-[12px] text-[var(--ink-3)]">
                  点「新增检验批次」录入，或在新建品种时上传结果表
                </p>
              </>
            )}
          </div>
        ) : (
          <QcReportTable items={items} batches={batchPage.items} />
        )}
      </section>

      {batchPage.total > PAGE_SIZE && (
        <div className="mt-3 flex items-center justify-between">
          <span className="qc-num text-[12px] text-[var(--ink-3)]">
            第 {page} / {totalPages} 页
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => void load(Math.max(1, page - 1), keyword, level)}
              className="qc-btn qc-btn-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              上一页
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => void load(Math.min(totalPages, page + 1), keyword, level)}
              className="qc-btn qc-btn-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              下一页
            </button>
          </div>
        </div>
      )}

      <QcBatchEntryModal
        open={entryOpen}
        productId={productId}
        onClose={() => setEntryOpen(false)}
        onCreated={() => void load(page, keyword, level)}
      />
    </div>
  )
}
