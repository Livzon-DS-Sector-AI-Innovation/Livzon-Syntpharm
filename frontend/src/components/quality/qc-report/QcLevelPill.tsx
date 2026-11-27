import type { QcLevel } from '@/types/qc-report'
import { QC_LEVEL_LABEL, QC_LEVEL_STYLE } from '@/types/qc-report'

interface Props {
  level: QcLevel
  /** 正常/仅记录时是否也显示胶囊（列表里默认不显示，避免视觉噪音） */
  showNeutral?: boolean
  size?: 'sm' | 'md'
}

/** 判定胶囊：6×6 指示方块 + 文字，颜色全部取自 QC_LEVEL_STYLE。 */
export function QcLevelPill({ level, showNeutral = false, size = 'sm' }: Props) {
  if (!showNeutral && (level === 'normal' || level === 'skip')) {
    return <span className="text-[12px] text-[var(--ink-3)]">—</span>
  }

  const style = QC_LEVEL_STYLE[level]
  const padding = size === 'sm' ? 'px-2.5 py-1 text-[11px]' : 'px-3 py-1.5 text-[12px]'

  return (
    <span
      className={`qc-pill ${padding}`}
      style={{ color: style.text, backgroundColor: style.bg, borderColor: style.border }}
    >
      <span className="sq" style={{ backgroundColor: style.dot }} />
      {QC_LEVEL_LABEL[level]}
    </span>
  )
}
