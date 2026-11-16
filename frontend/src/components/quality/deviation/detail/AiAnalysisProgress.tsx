'use client'

import { Alert, Button, Progress, Space } from 'antd'
import { CheckCircleFilled, ExclamationCircleFilled } from '@ant-design/icons'
import {
  ANALYSIS_STAGES,
  elapsedSeconds,
  stageIndexFromPercent,
} from './aiAnalysisProgress'

interface AiAnalysisProgressProps {
  /** 当前进度百分比：分析中 0~90，完成定格 100，失败冻结在中断点 */
  percent: number
  /** 已耗时（毫秒），用于「已用 N 秒」 */
  elapsedMs: number
  /** 失败原因；非空即失败态（进度条转红、提供重试/收起） */
  failed: string | null
  onRetry: () => void
  onDismiss: () => void
}

type StageState = 'done' | 'active' | 'error' | 'wait'

/** 图标颜色用内联 style：@ant-design/icons 的 `.anticon { color: inherit }` 会盖掉 Tailwind text-* */
const STAGE_ICON = {
  done: <CheckCircleFilled style={{ color: '#1AAE39' }} />,
  error: <ExclamationCircleFilled style={{ color: '#E03131' }} />,
} as const

/**
 * 偏差 AI 分析的过程区：阶段文案脉冲闪烁 + 进度条 + 已耗时 + 四步清单。
 *
 * 纯展示组件，不含计时器；进度与阶段都由调用方传入（`percent` → `stageIndexFromPercent`），
 * 保证文案与进度条永远一致。失败时冻结进度并给出「重试 / 收起」两个出口。
 */
export function AiAnalysisProgress({ percent, elapsedMs, failed, onRetry, onDismiss }: AiAnalysisProgressProps) {
  const stageIndex = stageIndexFromPercent(percent)
  const currentStage = ANALYSIS_STAGES[stageIndex]

  return (
    <div className="flex flex-col gap-3 py-0.5" role="status" aria-live="polite">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="relative flex h-2 w-2 shrink-0">
            {!failed && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#5645D4] opacity-70" />
            )}
            <span
              className={`relative inline-flex h-2 w-2 rounded-full ${
                failed ? 'bg-[var(--color-error)]' : 'bg-[#5645D4]'
              }`}
            />
          </span>
          <span
            className={`truncate text-[13px] font-medium ${
              failed ? 'text-[var(--color-error)]' : 'animate-pulse text-[var(--color-ink)]'
            }`}
          >
            {failed ? '分析已中断' : `${currentStage.label}…`}
          </span>
        </div>
        <span className="shrink-0 text-[12px] tabular-nums text-[var(--color-stone)]">
          已用 {elapsedSeconds(elapsedMs)} 秒
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <Progress
          percent={percent}
          showInfo={false}
          size="small"
          status={failed ? 'exception' : 'active'}
          strokeColor={failed ? '#E03131' : '#5645D4'}
          railColor="#EEECFB"
        />
        <span className="text-[12px] leading-4 text-[var(--color-stone)]">
          {failed ? `中断在 ${percent}%，可重试或稍后重新进入详情页查看` : 'AI 分析通常需要 20–60 秒，请勿关闭页面'}
        </span>
      </div>

      <ol className="flex flex-col gap-2">
        {ANALYSIS_STAGES.map((stage, index) => {
          const state: StageState = failed
            ? index < stageIndex
              ? 'done'
              : index === stageIndex
                ? 'error'
                : 'wait'
            : index < stageIndex
              ? 'done'
              : index === stageIndex
                ? 'active'
                : 'wait'

          return (
            <li key={stage.label} className="flex items-start gap-2">
              <span className="flex h-4 w-4 shrink-0 items-center justify-center text-[12px] leading-none">
                {state === 'done' || state === 'error' ? (
                  STAGE_ICON[state]
                ) : state === 'active' ? (
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#5645D4] opacity-70" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#5645D4]" />
                  </span>
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full border border-[var(--color-hairline-strong)]" />
                )}
              </span>
              <div className="min-w-0">
                <span
                  className={`text-[12px] leading-4 ${
                    state === 'active'
                      ? 'font-medium text-[#4534B3]'
                      : state === 'error'
                        ? 'font-medium text-[var(--color-error)]'
                        : state === 'done'
                          ? 'text-[var(--color-steel)]'
                          : 'text-[var(--color-muted)]'
                  }`}
                >
                  {stage.label}
                </span>
                {state === 'active' && (
                  <p className="text-[12px] leading-4 text-[var(--color-slate)]">{stage.hint}</p>
                )}
              </div>
            </li>
          )
        })}
      </ol>

      {failed ? (
        <Alert
          type="error"
          showIcon
          title="AI 分析未完成"
          description={failed}
          action={
            <Space size={4}>
              <Button size="small" type="primary" onClick={onRetry}>
                重试
              </Button>
              <Button size="small" onClick={onDismiss}>
                收起
              </Button>
            </Space>
          }
        />
      ) : (
        <p className="text-[12px] leading-4 text-[var(--color-stone)]">
          分析结果不会自动保存，生成后请人工校对再保存。
        </p>
      )}
    </div>
  )
}