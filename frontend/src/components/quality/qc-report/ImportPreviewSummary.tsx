'use client'

import type { QcImportPreview, QcStandardConflict } from '@/types/qc-report'

interface Props {
  preview: QcImportPreview
  /** 键为 `列号|层`，值为 docx / excel / none */
  choices: Record<string, string>
  onChoose: (key: string, value: string) => void
  /** 键为标准表项目名，值为结果表列字母 */
  mapping: Record<string, string>
  onMappingChange: (itemName: string, columnLetter: string) => void
  rematching?: boolean
}

const OPTIONS: { value: string; label: string }[] = [
  { value: 'docx', label: '用标准表' },
  { value: 'excel', label: '用结果表' },
  { value: 'none', label: '这层留空' },
]

function conflictKey(conflict: QcStandardConflict): string {
  return `${conflict.column_index}|${conflict.layer}`
}

interface ConflictCardProps {
  conflict: QcStandardConflict
  choices: Record<string, string>
  onChoose: (key: string, value: string) => void
}

function ConflictCard({ conflict, choices, onChoose }: ConflictCardProps) {
  const key = conflictKey(conflict)
  const picked = choices[key]
  return (
    <li className="rounded-md border border-[#F1F2F7] bg-white px-2.5 py-2">
      <p className="flex items-center gap-1.5 text-[12px]">
        <span className="rounded bg-[#F1F2F7] px-1 font-mono text-[11px] text-[#6B7280]">
          {conflict.column_letter}
        </span>
        <span className="font-medium text-[#1F2937]">{conflict.item_name.replace(/\n/g, '')}</span>
        <span className="text-[#9CA3AF]">·</span>
        <span className="text-[#6B7280]">{conflict.layer_label}</span>
      </p>
      <dl className="mt-1 grid grid-cols-2 gap-1.5 text-[12px]">
        <div className="rounded bg-[#fafaf9] px-2 py-1">
          <dt className="text-[11px] text-[#9CA3AF]">标准表</dt>
          <dd className="break-all text-[#1F2937]">{conflict.docx_text ?? '未写'}</dd>
        </div>
        <div className="rounded bg-[#fafaf9] px-2 py-1">
          <dt className="text-[11px] text-[#9CA3AF]">结果表</dt>
          <dd className="break-all text-[#1F2937]">{conflict.excel_text ?? '未写'}</dd>
        </div>
      </dl>
      {conflict.note && <p className="mt-1 text-[11px] text-[#9a7b0a]">{conflict.note}</p>}
      <div className="mt-1.5 flex gap-1.5">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChoose(key, option.value)}
            className={`rounded border px-2 py-0.5 text-[12px] transition-colors ${
              picked === option.value
                ? 'border-[#4F46C9] bg-[#F0EFFC] font-medium text-[#3E38A3]'
                : 'border-[#E9EAF2] text-[#6B7280] hover:border-[#c8c4be] hover:bg-[#f6f5f4]'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </li>
  )
}

export function ImportPreviewSummary({
  preview,
  choices,
  onChoose,
  mapping,
  onMappingChange,
  rematching = false,
}: Props) {
  const summary = preview.summary
  const unmatched = preview.unmatched_items
  const numericConflicts = preview.conflicts.filter((item) => item.severity === 'numeric')
  const textConflicts = preview.conflicts.filter((item) => item.severity !== 'numeric')
  const pendingNumeric = numericConflicts.filter((item) => !choices[conflictKey(item)])

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-[#E9EAF2] bg-[#fafaf9] px-3 py-2.5">
        <p className="text-[13px] text-[#1F2937]">
          共 <span className="font-semibold tabular-nums">{summary?.total_columns ?? preview.items.length}</span> 列 ·
          一致 <span className="font-semibold tabular-nums">{summary?.same_count ?? 0}</span> ·
          待确认 <span className="font-semibold tabular-nums">{summary?.conflict_count ?? 0}</span> ·
          仅结果表有 <span className="font-semibold tabular-nums">{summary?.only_excel_count ?? 0}</span> ·
          <span className="font-semibold tabular-nums"> {preview.batch_count}</span> 批数据
        </p>
        <p className="mt-1 text-[12px] text-[#6B7280]">
          工作表 {preview.sheet_title} · 首条批号{' '}
          <span className="font-mono">{preview.batch_no_samples[0] ?? '—'}</span>
        </p>
      </div>

      {unmatched.length > 0 && (
        <section className="rounded-lg border border-[#E9EAF2] bg-white px-3 py-2.5">
          <h4 className="flex items-center gap-2 text-[13px] font-medium text-[#1F2937]">
            需指定对应列 {unmatched.length} 项
            {rematching && <span className="text-[11px] font-normal text-[#9CA3AF]">重新核对中…</span>}
          </h4>
          <p className="mt-0.5 text-[12px] text-[#6B7280]">
            指定该列与标准表项目的对应关系；未指定时标准取自结果表。
          </p>
          <ul className="mt-2 space-y-1.5">
            {unmatched.map((item) => {
              const current = mapping[item.item_name] ?? item.matched_column_letter ?? ''
              return (
                <li key={item.item_name} className="flex items-center gap-2">
                  <span
                    className="w-[168px] shrink-0 truncate text-[12px] text-[#1F2937]"
                    title={`${item.item_name}\n标准表：${item.docx_legal_text ?? '—'}`}
                  >
                    {item.item_name.replace(/\n/g, '')}
                  </span>
                  <span className="shrink-0 text-[#c8c4be]">→</span>
                  <select
                    value={current}
                    onChange={(event) => onMappingChange(item.item_name, event.target.value)}
                    className="h-7 min-w-0 flex-1 rounded-md border border-[#E9EAF2] bg-white px-1.5 text-[12px] text-[#1F2937] outline-none transition-colors focus:border-[#4F46C9]"
                  >
                    <option value="">请选择对应列…</option>
                    {item.candidates.map((candidate) => (
                      <option key={candidate.letter} value={candidate.letter}>
                        {candidate.letter} · {candidate.name.replace(/\n/g, '')}
                      </option>
                    ))}
                  </select>
                  <span
                    className={`w-[42px] shrink-0 text-[11px] ${
                      current ? 'text-[#1aae39]' : 'text-[#9CA3AF]'
                    }`}
                  >
                    {current ? '已对应' : '未对应'}
                  </span>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {numericConflicts.length > 0 && (
        <section className="rounded-lg border border-[#ffe8d4] bg-[#fffdf9] px-3 py-2.5">
          <h4 className="flex items-center gap-2 text-[13px] font-medium text-[#dd5b00]">
            数值不一致 {numericConflicts.length} 处
            {pendingNumeric.length > 0 && (
              <span className="text-[11px] font-normal">未确认 {pendingNumeric.length}</span>
            )}
          </h4>
          <p className="mt-0.5 text-[12px] text-[#6B7280]">
            限值数字不同，判定结果会不一致，需确认采用哪一份。
          </p>
          <ul className="mt-2 space-y-2">
            {numericConflicts.map((conflict) => (
              <ConflictCard key={conflictKey(conflict)} conflict={conflict} choices={choices} onChoose={onChoose} />
            ))}
          </ul>
        </section>
      )}

      {textConflicts.length > 0 && (
        <details className="rounded-lg border border-[#E9EAF2] bg-white px-3 py-2.5">
          <summary className="cursor-pointer text-[13px] font-medium text-[#6B7280]">
            文字表述不同 {textConflicts.length} 处
          </summary>
          <p className="mt-1 text-[12px] text-[#9CA3AF]">
            两份文件写法不同，不影响判定结果；未选择时采用结果表的值。
          </p>
          <ul className="mt-2 space-y-2">
            {textConflicts.map((conflict) => (
              <ConflictCard key={conflictKey(conflict)} conflict={conflict} choices={choices} onChoose={onChoose} />
            ))}
          </ul>
        </details>
      )}

      {(summary?.skipped_standard_items.length ?? 0) > 0 && (
        <p className="rounded-lg border border-[#fef7d6] bg-[#fef7d6] px-3 py-2 text-[12px] text-[#9a7b0a]">
          标准表里有 {summary?.skipped_standard_items.length} 项在结果表中确实没有对应列，已跳过：
          {summary?.skipped_standard_items.join('、')}
        </p>
      )}

      {preview.unrecognized_items.length > 0 && (
        <p className="rounded-lg border border-[#fef7d6] bg-[#fef7d6] px-3 py-2 text-[12px] text-[#9a7b0a]">
          有 {preview.unrecognized_items.length} 个项目的标准无法自动识别，导入后请在项目设置里补一次：
          {preview.unrecognized_items.join('、')}
        </p>
      )}

      <details className="rounded-lg border border-[#E9EAF2] bg-white px-3 py-2">
        <summary className="cursor-pointer text-[12px] text-[#6B7280]">
          各列三层标准（{preview.items.length} 项）
        </summary>
        <ul className="mt-1.5 max-h-56 space-y-1 overflow-y-auto pr-1">
          {preview.items.map((item) => (
            <li key={item.item_no} className="flex gap-2 text-[12px]">
              <span className="w-[130px] shrink-0 truncate text-[#1F2937]" title={item.item_name}>
                {item.item_name.replace(/\n/g, '')}
              </span>
              <span className="shrink-0 text-[#9CA3AF]">
                {item.match_kind === 'pending'
                  ? '未对应'
                  : item.match_kind === 'diff'
                    ? '待确认'
                    : item.match_kind === 'only_excel'
                      ? '仅结果表'
                      : '一致'}
              </span>
              <span className="truncate text-[#6B7280]" title={item.legal_text ?? ''}>
                法定 {item.legal_text ?? '—'}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </div>
  )
}
