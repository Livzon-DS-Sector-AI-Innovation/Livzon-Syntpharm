'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { App, Button, Empty, Input, Space, Tag } from 'antd'
import { FormOutlined } from '@ant-design/icons'
import {
  completeDeviationAiAnalysis,
  getDeviationJobStatus,
  startDeviationAiAnalysis,
} from '@/actions/quality'
import type {
  DeviationAiAnalysisData,
  DeviationInvestigationPrefill,
  DeviationJobState,
  DeviationLedgerDetail,
} from '@/types/quality'
import { AiAnalysisProgress } from './AiAnalysisProgress'
import { ANALYSIS_FINISH_HOLD_MS, ANALYSIS_TICK_INTERVAL_MS, progressFromElapsed } from './aiAnalysisProgress'
import { buildInvestigationPrefill } from './aiPrefill'
import { SectionCard } from './SectionCard'

interface AiAnalysisCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
  /** 把当前 AI 结果带入调查表单（只填不提交）；调查节点之外不传 */
  onFillInvestigation?: (prefill: DeviationInvestigationPrefill) => void
}

type Draft = Pick<DeviationAiAnalysisData, 'description' | 'reason' | 'risk_assessment' | 'capa_suggestion'>

/**
 * 一次分析过程的状态机：
 * - `running`：过程区 + 心跳计时，进度封顶 90%
 * - `finishing`：进度定格 100%，短暂展示后切换结果
 * - `failed`：进度冻结、显示失败原因，可重试或收起（草稿保持分析前的值）
 */
interface AnalysisRun {
  startedAt: number
  phase: 'running' | 'finishing' | 'failed'
  error?: string
}

const EMPTY_DRAFT: Draft = { description: '', reason: '', risk_assessment: '', capa_suggestion: '' }

const FIELDS: { key: keyof Draft; label: string; rows: number; placeholder: string }[] = [
  { key: 'description', label: '偏差描述（AI 结构化）', rows: 3, placeholder: 'AI 将根据上报信息整理偏差描述' },
  { key: 'reason', label: '可能原因', rows: 3, placeholder: 'AI 将给出可能原因，可人工修改' },
  { key: 'risk_assessment', label: '风险评估', rows: 3, placeholder: 'AI 将评估质量风险' },
  { key: 'capa_suggestion', label: '提出 CAPA', rows: 3, placeholder: 'AI 将给出 CAPA 建议（仅文本，不建 CAPA 单）' },
]

/**
 * AI 智能分析：除「已关闭 / 已取消」外任意节点都可生成 / 重新分析 → 人工校对 → 保存结果
 * （只保存，不流转；流程由提交调查报告驱动）。
 * 调查表单可打开时额外提供「一键填写调查报告」：只把结果带入表单空白项，不提交。
 *
 * 分析期间（后端异步任务最长约 180 秒）卡片内容区整体替换为过程区：阶段文案闪烁 + 进度条 + 已耗时。
 */
