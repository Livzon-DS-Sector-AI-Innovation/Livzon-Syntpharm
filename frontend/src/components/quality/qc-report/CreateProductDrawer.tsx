'use client'

import { useRef, useState } from 'react'
import { commitQcImportWithProgress, previewQcImport } from '@/lib/api/client/qc-report'
import { ImportPreviewSummary } from './ImportPreviewSummary'
import { ImportProgressModal } from './ImportProgressModal'
import type { ImportStage } from './ImportProgressModal'
import { QC_CATEGORY_OPTIONS } from '@/types/qc-report'
import type { QcCategory, QcImportCommitResult, QcImportPreview } from '@/types/qc-report'

interface Props {
  open: boolean
  onClose: () => void
  onCreated: () => void
}

type Phase = 'idle' | 'parsing' | 'ready' | 'committing'

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function UploadBox({
  label,
  hint,
  accept,
  file,
  onPick,
}: {
  label: string
  hint: string
  accept: string
  file: File | null
  onPick: (file: File) => void
}) {
  const [dragging, setDragging] = useState(false)
  const extension = file ? (file.name.split('.').pop() ?? '').toUpperCase().slice(0, 4) : ''

  return (
    <div>
      <p className="mb-1.5 text-[12px] font-medium text-[#1F2937]">{label}</p>
      <label
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          const dropped = event.dataTransfer.files?.[0]
          if (dropped) onPick(dropped)
        }}
        className={`flex h-[124px] cursor-pointer flex-col justify-center rounded-xl border border-dashed px-4 transition-colors ${
          dragging
            ? 'border-[#4F46C9] bg-[#f6f4fd]'
            : file
              ? 'border-[#E9EAF2] bg-white hover:border-[#c8c4be]'
              : 'border-[#E9EAF2] bg-[#fafaf9] hover:border-[#c8c4be] hover:bg-[#f6f5f4]'
        }`}
      >
        <input
          type="file"
          accept={accept}
          className="sr-only"
          onChange={(event) => {
            const picked = event.target.files?.[0]
            if (picked) onPick(picked)
          }}
        />

        {file ? (
          <>
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#F0EFFC] text-[11px] font-semibold text-[#3E38A3]">
                {extension}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[12px] text-[#1F2937]" title={file.name}>
                  {file.name}
                </span>
                <span className="block text-[11px] text-[#9CA3AF]">{formatSize(file.size)}</span>
              </span>
              <svg
                viewBox="0 0 16 16"
                className="h-4 w-4 shrink-0 text-[#1aae39]"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M3.5 8.5 6.5 11.5 12.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="mt-3 text-[11px] text-[#4F46C9]">重新选择</span>
          </>
        ) : (
          <>
            <span className="mx-auto flex h-9 w-9 items-center justify-center rounded-lg bg-[#F1F2F7]">
              <svg
                viewBox="0 0 16 16"
                className="h-4 w-4 text-[#6B7280]"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.4"
              >
                <path
                  d="M8 2.5v7M5 6l3-3.5L11 6M2.5 11.5v1a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-1"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <span className="mt-2 text-center text-[12px] font-medium text-[#1F2937]">
              点击或拖入文件
            </span>
            <span className="mt-0.5 text-center text-[11px] text-[#9CA3AF]">{hint}</span>
          </>
        )}
      </label>
    </div>
  )
}

