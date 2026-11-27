'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import {
  deleteQcProduct,
  fetchQcAttentionBatchesClient,
  fetchQcProductsClient,
} from '@/lib/api/client/qc-report'
import { CreateProductDrawer } from './CreateProductDrawer'
import { QcStandardDrawer } from './QcStandardDrawer'
import { AttentionBatchPanel } from './AttentionBatchPanel'
import { QcLevelPill } from './QcLevelPill'
import type { QcAttentionBatch, QcCategory, QcLevel, QcProductListItem } from '@/types/qc-report'
import {
  QC_CATEGORY_LABEL,
  QC_CATEGORY_OPTIONS,
  QC_LEVEL_OPTIONS,
  QC_LEVEL_STYLE,
} from '@/types/qc-report'

interface Props {
  initialProducts: QcProductListItem[]
  initialAttention: QcAttentionBatch[]
  loadFailed?: boolean
}

/** 四色判定分布条：按各等级占比分段，颜色取判定色的指示方块色。 */
function DistributionBar({ product }: { product: QcProductListItem }) {
  const total = product.batch_count
  if (!total) return <span className="qc-distbar shrink-0" aria-hidden />

  const all: { level: QcLevel; count: number }[] = [
    { level: 'normal', count: product.normal_count },
    { level: 'trend', count: product.trend_count },
    { level: 'internal', count: product.internal_count },
    { level: 'oos', count: product.oos_count },
  ]
  const parts = all.filter((part) => part.count > 0)

  return (
    <span className="qc-distbar shrink-0" title={`正常 ${product.normal_count} · 超趋势 ${product.trend_count} · 超内控 ${product.internal_count} · 超法定 ${product.oos_count}`}>
      {parts.map((part) => (
        <i
          key={part.level}
          style={{ width: `${(part.count / total) * 100}%`, background: QC_LEVEL_STYLE[part.level].dot }}
        />
      ))}
    </span>
  )
}