export function AiAnalysisCard({ ledger, onUpdated, onFillInvestigation }: AiAnalysisCardProps) {
  const { message } = App.useApp()
  // 已保存结果的指纹：外部刷新（保存成功 / 重新拉取详情）后草稿自动回落到最新保存值
  const savedDraft = useMemo(() => toDraft(ledger.ai_analysis), [ledger.ai_analysis])
  const savedKey = useMemo(() => JSON.stringify(savedDraft), [savedDraft])
  const [edit, setEdit] = useState<{ key: string; draft: Draft }>(() => ({ key: savedKey, draft: savedDraft }))
  const [busy, setBusy] = useState<'save' | null>(null)
  const [run, setRun] = useState<AnalysisRun | null>(null)
  // 「100% 定格」定时器：卸载时清理，避免卸载后写状态
  const finishTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const draft = edit.key === savedKey ? edit.draft : savedDraft
  const updateDraft = (next: Draft) => setEdit({ key: savedKey, draft: next })

  // 只有分析进行中才需要心跳；其余状态停表，进度与秒数随之冻结
  const now = useTick(run?.phase === 'running' ? ANALYSIS_TICK_INTERVAL_MS : null)
  const elapsedMs = run ? Math.max(0, now - run.startedAt) : 0
  // 完成前永远不到 100%：90% 封顶，任务返回后由 finishing 态显式置满
  const percent = !run ? 0 : run.phase === 'finishing' ? 100 : progressFromElapsed(elapsedMs)

  useEffect(() => {
    return () => {
      if (finishTimer.current) {
        clearTimeout(finishTimer.current)
        finishTimer.current = null
      }
    }
  }, [])

  // 后端 allowed_actions 已放开到除「已关闭 / 已取消」外全部节点；人员限上报人 / 调查人 / 超管
  const canAnalyze = (ledger.allowed_actions ?? []).includes('analyze')
  // 可分析即意味着可编辑与保存：状态与人员门禁统一由后端单一真源决定
  const editable = canAnalyze
  // 调查表单可打开时（待 AI 分析 / 待调查 / 退回调查）才提供「一键填写调查报告」
  const canInvestigate = (ledger.allowed_actions ?? []).includes('investigate')
  const hasContent = Object.values(draft).some((value) => value.trim().length > 0)
  const dirty = JSON.stringify(draft) !== savedKey
  // 过程区在失败态仍占位（显示原因与出口），但按钮只在真正跑着时上锁
  const analyzing = run !== null
  const running = run?.phase === 'running' || run?.phase === 'finishing'

  const handleGenerate = async () => {
    // 进行中（含定格）不重复提交；失败态允许「重试」
    if (run?.phase === 'running' || run?.phase === 'finishing') return

    setRun({ startedAt: Date.now(), phase: 'running' })
    const fail = (error: string) => setRun((prev) => (prev ? { ...prev, phase: 'failed', error } : prev))

    try {
      const submitted = await startDeviationAiAnalysis(ledger.id)
      if (submitted.code !== 200 || !submitted.data) {
        fail(submitted.message || '提交 AI 分析任务失败')
        return
      }
      const job = await waitForJob(submitted.data.job_id)
      if (!job) {
        fail('等待分析结果超时，任务可能仍在后台运行，可重试或稍后重新进入详情页查看')
        return
      }
      if (job.status === 'failed') {
        fail(job.error ?? 'AI 分析失败')
        return
      }
      const aiAnalysis = pickAiAnalysis(job.result)
      // 先定格 100% 再切结果：避免进度条刚满、区域就整块消失
      setRun((prev) => (prev ? { ...prev, phase: 'finishing' } : prev))
      finishTimer.current = setTimeout(() => {
        finishTimer.current = null
        // 只更新本地草稿：AI 结果需人工校对后保存，刷新页面仍显示上一次保存的结果
        updateDraft(toDraft(aiAnalysis))
        message.success('AI 分析已生成，请校对后保存')
        setRun(null)
      }, ANALYSIS_FINISH_HOLD_MS)
    } catch (error) {
      // 网络/Server Action 异常只给中文兜底文案，原始错误留在控制台便于排查
      console.error('deviation ai analysis failed', error)
      fail('AI 分析请求失败，请稍后重试')
    }
  }

  const handleSave = async () => {
    setBusy('save')
    const result = await completeDeviationAiAnalysis(ledger.id, { ai_analysis: { ...draft } })
    setBusy(null)
    if (result.code === 200 && result.data) {
      onUpdated(result.data)
      message.success('分析结果已保存')
    } else {
      message.error(result.message)
    }
  }

  /** 一键填写：把当前 AI 结果（含未保存的本次生成）带给调查表单，只填不提交 */
  const handleFill = () => {
    if (!onFillInvestigation) return
    const prefill = buildInvestigationPrefill(draft)
    if (!prefill) {
      message.warning('当前没有可带入的 AI 分析内容')
      return
    }
    onFillInvestigation(prefill)
  }

  return (
    <SectionCard
      section="ai-analysis"
      ledger={ledger}
      badge={
        run?.phase === 'failed' ? (
          <Tag color="error">AI 分析失败</Tag>
        ) : running ? (
          <Tag color="processing">AI 分析中</Tag>
        ) : dirty ? (
          <Tag color="orange">有未保存的修改</Tag>
        ) : null
      }
      extra={
        <Space wrap size={4}>
          {canAnalyze && (
            <Button size="small" loading={running} disabled={running} onClick={handleGenerate}>
              {running ? '分析中…' : run?.phase === 'failed' ? '重试分析' : hasContent ? '重新分析' : '开始分析'}
            </Button>
          )}
          {editable && hasContent && (
            <Button
              type="primary"
              size="small"
              loading={busy === 'save'}
              disabled={analyzing}
              onClick={handleSave}
            >
              保存分析结果
            </Button>
          )}
          {canInvestigate && hasContent && onFillInvestigation && (
            <Button size="small" icon={<FormOutlined />} disabled={analyzing} onClick={handleFill}>
              一键填写调查报告
            </Button>
          )}
        </Space>
      }
    >
      {run ? (
        <AiAnalysisProgress
          percent={percent}
          elapsedMs={elapsedMs}
          failed={run.phase === 'failed' ? (run.error ?? 'AI 分析失败') : null}
          onRetry={handleGenerate}
          onDismiss={() => setRun(null)}
        />
      ) : !hasContent ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无 AI 分析结果，点击右上角「开始分析」自动生成"
        />
      ) : (
        <div className="flex flex-col gap-3">
          {ledger.ai_analysis?.model && (
            <p className="text-[12px] text-[var(--color-stone)]">
              模型：{ledger.ai_analysis.model} · 生成时间：
              {ledger.ai_analysis.generated_at
                ? new Date(ledger.ai_analysis.generated_at).toLocaleString('zh-CN', { hour12: false })
                : '-'}
              <Tag className="ml-2" color="blue">
                AI 结果需人工核对
              </Tag>
            </p>
          )}
          {FIELDS.map((field) => (
            <div key={field.key}>
              <label className="mb-1 block text-[13px] font-medium text-[var(--color-ink)]">
                {field.label}
              </label>
              <Input.TextArea
                rows={field.rows}
                value={draft[field.key]}
                placeholder={field.placeholder}
                disabled={!editable}
                maxLength={4000}
                onChange={(event) => updateDraft({ ...draft, [field.key]: event.target.value })}
              />
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  )
}

const JOB_POLL_INTERVAL_MS = 1500
// 1.5s × 120 ≈ 180s：模型偏慢时不误报失败，过程区可承载更长的等待
const JOB_POLL_MAX_ATTEMPTS = 120

/** 轮询后台任务：done/failed 返回终态，超过约 180s 返回 null（提示任务可能仍在后台） */
async function waitForJob(jobId: string): Promise<DeviationJobState | null> {
  for (let attempt = 0; attempt < JOB_POLL_MAX_ATTEMPTS; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, JOB_POLL_INTERVAL_MS))
    const state = await getDeviationJobStatus(jobId)
    if (state.code !== 200 || !state.data) continue
    if (state.data.status !== 'running') return state.data
  }
  return null
}

/**
 * 心跳：仅在 `intervalMs` 非空时每 `intervalMs` 刷新当前时间戳，用于驱动秒数与进度重渲染。
 * 定时器在 useEffect 的 cleanup 中清理，卸载后不会再写状态。
 */
function useTick(intervalMs: number | null): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (intervalMs === null) return
    const timer = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(timer)
  }, [intervalMs])

  return now
}

/** 任务返回值是通用字典（生成类型 `result?: {[key: string]: unknown} | null`），此处收窄为 AI 分析 DTO */
function pickAiAnalysis(result: DeviationJobState['result']): DeviationAiAnalysisData | null {
  if (!result || typeof result !== 'object') return null
  const analysis = (result as Record<string, unknown>).ai_analysis
  if (!analysis || typeof analysis !== 'object') return null
  return analysis as DeviationAiAnalysisData
}

function toDraft(analysis: DeviationAiAnalysisData | null | undefined): Draft {
  if (!analysis) return { ...EMPTY_DRAFT }
  return {
    description: analysis.description ?? '',
    reason: analysis.reason ?? '',
    risk_assessment: analysis.risk_assessment ?? '',
    capa_suggestion: analysis.capa_suggestion ?? '',
  }
}