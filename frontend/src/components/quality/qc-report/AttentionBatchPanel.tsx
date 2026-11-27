'use client'

import Link from 'next/link'
import type { QcAttentionBatch } from '@/types/qc-report'
import { QC_LEVEL_LABEL, QC_LEVEL_STYLE } from '@/types/qc-report'

interface Props {
  batches: QcAttentionBatch[]
}

export function AttentionBatchPanel({ batches }: Props) {
  return (
    <aside className="qc-rail-card">
      <div className="qc-panel-head" style={{ padding: '15px 18px 13px' }}>
        <div>
          <h2 className="text-[14px] font-extrabold tracking-[-0.01em] text-[var(--ink)]">需关注批次</h2>
          <div className="qc-sub">全品种 · 按风险层级排序</div>
        </div>
        <span className="qc-pill" style={{ color: 'var(--red)', backgroundColor: 'var(--red-bg)', borderColor: 'var(--red-border)' }}>
          <span className="sq" style={{ backgroundColor: 'var(--red)' }} />
          <span className="qc-num">{batches.length}</span> 批次
        </span>
      </div>

      {batches.length === 0 ? (
        <div className="px-4 py-10 text-center">
          <p className="text-[12.5px] text-[var(--ink-2)]">当前没有异常批次</p>
          <p className="mt-1 text-[12px] text-[var(--ink-3)]">所有入库批次都在三层限值内</p>
        </div>
      ) : (
        <ul className="qc-abn-list">
          {batches.map((batch, index) => {
            const style = QC_LEVEL_STYLE[batch.level]
            return (
              <li key={batch.batch_id}>
                <Link
                  href={`/quality/inspection/${batch.product_id}?highlight=${batch.batch_no}`}
                  className="qc-abn-item group"
                  style={{ animationDelay: `${Math.min(index * 40, 320)}ms` }}
                >
                  <span
                    className="h-[9px] w-[9px] shrink-0 rounded-[2px]"
                    style={{ backgroundColor: style.dot }}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1">
                    <span className="qc-num block truncate text-[12.5px] font-bold text-[var(--ink)]">
                      {batch.batch_no}
                    </span>
                    <span className="mt-0.5 block truncate text-[11px] text-[var(--ink-3)]">
                      {batch.product_name}
                      {batch.reason ? ` · ${batch.reason}` : ''}
                    </span>
                  </span>
                  <span
                    className="qc-pill shrink-0"
                    style={{ color: style.text, backgroundColor: style.bg, borderColor: style.border }}
                  >
                    <span className="sq" style={{ backgroundColor: style.dot }} />
                    {QC_LEVEL_LABEL[batch.level]}
                  </span>
                  <svg
                    viewBox="0 0 16 16"
                    className="h-3 w-3 shrink-0 text-[#C4C9D4] transition-all duration-150 group-hover:translate-x-1 group-hover:text-[var(--brand)]"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  >
                    <path d="M6 3.5 10.5 8 6 12.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </aside>
  )
}
