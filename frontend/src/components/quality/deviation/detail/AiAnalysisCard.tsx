'use client'

import { useMemo, useState } from 'react'
import { App, Button, Card, Empty, Input, Space, Tag } from 'antd'
import { RobotOutlined } from '@ant-design/icons'
import {
  completeDeviationAiAnalysis,
  getDeviationJobStatus,
  startDeviationAiAnalysis,
} from '@/actions/quality'
import type { DeviationAiAnalysisData, DeviationJobState, DeviationLedgerDetail } from '@/types/quality'

interface AiAnalysisCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
}

type Draft = Pick<DeviationAiAnalysisData, 'description' | 'reason' | 'risk_assessment' | 'capa_suggestion'>

const EMPTY_DRAFT: Draft = { description: '', reason: '', risk_assessment: '', capa_suggestion: '' }

const FIELDS: { key: keyof Draft; label: string; rows: number; placeholder: string }[] = [
  { key: 'description', label: '偏差描述（AI 结构化）', rows: 3, placeholder: 'AI 将根据上报信息整理偏差描述' },
  { key: 'reason', label: '可能原因', rows: 3, placeholder: 'AI 将给出可能原因，可人工修改' },
  { key: 'risk_assessment', label: '风险评估', rows: 3, placeholder: 'AI 将评估质量风险' },
  { key: 'capa_suggestion', label: '提出 CAPA', rows: 3, placeholder: 'AI 将给出 CAPA 建议（仅文本，不建 CAPA 单）' },
]

/** AI 智能分析：生成 / 重新分析 → 人工校对 → 保存结果（只保存，不流转；流程由提交调查报告驱动） */
export function AiAnalysisCard({ ledger, onUpdated }: AiAnalysisCardProps) {
  const { message } = App.useApp()
  // 已保存结果的指纹：外部刷新（保存成功 / 重新拉取详情）后草稿自动回落到最新保存值
  const savedDraft = useMemo(() => toDraft(ledger.ai_analysis), [ledger.ai_analysis])
  const savedKey = useMemo(() => JSON.stringify(savedDraft), [savedDraft])
  const [edit, setEdit] = useState<{ key: string; draft: Draft }>(() => ({ key: savedKey, draft: savedDraft }))
  const [busy, setBusy] = useState<'generate' | 'save' | null>(null)

  const draft = edit.key === savedKey ? edit.draft : savedDraft
  const updateDraft = (next: Draft) => setEdit({ key: savedKey, draft: next })

  const canAnalyze = (ledger.allowed_actions ?? []).includes('analyze')
  // 与后端可编辑口径对齐：待 AI 分析与已退回可编辑，其余阶段只读展示已保存结果
  const editable = ledger.can_operate && (ledger.status === 'pending_ai_analysis' || ledger.status === 'returned')
  const hasContent = Object.values(draft).some((value) => value.trim().length > 0)
  const dirty = JSON.stringify(draft) !== savedKey

  const handleGenerate = async () => {
    setBusy('generate')
    try {
      const submitted = await startDeviationAiAnalysis(ledger.id)
      if (submitted.code !== 200 || !submitted.data) {
        message.error(submitted.message)
        return
      }
      const job = await waitForJob(submitted.data.job_id)
      if (!job) {
        message.error('AI 分析耗时较长，请稍后重新进入详情页查看')
        return
      }
      if (job.status === 'failed') {
        message.error(job.error ?? 'AI 分析失败')
        return
      }
      const payload = job.result as { ai_analysis?: DeviationAiAnalysisData } | null
      // 只更新本地草稿：AI 结果需人工校对后保存，刷新页面仍显示上一次保存的结果
      updateDraft(toDraft(payload?.ai_analysis))
      message.success('AI 分析已生成，请校对后保存')
    } finally {
      setBusy(null)
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

  return (
    <Card
      id="ai-analysis"
      size="small"
      title={
        <span className="flex items-center gap-2">
          <RobotOutlined className="text-[var(--color-primary)]" />
          AI 智能分析
        </span>
      }
      className="scroll-mt-6 shadow-sm"
      extra={
        <Space wrap size={4}>
          {dirty && <Tag color="orange">有未保存的修改</Tag>}
          {canAnalyze && (
            <Button size="small" loading={busy === 'generate'} onClick={handleGenerate}>
              {hasContent ? '重新分析' : '开始分析'}
            </Button>
          )}
          {editable && hasContent && (
            <Button type="primary" size="small" loading={busy === 'save'} onClick={handleSave}>
              保存分析结果
            </Button>
          )}
        </Space>
      }
    >
      {!hasContent ? (
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
    </Card>
  )
}

const JOB_POLL_INTERVAL_MS = 1500
const JOB_POLL_MAX_ATTEMPTS = 40

/** 轮询后台任务：done/failed 返回终态，超过约 60s 返回 null（提示用户稍后查看） */
async function waitForJob(jobId: string): Promise<DeviationJobState | null> {
  for (let attempt = 0; attempt < JOB_POLL_MAX_ATTEMPTS; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, JOB_POLL_INTERVAL_MS))
    const state = await getDeviationJobStatus(jobId)
    if (state.code !== 200 || !state.data) continue
    if (state.data.status !== 'running') return state.data
  }
  return null
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