'use client'

import { useCallback, useEffect, useState } from 'react'
import { App, Button, Empty, Input, Modal, Space } from 'antd'
import { DownloadOutlined, FileTextOutlined, SendOutlined, WarningOutlined } from '@ant-design/icons'
import { submitDeviationInvestigationForReview } from '@/actions/quality'
import type {
  DeviationAttachment,
  DeviationInvestigationPrefill,
  DeviationInvestigationRecord,
  DeviationLedgerDetail,
} from '@/types/quality'
import { PersonInline } from '../PersonInline'
import { AttachmentPreviewDrawer } from './AttachmentPreviewDrawer'
import { InvestigationRecordForm } from './InvestigationRecordForm'
import { SectionCard } from './SectionCard'
import { scrollToSection } from './detailScroll'

interface InvestigationCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
  /** AI 分析带入调查表单的一次性载荷（只填空白，不提交） */
  prefill?: DeviationInvestigationPrefill | null
  /** 表单应用完 prefill 后回调实际写入项数，父级据此清空载荷并提示 */
  onPrefillApplied?: (filled: number) => void
}

function attachmentUrl(ledgerId: string, fileId: string): string {
  return `/api/v1/quality/deviation/ledger/${ledgerId}/attachments/${fileId}/download`
}

function formatSize(size: number): string {
  if (!size) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

function formatTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

/** 正文小节：统一「灰字标题 + 正文」排版 */
function Section({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-md bg-[var(--color-surface-soft,#fafafa)] px-2.5 py-2">
      <div className="text-[12px] font-medium text-[var(--color-slate)]">{title}</div>
      <p className="mt-0.5 whitespace-pre-wrap break-words text-[13px] leading-5 text-[var(--color-ink)]">{text}</p>
    </div>
  )
}

/** 记录正文：不符合事项 → 根因 → 风险 → CAPA → 紧急措施 → 记录附件；旧纯文本记录降级为段落展示 */
function RecordBody({
  ledgerId,
  record,
  onPreview,
}: {
  ledgerId: string
  record: DeviationInvestigationRecord
  onPreview: (attachment: DeviationAttachment) => void
}) {
  const capaRows = record.capa_proposals ?? []
  const recordAttachments = record.attachments ?? []
  const hasTextContent = Boolean(
    record.nonconformity_description ||
      record.root_cause_analysis ||
      record.risk_assessment ||
      record.urgent_measures ||
      capaRows.length,
  )
  // 附件路线：只引用了调查报告附件、未填文本，属于有效提交形态
  const viaAttachmentOnly = !hasTextContent && recordAttachments.length > 0
  if (!hasTextContent && !record.content && !viaAttachmentOnly) {
    return <p className="text-[13px] text-[var(--color-stone)]">（无文本内容）</p>
  }
  if (!hasTextContent && record.content) {
    return (
      <p className="whitespace-pre-wrap break-words text-[13px] leading-5 text-[var(--color-ink)]">{record.content}</p>
    )
  }
  const sections = [
    { title: '不符合事项描述', text: record.nonconformity_description },
    { title: '根本原因分析', text: record.root_cause_analysis },
    { title: '风险评估', text: record.risk_assessment },
  ].filter((section) => section.text)
  return (
    <div className="flex flex-col gap-2">
      {viaAttachmentOnly && (
        <span className="text-[12px] text-[#2f6fed]">以调查报告附件形式提交，文本内容见下方附件。</span>
      )}
      {sections.map((section) => (
        <Section key={section.title} title={section.title} text={section.text ?? ''} />
      ))}
      {capaRows.length > 0 && (
        <div className="rounded-md bg-[var(--color-surface-soft,#fafafa)] px-2.5 py-2">
          <div className="text-[12px] font-medium text-[var(--color-slate)]">改进建议（CAPA）</div>
          <ol className="mt-1 flex list-decimal flex-col gap-1 pl-5 text-[13px] text-[var(--color-ink)]">
            {capaRows.map((row, index) => (
              <li key={row.sequence ?? index} className="break-words">
                {row.summary}
                {(row.executor || row.expected_completion_date) && (
                  <span className="text-[12px] text-[var(--color-slate)]">
                    {' '}
                    —— {row.executor ?? '执行人待定'}
                    {row.expected_completion_date ? ` · 预计 ${row.expected_completion_date}` : ''}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
      {record.urgent_measures && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-2">
          <span className="flex items-center gap-1 text-[12px] font-medium text-amber-800">
            <WarningOutlined />
            紧急处理措施
          </span>
          <p className="mt-1 whitespace-pre-wrap break-words text-[13px] leading-5 text-amber-900">
            {record.urgent_measures}
          </p>
        </div>
      )}
      {recordAttachments.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-[12px] font-medium text-[var(--color-slate)]">
            {viaAttachmentOnly ? '调查报告' : '记录附件'}
          </span>
          {recordAttachments.map((attachment) => (
            <div
              key={attachment.file_id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--color-hairline)] px-2.5 py-1.5 transition-colors hover:bg-[var(--color-fill,#f4f4f5)]"
            >
              <span className="flex min-w-0 items-center gap-1.5 text-[12px]">
                <FileTextOutlined className="shrink-0 text-[var(--color-slate)]" />
                <span className="truncate text-[var(--color-ink)]">{attachment.file_name}</span>
                <span className="shrink-0 text-[var(--color-stone)]">{formatSize(attachment.size)}</span>
              </span>
              <Space size={2} className="shrink-0">
                <Button type="link" size="small" className="!px-1" onClick={() => onPreview(attachment)}>
                  预览
                </Button>
                <Button
                  type="link"
                  size="small"
                  className="!px-1"
                  icon={<DownloadOutlined />}
                  href={attachmentUrl(ledgerId, attachment.file_id)}
                >
                  下载
                </Button>
              </Space>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * 调查记录：时间线改为卡片流（作者/部门/时间 + 分区正文 + 附件预览下载）。
 * 附件只在调查记录内维护：未提交时在表单中上传/删除，提交后只能预览与下载。
 */
export function InvestigationCard({ ledger, onUpdated, prefill, onPrefillApplied }: InvestigationCardProps) {
  const { message } = App.useApp()
  // 结构化调查表单：submit=提交调查（流转），append=追加记录（不流转），null=收起
  const [formMode, setFormMode] = useState<'submit' | 'append' | null>(null)
  // 卡片快捷提交：调查记录已填写后可直接提交审核（不新建记录）
  const [submitOpen, setSubmitOpen] = useState(false)
  const [submitInfo, setSubmitInfo] = useState('')
  const [overrideReason, setOverrideReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  // 当前正在预览的附件：非空即打开预览抽屉（左文档 + 右批注）
  const [previewAttachment, setPreviewAttachment] = useState<DeviationAttachment | null>(null)

  const handlePreview = useCallback((attachment: DeviationAttachment) => {
    setPreviewAttachment(attachment)
  }, [])

  const closePreview = useCallback(() => setPreviewAttachment(null), [])
  // 已关闭 / 已取消的偏差：批注只读存档
  const commentsFrozen = ledger.status === 'closed' || ledger.status === 'cancelled'

  const actions = ledger.allowed_actions ?? []
  const canInvestigate = actions.includes('investigate')
  const records = ledger.investigation_records ?? []
  // 主流程调查草稿（department 为空的本人草稿）；跨部门行草稿在跨部门卡片内使用
  const mainDraft =
    (ledger.investigation_drafts ?? []).find((draft) => (draft.department ?? null) === null) ?? null
  // 调查人 / 上报人在调查中与审核阶段都可维护调查记录（后端单一真源）
  const canEditInvestigation = ledger.can_edit_investigation === true
  // 已进入审核（不再有提交调查动作）时，展示「只追加不流转」的补录入口
  const canAppend = canEditInvestigation && !canInvestigate
  const lastUpdated = records.length > 0 ? records[records.length - 1].create_time : null
  // 二选一：已有主流程调查记录（文本 / CAPA / 引用附件）或台账已有调查报告附件，才允许直接提交审核
  const hasInvestigationMaterial =
    records.some(
      (record) =>
        !record.department &&
        Boolean(
          record.content ||
            record.nonconformity_description ||
            record.root_cause_analysis ||
            record.risk_assessment ||
            (record.capa_proposals ?? []).length ||
            (record.attachments ?? []).length,
        ),
    ) || (ledger.attachments ?? []).length > 0

  const handleSubmitForReview = async () => {
    setSubmitting(true)
    const result = await submitDeviationInvestigationForReview(ledger.id, {
      content: submitInfo.trim() || null,
      override_reason: overrideReason.trim() || undefined,
    })
    setSubmitting(false)
    if (result.code === 200 && result.data) {
      setSubmitOpen(false)
      setSubmitInfo('')
      message.success('调查已提交审核，进入部门负责人审核')
      onUpdated(result.data)
    } else {
      message.error(result.message)
    }
  }

  // AI 一键填写：展开提交表单并滚动到本卡片；表单内部按 nonce 去重并只补空白
  useEffect(() => {
    if (!prefill) return
    if (!canInvestigate) {
      //: 调查表单不可打开的节点（如审核、已关闭）直接消费掉，避免悬挂
      onPrefillApplied?.(0)
      return
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- AI 卡片发出的一次性跨组件指令；改为派生会在填充完成、父级清空 prefill 时误关表单
    setFormMode('submit')
    const timer = window.setTimeout(() => {
      scrollToSection('investigation')
    }, 60)
    return () => window.clearTimeout(timer)
  }, [prefill, canInvestigate, onPrefillApplied])

  return (
    <SectionCard
      section="investigation"
      ledger={ledger}
      extra={
        <span className="text-[12px] text-[var(--color-stone)]">
          {records.length} 条记录
          {lastUpdated ? ` · 最近更新 ${formatTime(lastUpdated)}` : ''}
        </span>
      }
    >
      {mainDraft && formMode === null && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#c7d7fb] bg-[#eff4ff] px-3 py-2">
          <span className="text-[12px] text-[#2f4b8f]">
            有未提交的调查草稿 · 暂存于 {formatTime(mainDraft.updated_at)}
          </span>
          <Button type="link" size="small" className="!h-auto !p-0 !text-[12px]" onClick={() => setFormMode('submit')}>
            继续填写
          </Button>
        </div>
      )}

      {records.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无调查记录" />
      ) : (
        <div className="flex flex-col gap-2.5">
          {records.map((record, index) => (
            <div
              key={`${record.create_time ?? ''}-${index}`}
              className="rounded-lg border border-[var(--color-hairline)] bg-white p-3 transition-all hover:border-[#c7d7fb] hover:shadow-sm"
            >
              <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[12px] text-[var(--color-slate)]">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#eff4ff] text-[11px] font-medium text-[#2f6fed]">
                  {index + 1}
                </span>
                <PersonInline
                  person={{ id: record.author_id, name: record.author_name, avatar_url: record.author_avatar }}
                  avatarSize={20}
                />
                {record.department && (
                  <span className="rounded-full bg-[var(--color-fill,#f4f4f5)] px-1.5 py-0.5 text-[11px]">
                    跨部门 · {record.department}
                  </span>
                )}
                <span>· {formatTime(record.create_time)}</span>
              </div>
              <RecordBody ledgerId={ledger.id} record={record} onPreview={handlePreview} />
            </div>
          ))}
        </div>
      )}

      {(canInvestigate || canAppend) && formMode === null && (
        <div className="mt-3 flex flex-col gap-2 border-t border-[var(--color-hairline)] pt-3">
          <span className="text-[12px] text-[var(--color-stone)]">
            {canInvestigate
              ? '填写结构化调查报告，或上传调查报告文档——二者满足其一即可提交，提交后进入部门负责人审核。'
              : '流程已进入审核，此处补充调查记录仅追加内容，不会改变流程状态。'}
          </span>
          <div className="flex flex-wrap justify-end gap-2">
            <Button
              type={canInvestigate && !hasInvestigationMaterial ? 'primary' : 'default'}
              onClick={() => setFormMode(canInvestigate ? 'submit' : 'append')}
            >
              {canInvestigate ? (mainDraft ? '继续填写调查报告' : '填写调查报告') : '追加调查记录'}
            </Button>
            {canInvestigate && (
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={() => {
                  if (!hasInvestigationMaterial) {
                    message.warning('请先填写调查记录，或上传并引用调查报告附件后再提交审核')
                    return
                  }
                  setSubmitOpen(true)
                }}
              >
                提交审核
              </Button>
            )}
          </div>
        </div>
      )}

      {formMode && (canInvestigate || canAppend) && (
        <InvestigationRecordForm
          key={formMode}
          ledger={ledger}
          mode={formMode}
          initialDraft={mainDraft}
          prefill={prefill}
          onPrefillApplied={onPrefillApplied}
          onPreviewAttachment={handlePreview}
          onCancel={() => setFormMode(null)}
          onSubmitted={(next) => {
            onUpdated(next)
            setFormMode(null)
          }}
          onLedgerChange={onUpdated}
        />
      )}

      {ledger.returned_step === 'investigation' && (
        <p className="mt-3 text-[13px] text-[var(--color-error)]">
          调查报告已被退回：请补充调查记录或调查报告附件后，点击「提交审核」重新提交。
        </p>
      )}

      <Modal
        open={submitOpen}
        title="确认提交审核？"
        okText="确认提交"
        cancelText="取消"
        confirmLoading={submitting}
        onOk={() => void handleSubmitForReview()}
        onCancel={() => setSubmitOpen(false)}
        destroyOnHidden
      >
        <div className="flex flex-col gap-2">
          <p className="text-[13px] text-[var(--color-slate)]">
            已填写的调查记录将提交部门负责人审核，本次提交说明会记录在「审核记录」中。
          </p>
          <Input.TextArea
            rows={3}
            value={submitInfo}
            maxLength={500}
            showCount
            placeholder="提交信息（选填），如：已按退回意见补充根本原因分析"
            onChange={(event) => setSubmitInfo(event.target.value)}
          />
          {ledger.viewer_is_superuser && (
            <div>
              <p className="mb-1 text-[12px] text-[var(--color-slate)]">
                管理员代审原因（非调查人操作时必填）
              </p>
              <Input
                value={overrideReason}
                maxLength={200}
                allowClear
                placeholder="如：调查人休假，管理员代提交；将写入审计日志"
                onChange={(event) => setOverrideReason(event.target.value)}
              />
            </div>
          )}
        </div>
      </Modal>

      <AttachmentPreviewDrawer
        open={previewAttachment !== null}
        ledgerId={ledger.id}
        attachment={previewAttachment}
        frozen={commentsFrozen}
        onClose={closePreview}
        onCommentCountChange={() => undefined}
      />
    </SectionCard>
  )
}