'use client'

import { useRef, useState } from 'react'
import { importQcBatches } from '@/lib/api/client/qc-report'
import type { QcBatchImportResult } from '@/types/qc-report'
import { QC_LEVEL_STYLE } from '@/types/qc-report'

interface Props {
  open: boolean
  productId: string
  onClose: () => void
  onCreated: () => void
}

const LEVEL_LABEL: Record<string, string> = {
  oos: '超法定',
  internal: '超内控',
  trend: '超趋势',
  normal: '正常',
  skip: '仅记录',
  pending: '待检',
}

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function QcBatchEntryModal({ open, productId, onClose, onCreated }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<QcBatchImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  if (!open) return null

  function pick(next: File | null) {
    if (!next) return
    if (!next.name.toLowerCase().endsWith('.xlsx')) {
      setError('请上传 .xlsx 格式的检验结果表')
      return
    }
    setFile(next)
    setError(null)
    setResult(null)
  }

  async function submit() {
    if (!file || busy) return
    setBusy(true)
    setError(null)
    try {
      const data = await importQcBatches(productId, file)
      setResult(data)
      onCreated()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '导入失败')
    } finally {
      setBusy(false)
    }
  }

  function close() {
    setFile(null)
    setResult(null)
    setError(null)
    setDragging(false)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button type="button" aria-label="关闭" onClick={close} className="absolute inset-0 bg-[#1a1a1a]/25" />

      <section className="relative w-full max-w-[560px] overflow-hidden rounded-2xl bg-white shadow-[0_28px_70px_rgba(23,26,40,0.28)]">
        <header className="flex items-start justify-between border-b border-[#E9EAF2] bg-[linear-gradient(135deg,#F8F7FE,#F1EFFD)] px-5 py-4">
          <div>
            <h3 className="flex items-center gap-2.5 text-[16px] font-extrabold tracking-[-0.01em] text-[#1F2937]">
              <span className="inline-block h-4 w-1 rounded-[2px] bg-[linear-gradient(180deg,#4F46C9,#7C72F0)]" />
              新增检验批次
            </h3>
            <p className="mt-1 text-[12px] text-[#6B7280]">
              上传检验结果表，一次写入多批；列按顺序对应该品种的检验项目
            </p>
          </div>
          <button
            type="button"
            onClick={close}
            className="h-8 w-8 rounded-lg border border-[#E9EAF2] bg-white text-[13px] text-[#6B7280] transition-colors hover:border-[#4F46C9] hover:text-[#4F46C9]"
            aria-label="关闭"
          >
            ✕
          </button>
        </header>

        <div className="px-5 py-4">
          {result ? (
            <div className="rounded-xl border border-[#BFE6D2] bg-[#E9F7EF] px-4 py-3.5">
              <p className="flex items-center gap-2 text-[14px] font-semibold text-[#1E8E5A]">
                <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3.5 8.5 6.5 11.5 12.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                新增 {result.created_count} 批检验数据
              </p>

              {result.skipped_count > 0 && (
                <p className="mt-1.5 text-[12px] text-[#6B7280]">
                  跳过 {result.skipped_count} 批（批号已存在：
                  {result.skipped_batch_nos.slice(0, 5).join('、')}
                  {result.skipped_batch_nos.length > 5 ? ' 等' : ''}）
                </p>
              )}

              {Object.keys(result.level_counts).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.entries(result.level_counts).map(([level, count]) => {
                    const tone = QC_LEVEL_STYLE[level as keyof typeof QC_LEVEL_STYLE]
                    return (
                      <span
                        key={level}
                        className="qc-pill"
                        style={{
                          color: tone?.text ?? '#6B7280',
                          backgroundColor: tone?.bg ?? '#F3F4F6',
                          borderColor: tone?.border ?? '#E5E7EB',
                        }}
                      >
                        <span className="sq" style={{ backgroundColor: tone?.dot ?? '#C4C9D1' }} />
                        {LEVEL_LABEL[level] ?? level} <span className="qc-num">{count}</span>
                      </span>
                    )
                  })}
                </div>
              )}
            </div>
          ) : (
            <>
              <label
                onDragOver={(event) => {
                  event.preventDefault()
                  setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(event) => {
                  event.preventDefault()
                  setDragging(false)
                  pick(event.dataTransfer.files?.[0] ?? null)
                }}
                className={`flex h-[132px] cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-4 transition-colors ${
                  dragging
                    ? 'border-[#4F46C9] bg-[#F6F4FD]'
                    : 'border-[#E9EAF2] bg-[#FAFAF9] hover:border-[#C8C4BE] hover:bg-[#F6F5F4]'
                }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx"
                  className="sr-only"
                  onChange={(event) => pick(event.target.files?.[0] ?? null)}
                />
                {file ? (
                  <>
                    <div className="flex w-full items-center gap-2.5">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#F0EFFC] text-[11px] font-semibold text-[#3E38A3]">
                        XLSX
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[12px] text-[#1F2937]" title={file.name}>
                          {file.name}
                        </span>
                        <span className="block text-[11px] text-[#9CA3AF]">{formatSize(file.size)}</span>
                      </span>
                      <svg viewBox="0 0 16 16" className="h-4 w-4 shrink-0 text-[#1E8E5A]" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3.5 8.5 6.5 11.5 12.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <span className="mt-3 text-[11px] text-[#4F46C9]">重新选择</span>
                  </>
                ) : (
                  <>
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#F0EEEC]">
                      <svg viewBox="0 0 16 16" className="h-4 w-4 text-[#5D5B54]" fill="none" stroke="currentColor" strokeWidth="1.4">
                        <path
                          d="M8 2.5v7M5 6l3-3.5L11 6M2.5 11.5v1a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-1"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </span>
                    <span className="mt-2 text-[12px] font-medium text-[#1F2937]">点击或拖入文件</span>
                    <span className="mt-0.5 text-[11px] text-[#9CA3AF]">.xlsx · 格式与初次导入的结果表相同</span>
                  </>
                )}
              </label>

              <p className="mt-2.5 text-[11px] leading-relaxed text-[#9CA3AF]">
                A 列批号，第 7 行起为检验数据；批号重复的批次会自动跳过，列数或表头与系统项目对不上时会拒绝导入。
              </p>

              {error && (
                <p className="mt-3 rounded-lg border border-[#F5CDC8] bg-[#FDECEA] px-3 py-2 text-[12px] text-[#D64545]">
                  {error}
                </p>
              )}
            </>
          )}
        </div>

        <footer className="flex items-center justify-between border-t border-[#E9EAF2] bg-[#FCFCFE] px-5 py-3">
          <p className="text-[11px] text-[#9CA3AF]">
            {result
              ? '统计卡与表格已刷新'
              : file
                ? '将按列顺序写入，批号重复自动跳过'
                : '请选择一个 .xlsx 文件'}
          </p>
          <div className="flex gap-2">
            <button type="button" onClick={close} className="qc-btn qc-btn-sm">
              {result ? '完成' : '取消'}
            </button>
            {!result && (
              <button
                type="button"
                onClick={() => void submit()}
                disabled={!file || busy}
                className="qc-btn qc-btn-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busy ? '正在写入…' : '开始导入'}
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>
  )
}
