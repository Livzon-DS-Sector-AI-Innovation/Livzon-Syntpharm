'use client'

import { useState } from 'react'
import { App, Button, Card, Empty, Input, Space, Tag } from 'antd'
import { RobotOutlined } from '@ant-design/icons'
import { completeDeviationAiAnalysis, startDeviationAiAnalysis } from '@/actions/quality'
import type { DeviationAiAnalysisData, DeviationLedgerDetail } from '@/types/quality'

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

/** AI 智能分析：生成 → 人工校对 → 确认保存并转入调查 */
export function AiAnalysisCard({ ledger, onUpdated }: AiAnalysisCardProps) {
  const { message } = App.useApp()
  const [draft, setDraft] = useState<Draft>(() => toDraft(ledger.ai_analysis))
  const [signature, setSignature] = useState(() => JSON.stringify(ledger.ai_analysis ?? null))
  const [busy, setBusy] = useState<'generate' | 'save' | null>(null)

  // 外部刷新（如 AI 重新生成）后同步草稿
  const incoming = JSON.stringify(ledger.ai_analysis ?? null)
  if (incoming !== signature) {
    setSignature(incoming)
    setDraft(toDraft(ledger.ai_analysis))
  }

  const canAnalyze = (ledger.allowed_actions ?? []).includes('analyze')
  const canSave = ledger.can_operate && ledger.status !== 'closed' && ledger.status !== 'cancelled'
  const hasContent = Object.values(draft).some((value) => value.trim().length > 0)

  const handleGenerate = async () => {
    setBusy('generate')
    const result = await startDeviationAiAnalysis(ledger.id)
    setBusy(null)
    if (result.code === 200 && result.data) {
      setDraft(toDraft(result.data.ai_analysis))
      onUpdated(result.data)
      message.success('AI 分析已生成，请校对后确认')
    } else {
      message.error(result.message)
    }
  }

  const handleSave = async () => {
    setBusy('save')
    const result = await completeDeviationAiAnalysis(ledger.id, {
      ai_analysis: { ...draft },
      content: '人工校对后确认 AI 分析',
    })
    setBusy(null)
    if (result.code === 200 && result.data) {
      onUpdated(result.data)
      message.success('分析已保存并转入调查')
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
      className="scroll-mt-40 shadow-sm"
      extra={
        <Space wrap size={4}>
          {canAnalyze && (
            <Button size="small" loading={busy === 'generate'} onClick={handleGenerate}>
              {hasContent ? '重新生成' : '开始分析'}
            </Button>
          )}
          {canSave && hasContent && (
            <Button type="primary" size="small" loading={busy === 'save'} onClick={handleSave}>
              确认并转入调查
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
                disabled={!canSave}
                maxLength={4000}
                onChange={(event) => setDraft((prev) => ({ ...prev, [field.key]: event.target.value }))}
              />
            </div>
          ))}
        </div>
      )}
    </Card>
  )
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