export function CreateProductDrawer({ open, onClose, onCreated }: Props) {
  const [name, setName] = useState('')
  const [abbr, setAbbr] = useState('')
  const [category, setCategory] = useState<QcCategory>('finished')
  const [qualityStandard, setQualityStandard] = useState('')
  const [standardFile, setStandardFile] = useState<File | null>(null)
  const [resultFile, setResultFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<QcImportPreview | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  // 冲突裁决：键 `列号|层`，值 docx / excel / none
  const [choices, setChoices] = useState<Record<string, string>>({})
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [rematching, setRematching] = useState(false)
  const [progress, setProgress] = useState<{
    open: boolean
    stage: ImportStage
    percent: number
    message?: string
    result: QcImportCommitResult | null
    error: string | null
  }>({ open: false, stage: 'uploading', percent: 0, result: null, error: null })
  const nameTouched = useRef(false)
  const rematchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  function resetForm() {
    setName('')
    setAbbr('')
    setCategory('finished')
    setQualityStandard('')
    setStandardFile(null)
    setResultFile(null)
    setPreview(null)
    setMapping({})
    setChoices({})
    setPhase('idle')
    setError(null)
    setRematching(false)
    setProgress({ open: false, stage: 'uploading', percent: 0, result: null, error: null })
    if (rematchTimer.current) {
      clearTimeout(rematchTimer.current)
      rematchTimer.current = null
    }
    nameTouched.current = false
  }

  function handleClose() {
    resetForm()
    onClose()
  }

  /** 两个文件都齐了就立刻解析 —— 由选文件的动作触发，不放在 effect 里。 */
  async function runPreview(standard: File | null, result: File | null) {
    if (!standard || !result) return
    setPhase('parsing')
    setError(null)
    try {
      const data = await previewQcImport(standard, result)
      setPreview(data)
      setMapping({})
      setChoices({})
      if (!nameTouched.current && data.product_name_suggestion) {
        setName(data.product_name_suggestion)
      }
      setPhase('ready')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '解析失败')
      setPhase('idle')
    }
  }

  // 只有「数值不一致」必须人工确认；文字表述不同默认取结果表，不阻塞
  const unresolvedConflicts =
    preview?.conflicts.filter(
      (conflict) =>
        conflict.severity === 'numeric' && !choices[`${conflict.column_index}|${conflict.layer}`],
    ) ?? []
  const canCommit = Boolean(
    preview &&
      name.trim() &&
      abbr.trim().length >= 2 &&
      qualityStandard.trim() &&
      phase === 'ready' &&
      unresolvedConflicts.length === 0,
  )

  /** 人工指定对应关系后，重新核对两份文件的标准（300ms 防抖，避免连点发多次请求）。 */
  function handleMappingChange(itemName: string, columnLetter: string) {
    const next = { ...mapping }
    if (columnLetter) next[itemName] = columnLetter
    else delete next[itemName]
    setMapping(next)
    if (!standardFile || !resultFile) return

    if (rematchTimer.current) clearTimeout(rematchTimer.current)
    rematchTimer.current = setTimeout(() => {
      setRematching(true)
      previewQcImport(standardFile, resultFile, undefined, next)
        .then((data) => {
          // 只替换预览数据，绝不清理 choices。
          // 以前这里用新冲突列表过滤旧选择，用户选过的项一旦不在新列表里就被静默删掉，
          // 提交时再被默认值顶上——这就是「选了却没按选择判定」的根源。
          setPreview(data)
        })
        .catch((err: unknown) => {
          setError(err instanceof Error ? err.message : '重新核对失败')
        })
        .finally(() => setRematching(false))
    }, 300)
  }

  async function handleCommit() {
    if (!standardFile || !resultFile || !preview) return
    if (unresolvedConflicts.length > 0) {
      setError(
        `还有 ${unresolvedConflicts.length} 处标准没确认：${unresolvedConflicts
          .slice(0, 4)
          .map((item) => `${item.column_letter}·${item.layer_label}`)
          .join('、')}`,
      )
      return
    }
    setError(null)
    setProgress({ open: true, stage: 'uploading', percent: 0, result: null, error: null })

    // 原样提交用户的选择，不再替用户补默认值。
    // 没选的层由后端按既有规则取结果表，导入完成页会标注「默认」，
    // 用户能自己看出哪一条没生效，而不是被悄悄替换掉。
    const resolutions = { ...choices }

    try {
      const result = await commitQcImportWithProgress(
        {
          standardFile,
          resultFile,
          name: name.trim(),
          abbr: abbr.trim().toUpperCase(),
          category,
          qualityStandard: qualityStandard.trim() || undefined,
          manualMapping: mapping,
          resolutions,
        },
        (event) =>
          setProgress((prev) => ({
            ...prev,
            stage: event.stage,
            percent: event.percent,
            message: event.message,
          })),
      )
      setProgress({ open: true, stage: 'done', percent: 100, result, error: null })
      onCreated()
    } catch (err: unknown) {
      setProgress({
        open: true,
        stage: 'error',
        percent: 100,
        result: null,
        error: err instanceof Error ? err.message : '导入失败',
      })
    }
  }

  if (!open) return null

  // 提交后抽屉让位，只保留进度弹窗；完成自动关闭时再重置并退出
  if (progress.open) {
    return (
      <ImportProgressModal
        open
        stage={progress.stage}
        percent={progress.percent}
        message={progress.message}
        result={progress.result}
        error={progress.error}
        onClose={() => setProgress((prev) => ({ ...prev, open: false }))}
        onAutoClose={() => {
          resetForm()
          onClose()
        }}
      />
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="关闭"
        onClick={handleClose}
        className="absolute inset-0 bg-[#1F2937]/25"
      />
      <section className="relative flex h-full w-full max-w-[880px] flex-col bg-white shadow-[-8px_0_24px_rgba(26,26,26,0.08)]">
        <header className="flex items-start justify-between border-b border-[#E9EAF2] bg-[linear-gradient(135deg,#F8F7FE,#F1EFFD)] px-6 py-5">
          <div>
            <h2 className="flex items-center gap-2.5 text-[17px] font-extrabold tracking-[-0.01em] text-[#1F2937]">
              <span className="inline-block h-4 w-1 rounded-[2px] bg-[linear-gradient(180deg,#4F46C9,#7C72F0)]" />
              新增品种
            </h2>
            <p className="mt-1 text-[12px] text-[#6B7280]">
              填写品种信息并上传标准表与结果表，系统自动解析项目、限值与历史批次
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-md p-1 text-[#9CA3AF] transition-colors hover:bg-[#f6f5f4] hover:text-[#1F2937]"
          >
            <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
            </svg>
          </button>
        </header>

        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
          <>
              <section className="space-y-3">
                <p className="text-[12px] font-medium text-[#6B7280]">① 上传文件</p>
                <div className="grid grid-cols-2 gap-3">
                  <UploadBox
                    label="标准表（.docx）"
                    hint="项目清单与法定/内控/3σ 三层标准"
                    accept=".docx"
                    file={standardFile}
                    onPick={(picked) => {
                      setStandardFile(picked)
                      void runPreview(picked, resultFile)
                    }}
                  />
                  <UploadBox
                    label="检验结果表（.xlsx）"
                    hint="批号与全部历史检验数据"
                    accept=".xlsx"
                    file={resultFile}
                    onPick={(picked) => {
                      setResultFile(picked)
                      void runPreview(standardFile, picked)
                    }}
                  />
                </div>
                {phase === 'parsing' && (
                  <p className="text-[13px] text-[#6B7280]">正在解析两个文件…</p>
                )}
              </section>

              <section className="space-y-3 border-t border-[#F1F2F7] pt-4">
                <p className="text-[12px] font-medium text-[#6B7280]">② 品种信息</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="qc-name" className="mb-1 block text-[12px] font-medium text-[#1F2937]">
                      品种名称
                    </label>
                    <input
                      id="qc-name"
                      value={name}
                      onChange={(event) => {
                        nameTouched.current = true
                        setName(event.target.value)
                      }}
                      placeholder="上传后从文件名带出，可修改"
                      className="h-8 w-full rounded-md border border-[#E9EAF2] px-2.5 text-[13px] text-[#1F2937] outline-none transition-colors placeholder:text-[#bbb8b1] focus:border-[#4F46C9]"
                    />
                  </div>
                  <div>
                    <label htmlFor="qc-abbr" className="mb-1 block text-[12px] font-medium text-[#1F2937]">
                      品名缩写 <span className="text-[#e03131]">*</span>
                    </label>
                    <input
                      id="qc-abbr"
                      value={abbr}
                      onChange={(event) => setAbbr(event.target.value.toUpperCase())}
                      maxLength={16}
                      placeholder="如 QS"
                      className="h-8 w-full rounded-md border border-[#E9EAF2] px-2.5 font-mono text-[13px] uppercase text-[#1F2937] outline-none transition-colors placeholder:font-sans placeholder:normal-case placeholder:text-[#bbb8b1] focus:border-[#4F46C9]"
                    />
                  </div>
                </div>

                <div>
                  <span className="mb-1 block text-[12px] font-medium text-[#1F2937]">物料分类</span>
                  <div className="inline-flex rounded-md border border-[#E9EAF2] p-0.5">
                    {QC_CATEGORY_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setCategory(option.value)}
                        className={`rounded px-3 py-1 text-[12px] transition-colors ${
                          category === option.value
                            ? 'bg-[#F0EFFC] font-medium text-[#3E38A3]'
                            : 'text-[#6B7280] hover:bg-[#f6f5f4]'
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label htmlFor="qc-standard" className="mb-1 block text-[12px] font-medium text-[#1F2937]">
                    质量标准 <span className="text-[#D64545]">*</span>
                  </label>
                  <input
                    id="qc-standard"
                    value={qualityStandard}
                    onChange={(event) => setQualityStandard(event.target.value)}
                    required
                    aria-required
                    placeholder="如 ChP 2025 / QS-C011014-08（手册缩写 ChP / USP / EP / JP）"
                    className="h-8 w-full rounded-md border border-[#E9EAF2] px-2.5 text-[13px] text-[#1F2937] outline-none transition-colors placeholder:text-[#bbb8b1] focus:border-[#4F46C9]"
                  />
                </div>
              </section>

              {preview && (
                <ImportPreviewSummary
                  preview={preview}
                  choices={choices}
                  onChoose={(key, value) => setChoices((prev) => ({ ...prev, [key]: value }))}
                  mapping={mapping}
                  onMappingChange={handleMappingChange}
                  rematching={rematching}
                />
              )}

              {error && (
                <p className="rounded-lg border border-[#fde0ec] bg-[#fde0ec] px-3 py-2 text-[12px] text-[#9c0006]">
                  {error}
                </p>
              )}
          </>
        </div>

        <footer className="flex items-center justify-between border-t border-[#F1F2F7] px-6 py-3">
          <p className="text-[12px] text-[#9CA3AF]">
            {rematching ? '正在按新对应关系重新核对…' : '两个文件都不限制文件名，按后缀自动识别'}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="h-8 rounded-md border border-[#E9EAF2] px-3 text-[13px] text-[#6B7280] transition-colors hover:bg-[#f6f5f4]"
            >
              取消
            </button>
            <button
              type="button"
              disabled={!canCommit || rematching}
              onClick={handleCommit}
              className="h-8 rounded-md bg-[#4F46C9] px-4 text-[13px] font-medium text-white transition-colors hover:bg-[#3E38A3] disabled:cursor-not-allowed disabled:bg-[#c8c4be]"
            >
              确认导入
            </button>
          </div>
        </footer>
      </section>
    </div>
  )
}
