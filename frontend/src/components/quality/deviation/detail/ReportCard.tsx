'use client'

import { useMemo, useState } from 'react'
import { App, Button, Card, Collapse, Empty, Input } from 'antd'
import { saveDeviationReport } from '@/actions/quality'
import type { DeviationLedgerDetail, DeviationReportVersion } from '@/types/quality'
import { PersonInline } from '../PersonInline'

interface ReportCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
}

function formatTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

/** 调查报告：正文编辑 + 历史版本（调查文档在「调查记录」区上传与呈现） */
export function ReportCard({ ledger, onUpdated }: ReportCardProps) {
  const { message } = App.useApp()
  const [content, setContent] = useState(ledger.report_content ?? '')
  const [summary, setSummary] = useState('')
  const [saving, setSaving] = useState(false)

  // 外部刷新（提交调查 / 重新拉取）后同步正文草稿
  const incoming = ledger.report_content ?? ''
  const [synced, setSynced] = useState(incoming)
  if (synced !== incoming) {
    setSynced(incoming)
    setContent(incoming)
  }

  const editable = ledger.can_operate && ledger.current_step === 'investigation'

  const versionItems = useMemo(() => {
    const versions: DeviationReportVersion[] = ledger.report_versions ?? []
    return versions.map((version, index) => ({
        key: `${version.edit_time ?? index}-${index}`,
        label: (
          <span className="flex flex-wrap items-center gap-2 text-[13px]">
            <span className="font-medium text-[var(--color-ink)]">版本 {versions.length - index}</span>
            <span className="flex items-center gap-1 text-[12px] text-[var(--color-slate)]">
              <PersonInline
                person={{
                  id: version.editor_id,
                  name: version.editor_name,
                  avatar_url: version.editor_avatar,
                }}
                avatarSize={20}
              />
              <span>· {formatTime(version.edit_time)}</span>
            </span>
            {version.change_summary && (
              <span className="text-[12px] text-[var(--color-stone)]">{version.change_summary}</span>
            )}
          </span>
        ),
        children: (
          <p className="whitespace-pre-wrap break-words text-[13px] leading-5 text-[var(--color-slate)]">
            {version.content || '（空）'}
          </p>
        ),
      }))
  }, [ledger.report_versions])

  const handleSave = async () => {
    if (!content.trim()) {
      message.warning('请填写调查报告内容')
      return
    }
    setSaving(true)
    const result = await saveDeviationReport(ledger.id, {
      content,
      change_summary: summary.trim() || undefined,
      append_version: true,
    })
    setSaving(false)
    if (result.code === 200 && result.data) {
      setSummary('')
      onUpdated(result.data)
      message.success('调查报告已保存')
    } else {
      message.error(result.message)
    }
  }

  return (
    <Card
      id="report"
      size="small"
      title="调查报告"
      className="scroll-mt-40 shadow-sm"
      extra={
        <span className="text-[12px] text-[var(--color-stone)]">
          {ledger.report_versions?.length ?? 0} 个版本 · 调查文档见「调查记录」
        </span>
      }
    >
      <div className="flex flex-col gap-2">
        <Input.TextArea
          rows={6}
          value={content}
          maxLength={20000}
          showCount
          disabled={!editable}
          placeholder={editable ? '填写调查报告（调查过程、根因分析、风险评估、纠正措施等）' : '暂无可编辑的调查报告'}
          onChange={(event) => setContent(event.target.value)}
        />
        {editable && (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[var(--color-hairline)] pt-3">
            <Input
              value={summary}
              maxLength={255}
              placeholder="本次修改说明（可选，记入版本记录）"
              className="w-full sm:w-auto sm:flex-1"
              onChange={(event) => setSummary(event.target.value)}
            />
            <Button type="primary" loading={saving} onClick={handleSave}>
              保存报告
            </Button>
          </div>
        )}
      </div>

      <div className="mt-4 border-t border-[var(--color-hairline)] pt-3">
        <h3 className="mb-2 text-[13px] font-semibold text-[var(--color-ink)]">版本记录</h3>
        {versionItems.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无版本记录" />
        ) : (
          <Collapse size="small" items={versionItems} />
        )}
      </div>
    </Card>
  )
}