export function QcProductListClient({ initialProducts, initialAttention, loadFailed }: Props) {
  const [products, setProducts] = useState(initialProducts)
  // 关注批次初始来自 SSR，删除品种后需要局部重取，否则右栏会残留已删品种的数据
  const [attention, setAttention] = useState(initialAttention)
  const [keyword, setKeyword] = useState('')
  const [category, setCategory] = useState<QcCategory | ''>('')
  const [level, setLevel] = useState<QcLevel | ''>('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [standardProduct, setStandardProduct] = useState<QcProductListItem | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const word = keyword.trim().toLowerCase()
    return products.filter((product) => {
      if (category && product.category !== category) return false
      if (level && product.top_level !== level) return false
      if (!word) return true
      return (
        product.name.toLowerCase().includes(word) ||
        product.abbr.toLowerCase().includes(word) ||
        (product.quality_standard ?? '').toLowerCase().includes(word)
      )
    })
  }, [products, keyword, category, level])

  /**
   * 刷新首页两栏数据。
   *
   * 导入完成、标准重判都会走这里：左栏品种与右栏关注批次必须一起更新，
   * 否则会看到「新品种出来了，但它的异常批次没出现」。
   * 用 allSettled 而非 all，一侧接口挂了另一侧照样更新。
   */
  async function refresh() {
    setRefreshing(true)
    const [productResult, attentionResult] = await Promise.allSettled([
      fetchQcProductsClient(),
      fetchQcAttentionBatchesClient(20),
    ])

    if (productResult.status === 'fulfilled') {
      setProducts(productResult.value)
    } else {
      console.error('品种列表刷新失败', productResult.reason)
    }

    if (attentionResult.status === 'fulfilled') {
      setAttention(attentionResult.value)
    } else {
      console.error('需关注批次刷新失败', attentionResult.reason)
    }

    setRefreshing(false)
  }

  async function removeProduct(product: QcProductListItem) {
    setDeletingId(product.id)
    try {
      await deleteQcProduct(product.id)
      // 本地过滤即可：剩余行按 key 重排，自动向上补位，无需整页重渲染
      setProducts((prev) => prev.filter((entry) => entry.id !== product.id))
      if (standardProduct?.id === product.id) setStandardProduct(null)

      // 右栏是 SSR 一次性数据，必须重取，否则已删品种的批次还挂在那里。
      // 重取失败不回滚删除结果，只保留旧列表并记录日志。
      await fetchQcAttentionBatchesClient(20)
        .then(setAttention)
        .catch((err: unknown) => console.error('刷新需关注批次失败', err))
    } catch (err: unknown) {
      console.error('删除品种失败', err)
      window.alert(err instanceof Error ? err.message : '删除失败')
    } finally {
      setDeletingId(null)
    }
  }

  const totalBatches = products.reduce((sum, product) => sum + product.batch_count, 0)
  const hasFilter = Boolean(keyword || category || level)

  return (
    <div className="p-6">
      {/* 固定撑满一屏：页头与筛选栏不滚，只有下面两栏各自滚 */}
      <section className="qc-panel qc-enter flex h-full min-h-0 flex-col overflow-hidden">
        <div className="qc-panel-head">
          <div>
            <h1 className="qc-title">品种台账</h1>
            <div className="qc-sub">
              共{' '}
              <b className="qc-num" style={{ color: 'var(--brand)' }}>
                {products.length}
              </b>{' '}
              个在库品种 · <span className="qc-num">{totalBatches}</span> 批检验数据 · 点击品种行查看检验数据报表
            </div>
          </div>
          <button type="button" className="qc-btn qc-btn-primary" onClick={() => setDrawerOpen(true)}>
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M8 3v10M3 8h10" strokeLinecap="round" />
            </svg>
            新增品种
          </button>
        </div>

        <div className="qc-filter-row">
          <div className="qc-fi" style={{ width: 240 }}>
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0 text-[var(--ink-3)]" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="7" cy="7" r="4.2" />
              <path d="M10.2 10.2 13.5 13.5" strokeLinecap="round" />
            </svg>
            <input
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="搜索品种名称 / 缩写 / 质量标准"
              className="w-full"
            />
          </div>

          {/* 分类用分段胶囊，不用下拉：只有两个分类，下拉的「全部物料分类」占位既多余又难看 */}
          <div className="qc-seg">
            <button
              type="button"
              onClick={() => setCategory('')}
              className={category === '' ? 'on' : ''}
            >
              全部
            </button>
            {QC_CATEGORY_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setCategory(option.value)}
                className={category === option.value ? 'on' : ''}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="qc-fi">
            <select value={level} onChange={(event) => setLevel(event.target.value as QcLevel | '')}>
              <option value="">全部风险等级</option>
              {QC_LEVEL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {hasFilter && (
            <button
              type="button"
              onClick={() => {
                setKeyword('')
                setCategory('')
                setLevel('')
              }}
              className="qc-btn qc-btn-sm"
            >
              重置
            </button>
          )}

          <span className="qc-num ml-auto text-[12px] font-semibold text-[var(--ink-3)]">
            {refreshing ? '刷新中…' : `显示 ${filtered.length} / ${products.length}`}
          </span>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-y-auto p-4 min-[1100px]:grid-cols-[minmax(0,1fr)_336px] min-[1100px]:overflow-hidden">
          <div className="qc-list-scroll min-w-0">
            {loadFailed && (
              <p className="mb-3 rounded-lg border border-[#FBF6DE] bg-[#FBF6DE] px-4 py-2 text-[12px] text-[#9A7B0A]">
                数据加载不完整，请刷新页面重试
              </p>
            )}

            {filtered.length === 0 ? (
              <div className="rounded-xl border border-[var(--hairline)] bg-white px-6 py-16 text-center">
                <p className="text-[13px] text-[var(--ink-2)]">
                  {products.length === 0 ? '还没有品种' : '没有匹配的品种'}
                </p>
                <p className="mt-1 text-[12px] text-[var(--ink-3)]">
                  {products.length === 0
                    ? '点右上角「新增品种」，上传标准表与检验结果表即可建档'
                    : '换个关键词或清除筛选条件'}
                </p>
              </div>
            ) : (
              <ul className="flex flex-col gap-2.5">
                {filtered.map((product, index) => (
                  <li key={product.id} className="group relative">
                    <Link
                      href={`/quality/inspection/${product.id}`}
                      className="qc-prow"
                      style={{ animationDelay: `${Math.min(index * 50, 400)}ms` }}
                    >
                      <span className="qc-picon">{product.abbr.slice(0, 4)}</span>

                      <span className="min-w-0 flex-1">
                        <span className="qc-pname block truncate">{product.name}</span>
                        <span className="qc-pcode block truncate">
                          {product.quality_standard || '未填写质量标准'} ·{' '}
                          {QC_CATEGORY_LABEL[product.category] ?? product.category}
                        </span>
                      </span>

                      <span className="qc-pstat shrink-0 text-right">
                        <span className="v qc-num">
                          {product.batch_count}
                          <small> 批</small>
                        </span>
                        <span className="k block">在库批次</span>
                      </span>

                      <DistributionBar product={product} />

                      <span className="shrink-0">
                        <QcLevelPill level={product.top_level} showNeutral={product.batch_count > 0} />
                      </span>

                      {/* 给右侧操作区留位，避免内容与按钮重叠 */}
                      <span className="w-[172px] shrink-0" aria-hidden />
                    </Link>

                    {/*
                      操作区是 Link 的兄弟节点：<a> 里不能放 <button>，
                      也不能靠绝对定位硬挤，否则会和行内胶囊重叠。
                    */}
                    {/* 卡片悬停会上浮 2px，操作区跟着上移，避免视觉错位 */}
                    <div className="pointer-events-none absolute right-4 top-1/2 z-[1] flex -translate-y-1/2 items-center gap-2 transition-transform duration-150 group-hover:-translate-y-[calc(50%+2px)]">
                      {/* 同规格 ghost chip，规格写在 qc-theme.css 的 .qc-chip 里，
                          两个只差配色，尺寸/圆角/内距/过渡完全共用 */}
                      <button
                        type="button"
                        onClick={() => setStandardProduct(product)}
                        className="qc-chip qc-chip-standard pointer-events-auto"
                        title="查看并修改三级标准"
                      >
                        标准
                      </button>

                      <Link
                        href={`/quality/inspection/${product.id}`}
                        className="qc-chip qc-chip-report pointer-events-auto"
                      >
                        {product.batch_count === 0 ? '去录入首批 →' : '报表'}
                      </Link>

                      <Link href={`/quality/inspection/${product.id}`} aria-label="进入报表">
                        <svg
                          viewBox="0 0 16 16"
                          className="pointer-events-auto h-4 w-4 text-[#C4C9D4] transition-all duration-150 group-hover:translate-x-1 group-hover:text-[var(--brand)]"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        >
                          <path d="M6 3.5 10.5 8 6 12.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </Link>

                      {/* 删除是低频危险操作，用图标不占宽度；悬停变红，点击二次确认 */}
                      <button
                        type="button"
                        onClick={() => {
                          if (
                            window.confirm(
                              `确定删除「${product.name}」？\n该品种下的 ${product.batch_count} 批检验数据会一并删除，不可恢复。`,
                            )
                          ) {
                            void removeProduct(product)
                          }
                        }}
                        disabled={deletingId === product.id}
                        className="pointer-events-auto ml-0.5 inline-flex h-[26px] w-[26px] items-center justify-center rounded-full text-[#D8DCE5] transition-colors duration-[140ms] hover:bg-[#FDF2F1] hover:text-[#D64545] disabled:cursor-not-allowed disabled:opacity-50"
                        title="删除品种"
                        aria-label={`删除 ${product.name}`}
                      >
                        <svg
                          viewBox="0 0 20 20"
                          className="h-[15px] w-[15px]"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.4"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M4.2 6h11.6M8 6V4.4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1V6" />
                          <path d="M5.6 6l.55 8.9a1.2 1.2 0 0 0 1.2 1.1h5.3a1.2 1.2 0 0 0 1.2-1.1L14.4 6" />
                          <path d="M8.4 8.8v4.4M11.6 8.8v4.4" />
                        </svg>
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <AttentionBatchPanel batches={attention} />
        </div>
      </section>

      <CreateProductDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onCreated={refresh}
      />

      <QcStandardDrawer
        open={Boolean(standardProduct)}
        productId={standardProduct?.id ?? ''}
        productName={standardProduct?.name ?? ''}
        onClose={() => setStandardProduct(null)}
        onRejudged={refresh}
      />
    </div>
  )
}
