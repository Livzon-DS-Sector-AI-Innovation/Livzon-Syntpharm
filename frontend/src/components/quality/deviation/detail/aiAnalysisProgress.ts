/**
 * 偏差 AI 分析的「过程展示」纯逻辑：阶段文案、时间到百分比的进度曲线。
 *
 * 后端 AI 分析是异步任务（`quality.deviation-ai-analysis`），只有 running/done/failed
 * 三态，没有真实进度，因此进度条按「已耗时」映射：分段线性推进、封顶 90%，
 * 任务返回后由调用方显式置 100%，避免进度条自己跑到 100% 却仍在等待。
 *
 * 本文件不含 React 与副作用，便于单测与复用。
 */

/** 分析未结束时进度上限：诚实表达「还没完成」 */
export const ANALYSIS_PROGRESS_CAP = 90

/** 过程区心跳间隔（毫秒）：兼顾秒数刷新与重渲染成本 */
export const ANALYSIS_TICK_INTERVAL_MS = 400

/** 「完成」定格时长：让用户看清 100% 再切到结果，避免结果一闪而出 */
export const ANALYSIS_FINISH_HOLD_MS = 600

export interface AnalysisStage {
  /** 阶段文案 */
  label: string
  /** 当前阶段的补充说明（只在当前阶段显示） */
  hint: string
  /** 进入该阶段的最小进度百分比，需单调不减 */
  from: number
}

/** 四个阶段与时间锚点对齐（约 0s / 6s / 22s / 38s 进入） */
export const ANALYSIS_STAGES: readonly AnalysisStage[] = [
  { label: '正在读取偏差信息', hint: '产品、批次、发生环节与上报描述', from: 0 },
  { label: 'AI 正在分析可能原因', hint: '结合偏差描述与历史同类问题', from: 18 },
  { label: '正在评估质量风险', hint: '影响范围、批次放行与合规风险', from: 45 },
  { label: '正在生成 CAPA 建议', hint: '纠正措施与预防措施的文本建议', from: 70 },
]

/** 进度锚点：`[已耗时 ms, 百分比]`，必须按耗时递增且百分比单调不减 */
const PROGRESS_ANCHORS: readonly (readonly [number, number])[] = [
  [0, 4],
  [5_000, 16],
  [12_000, 32],
  [22_000, 50],
  [35_000, 66],
  [50_000, 80],
  [70_000, 88],
  [180_000, ANALYSIS_PROGRESS_CAP],
]

/**
 * 已耗时 → 进度百分比（0~90）。
 *
 * 前 5 秒涨得快（提交与读取信息阶段用户需要即时反馈），随后放缓，
 * 180 秒后停在 90%：既不虚报完成，也不会长时间一动不动。
 */
export function progressFromElapsed(elapsedMs: number): number {
  if (!Number.isFinite(elapsedMs) || elapsedMs <= 0) return PROGRESS_ANCHORS[0][1]

  for (let index = 1; index < PROGRESS_ANCHORS.length; index += 1) {
    const [prevMs, prevPercent] = PROGRESS_ANCHORS[index - 1]
    const [nextMs, nextPercent] = PROGRESS_ANCHORS[index]
    if (elapsedMs <= nextMs) {
      const ratio = (elapsedMs - prevMs) / (nextMs - prevMs)
      const percent = prevPercent + ratio * (nextPercent - prevPercent)
      return Math.min(ANALYSIS_PROGRESS_CAP, Math.round(percent))
    }
  }
  return ANALYSIS_PROGRESS_CAP
}

/**
 * 进度百分比 → 当前阶段下标。
 *
 * 阶段与进度由同一百分比派生，保证「进度 70% 却停在第 1 步」这类不一致不会出现。
 */
export function stageIndexFromPercent(percent: number): number {
  let index = 0
  for (let cursor = 0; cursor < ANALYSIS_STAGES.length; cursor += 1) {
    if (ANALYSIS_STAGES[cursor].from <= percent) index = cursor
  }
  return index
}

/** 已耗时 → 展示用秒数（不小于 0，整数） */
export function elapsedSeconds(elapsedMs: number): number {
  if (!Number.isFinite(elapsedMs) || elapsedMs <= 0) return 0
  return Math.floor(elapsedMs / 1000)
}