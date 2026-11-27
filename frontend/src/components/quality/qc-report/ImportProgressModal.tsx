'use client'

import { useEffect, useRef } from 'react'
import type { QcImportCommitResult } from '@/types/qc-report'

export type ImportStage = 'uploading' | 'parsing' | 'writing' | 'done' | 'error'

interface Props {
  open: boolean
  stage: ImportStage
  /** 真实进度 0–100：上传阶段来自字节数，之后来自服务端处理量 */
  percent: number
  /** 服务端给的进度描述，如「已写入 8000 / 46740 条检验值」 */
  message?: string
  result: QcImportCommitResult | null
  error: string | null
  autoCloseMs?: number
  onClose: () => void
  onAutoClose: () => void
}

const STEPS = ['上传文件', '解析入库', '完成']

const STEP_INDEX: Record<ImportStage, number> = {
  uploading: 0,
  parsing: 1,
  writing: 1,
  done: 2,
  error: -1,
}

function StepIndicator({ stage }: { stage: ImportStage }) {
  const current = STEP_INDEX[stage]
  return (
    <ol className="flex items-center gap-2">
      {STEPS.map((label, index) => {
        const finished = current > index || stage === 'done'
        const active = current === index && stage !== 'done'
        return (
          <li key={label} className="flex flex-1 items-center gap-2 last:flex-none">
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium transition-colors ${
                finished
                  ? 'border-[#4F46C9] bg-[#4F46C9] text-white'
                  : active
                    ? 'border-[#4F46C9] bg-white text-[#4F46C9]'
                    : 'border-[#E9EAF2] bg-white text-[#9CA3AF]'
              }`}
            >
              {finished ? (
                <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M3.5 8.5 6.5 11.5 12.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                index + 1
              )}
            </span>
            <span
              className={`whitespace-nowrap text-[12px] ${
                finished || active ? 'text-[#1F2937]' : 'text-[#9CA3AF]'
              }`}
            >
              {label}
            </span>
            {index < STEPS.length - 1 && (
              <span className={`h-px flex-1 ${finished ? 'bg-[#4F46C9]' : 'bg-[#E9EAF2]'}`} aria-hidden />
            )}
          </li>
        )
      })}
    </ol>
  )
}

export function ImportProgressModal({
  open,
  stage,
  percent,
  message,
  result,
  error,
  autoCloseMs = 2000,
  onClose,
  onAutoClose,
}: Props) {
  const autoCloseRef = useRef(onAutoClose)
  useEffect(() => {
    autoCloseRef.current = onAutoClose
  }, [onAutoClose])

  useEffect(() => {
    if (!open || stage !== 'done') return
    const timer = setTimeout(() => autoCloseRef.current(), autoCloseMs)
    return () => clearTimeout(timer)
  }, [open, stage, autoCloseMs])

  if (!open) return null

  const succeeded = stage === 'done'
  const failed = stage === 'error'
  const barColor = succeeded ? '#1aae39' : failed ? '#e03131' : '#4F46C9'
  const barWidth = succeeded || failed ? 100 : Math.max(0, Math.min(99, percent))
  const running = !succeeded && !failed

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[#1F2937]/30" aria-hidden />

      <section
        role="dialog"
        aria-live="polite"
        aria-label={succeeded ? '导入完成' : failed ? '导入失败' : '正在导入'}
        className="relative w-full max-w-[420px] rounded-xl bg-white px-5 py-5 shadow-[0_16px_40px_rgba(26,26,26,0.18)]"
      >
        {!failed && (
          <div className="mb-4">
            <StepIndicator stage={stage} />
          </div>
        )}

        {succeeded ? (
          <>
            <div className="flex items-center gap-2.5">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#d9f3e1]">
                <svg viewBox="0 0 16 16" className="h-4 w-4 text-[#1aae39]" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3.5 8.5 6.5 11.5 12.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <h2 className="text-[16px] font-semibold text-[#1F2937]">导入完成</h2>
            </div>
            {result && (
              <>
                <p className="mt-2 text-[13px] text-[#6B7280]">{result.product_name}</p>
                <dl className="mt-2 grid grid-cols-3 gap-1.5 text-center">
                  <div className="rounded-md bg-[#fafaf9] py-2">
                    <dt className="text-[11px] text-[#9CA3AF]">检验项目</dt>
                    <dd className="text-[18px] font-semibold tabular-nums text-[#1F2937]">{result.item_count}</dd>
                  </div>
                  <div className="rounded-md bg-[#fafaf9] py-2">
                    <dt className="text-[11px] text-[#9CA3AF]">批次</dt>
                    <dd className="text-[18px] font-semibold tabular-nums text-[#1F2937]">{result.batch_count}</dd>
                  </div>
                  <div className="rounded-md bg-[#fafaf9] py-2">
                    <dt className="text-[11px] text-[#9CA3AF]">检验值</dt>
                    <dd className="text-[18px] font-semibold tabular-nums text-[#1F2937]">{result.value_count}</dd>
                  </div>
                </dl>

                {result.standard_sources.length > 0 && (
                  <details className="mt-3 rounded-lg border border-[#E9EAF2] bg-white px-3 py-2">
                    <summary className="cursor-pointer text-[12px] font-medium text-[#6B7280]">
                      标准来源明细 {result.standard_sources.length} 处
                    </summary>
                    <ul className="mt-1.5 max-h-[180px] space-y-1 overflow-y-auto">
                      {result.standard_sources.map((item) => (
                        <li
                          key={`${item.column_letter}-${item.layer}`}
                          className="flex items-center gap-1.5 text-[12px]"
                        >
                          <span className="w-[22px] shrink-0 rounded bg-[#F4F5FA] text-center font-mono text-[11px] text-[#6B7280]">
                            {item.column_letter}
                          </span>
                          <span className="min-w-0 flex-1 truncate text-[#6B7280]" title={item.item_name}>
                            {item.item_name.replace(/\n/g, '')}·{item.layer_label}
                          </span>
                          <span className="max-w-[92px] shrink-0 truncate text-[#1F2937]" title={item.final_text ?? ''}>
                            {item.final_text ?? '—'}
                          </span>
                          <span
                            className={`shrink-0 rounded-full px-1.5 py-[1px] text-[11px] ${
                              item.from_choice
                                ? 'bg-[#F0EFFC] text-[#3E38A3]'
                                : 'bg-[#F4F5FA] text-[#6B7280]'
                            }`}
                          >
                            {item.source === 'docx' ? '标准表' : item.source === 'none' ? '留空' : '结果表'}
                            {item.from_choice ? ' · 人工选择' : ' · 默认'}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </>
            )}
            <p className="mt-2 text-[11px] text-[#9CA3AF]">{autoCloseMs / 1000} 秒后自动关闭</p>
          </>
        ) : failed ? (
          <>
            <div className="flex items-center gap-2.5">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#fde0ec]">
                <svg viewBox="0 0 16 16" className="h-4 w-4 text-[#e03131]" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 5l6 6M11 5l-6 6" strokeLinecap="round" />
                </svg>
              </span>
              <h2 className="text-[16px] font-semibold text-[#1F2937]">导入失败</h2>
            </div>
            <p className="mt-2 break-all text-[13px] text-[#9c0006]">{error ?? '未知错误'}</p>
            <p className="mt-1 text-[12px] text-[#6B7280]">返回后表单内容不会清空，可以直接改完重试。</p>
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="h-8 rounded-md bg-[#4F46C9] px-3.5 text-[13px] font-medium text-white transition-colors hover:bg-[#3E38A3]"
              >
                返回修改
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-baseline justify-between">
              <h2 className="text-[16px] font-semibold text-[#1F2937]">
                {stage === 'uploading' ? '正在上传文件' : '正在写入数据'}
              </h2>
              <span className="text-[13px] tabular-nums text-[#4F46C9]">{Math.round(barWidth)}%</span>
            </div>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#F1F2F7]">
              <div
                className="h-full rounded-full transition-[width] duration-200 ease-linear"
                style={{ width: `${barWidth}%`, backgroundColor: barColor }}
              />
            </div>
            <p className="mt-2 text-[12px] text-[#6B7280]">
              {message ?? (stage === 'uploading' ? '文件较大时需要几秒，请不要关闭页面' : '正在处理数据…')}
            </p>
            {running && stage === 'parsing' && !message && (
              <p className="mt-0.5 text-[11px] text-[#9CA3AF]">解析完成后会显示写入条数</p>
            )}
          </>
        )}
      </section>
    </div>
  )
}
