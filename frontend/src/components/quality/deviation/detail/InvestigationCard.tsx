'use client'

import { useCallback, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { App, Button, Card, Empty, Popconfirm, Space, Timeline, Tooltip, Upload } from 'antd'
import { DeleteOutlined, EyeOutlined, MessageOutlined, UploadOutlined, WarningOutlined } from '@ant-design/icons'
import { deleteDeviationAttachment, uploadDeviationAttachment } from '@/actions/quality'
import { fetchDeviationAttachmentCommentSummary } from '@/lib/api/client/quality'
import type { DeviationAttachment, DeviationInvestigationRecord, DeviationLedgerDetail } from '@/types/quality'
import { PersonInline } from '../PersonInline'
import { AttachmentPreviewDrawer } from './AttachmentPreviewDrawer'
import { InvestigationRecordForm } from './InvestigationRecordForm'

interface InvestigationCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
}

/** 单文件上限 20MB，与后端保持一致 */
const MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024

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

/** 记录正文：不符合事项 → 根因 → 风险 → CAPA → 紧急措施 → 记录附件；旧纯文本记录降级为段落展示 */
function RecordBody({
  record,
  onPreview,
}: {
  record: DeviationInvestigationRecord
  onPreview: (attachment: DeviationAttachment) => void
}) {
  const capaRows = record.capa_proposals ?? []
  const recordAttachments = record.attachments ?? []
  const isStructured = Boolean(
    record.nonconformity_description ||
      record.root_cause_analysis ||
      record.risk_assessment ||
      record.urgent_measures ||
      capaRows.length,
  )
  if (!isStructured) {
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
      {sections.map((section) => (
        <div key={section.title}>
          <div className="text-[12px] font-medium text-[var(--color-slate)]">{section.title}</div>
          <p className="whitespace-pre-wrap break-words text-[13px] leading-5 text-[var(--color-ink)]">
            {section.text}
          </p>
        </div>
      ))}
      {capaRows.length > 0 && (
        <div>
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
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-[12px] text-[var(--color-slate)]">记录附件：</span>
          {recordAttachments.map((attachment) => (
            <Button
              key={attachment.file_id}
              type="link"
              size="small"
              className="!h-auto !px-0 !text-[12px]"
              onClick={() => onPreview(attachment)}
            >
              {attachment.file_name}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}

/** 调查记录：过程记录 + 调查文档（上传的文档在此呈现），提交后进入部门负责人审核 */
export function InvestigationCard({ ledger, onUpdated }: InvestigationCardProps) {
  const { message } = App.useApp()
  // 结构化调查表单：submit=提交调查（流转），append=追加记录（不流转），null=收起
  const [formMode, setFormMode] = useState<'submit' | 'append' | null>(null)
  const [uploading, setUploading] = useState(false)
  // 当前正在预览的附件：非空即打开预览抽屉（左文档 + 右批注）
  const [previewAttachment, setPreviewAttachment] = useState<DeviationAttachment | null>(null)
  // 抽屉内批注变化后的即时覆盖值，避免关闭再开详情才刷新角标
  const [commentOverrides, setCommentOverrides] = useState<Record<string, { open: number; total: number }>>({})

  const { data: commentSummary } = useQuery({
    queryKey: ['deviation-attachment-comment-summary', ledger.id],
    queryFn: () => fetchDeviationAttachmentCommentSummary(ledger.id),
    staleTime: 30_000,
  })

  const commentCounts = useMemo(() => {
    const merged: Record<string, { open: number; total: number }> = {}
    for (const item of commentSummary?.items ?? []) {
      merged[item.file_id] = { open: item.open_count ?? 0, total: item.total_count ?? 0 }
    }
    return { ...merged, ...commentOverrides }
  }, [commentSummary, commentOverrides])

  const handleCommentCountChange = useCallback((fileId: string, openCount: number, total: number) => {
    setCommentOverrides((prev) => ({ ...prev, [fileId]: { open: openCount, total } }))
  }, [])

  const handlePreview = useCallback((attachment: DeviationAttachment) => {
    setPreviewAttachment(attachment)
  }, [])

  const closePreview = useCallback(() => setPreviewAttachment(null), [])
  // 已关闭 / 已取消的偏差：批注只读存档
  const commentsFrozen = ledger.status === 'closed' || ledger.status === 'cancelled'

  const actions = ledger.allowed_actions ?? []
  const canInvestigate = actions.includes('investigate')
  const records = ledger.investigation_records ?? []
  const attachments = ledger.attachments ?? []
  // 调查人 / 上报人在调查中与审核阶段都可维护调查记录与文档（后端单一真源）
  const canEditInvestigation = ledger.can_edit_investigation === true
  // 已进入审核（不再有提交调查动作）时，展示「只追加不流转」的补录入口
  const canAppend = canEditInvestigation && !canInvestigate

  const handleUpload = async (file: File) => {
    if (file.size > MAX_ATTACHMENT_SIZE) {
      message.error(`单个文档不能超过 20MB（当前 ${formatSize(file.size)}）`)
      return
    }
    const formData = new FormData()
    formData.append('file', file)
    setUploading(true)
    const result = await uploadDeviationAttachment(ledger.id, formData)
    setUploading(false)
    if (result.code === 200 && result.data) {
      onUpdated(result.data)
      message.success('文档已上传')
    } else {
      message.error(result.message)
    }
  }

  const handleDelete = async (fileId: string) => {
    const result = await deleteDeviationAttachment(ledger.id, fileId)
    if (result.code === 200 && result.data) {
      onUpdated(result.data)
      message.success('文档已删除')
    } else {
      message.error(result.message)
    }
  }

  return (
    <Card
      id="investigation"
      size="small"
      title="调查记录"
      className="scroll-mt-6 shadow-sm"
      extra={
        <span className="text-[12px] text-[var(--color-stone)]">
          {records.length} 条记录 · {attachments.length} 份文档
        </span>
      }
    >
      {records.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无调查记录" />
      ) : (
        <Timeline
          className="mb-2"
          items={records.map((record, index) => ({
            key: index,
            color: 'blue',
            content: (
              <div className="flex flex-col gap-1">
                <span className="flex flex-wrap items-center gap-1 text-[12px] text-[var(--color-slate)]">
                  <PersonInline
                    person={{ id: record.author_id, name: record.author_name, avatar_url: record.author_avatar }}
                    avatarSize={20}
                  />
                  <span>
                    ·{' '}
                    {record.create_time
                      ? new Date(record.create_time).toLocaleString('zh-CN', { hour12: false })
                      : '-'}
                  </span>
                </span>
                <RecordBody record={record} onPreview={handlePreview} />
              </div>
            ),
          }))}
        />
      )}

      {(canInvestigate || canAppend) && formMode === null && (
        <div className="mt-3 flex flex-col gap-2 border-t border-[var(--color-hairline)] pt-3">
          <span className="text-[12px] text-[var(--color-stone)]">
            {canInvestigate
              ? '填写结构化调查报告（不符合事项 / 根因 / 风险 / CAPA / 紧急措施），提交后进入部门负责人审核。'
              : '流程已进入审核，此处补充调查记录仅追加内容，不会改变流程状态。'}
          </span>
          <div className="flex flex-wrap justify-end gap-2">
            <Button type={canInvestigate ? 'primary' : 'default'} onClick={() => setFormMode(canInvestigate ? 'submit' : 'append')}>
              {canInvestigate ? '填写调查报告' : '追加调查记录'}
            </Button>
          </div>
        </div>
      )}

      {formMode && (canInvestigate || canAppend) && (
        <InvestigationRecordForm
          key={formMode}
          ledger={ledger}
          mode={formMode}
          onCancel={() => setFormMode(null)}
          onSubmitted={(next) => {
            onUpdated(next)
            setFormMode(null)
          }}
          onLedgerChange={onUpdated}
        />
      )}

      <div className="mt-4 border-t border-[var(--color-hairline)] pt-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-[13px] font-semibold text-[var(--color-ink)]">调查文档</h3>
          {canEditInvestigation && (
            <Upload
              showUploadList={false}
              beforeUpload={(file) => {
                void handleUpload(file)
                return false
              }}
            >
              <Button size="small" icon={<UploadOutlined />} loading={uploading}>
                上传文档
              </Button>
            </Upload>
          )}
        </div>
        {attachments.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档" />
        ) : (
          <div className="flex flex-col divide-y divide-[var(--color-hairline-soft)]">
            {attachments.map((attachment) => {
              const openComments = commentCounts[attachment.file_id]?.open ?? 0
              return (
                <div key={attachment.file_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <div className="min-w-0">
                    <p className="flex items-center gap-1.5 text-[13px] text-[var(--color-ink)]">
                      <span className="truncate">{attachment.file_name}</span>
                      {openComments > 0 && (
                        <Tooltip title={`${openComments} 条待处理批注`}>
                          <span className="flex shrink-0 items-center gap-0.5 rounded-full bg-[#f1efff] px-1.5 py-0.5 text-[11px] font-medium text-[var(--color-primary,#5645d4)]">
                            <MessageOutlined className="text-[10px]" />
                            {openComments}
                          </span>
                        </Tooltip>
                      )}
                    </p>
                    <span className="flex flex-wrap items-center gap-1 text-[12px] text-[var(--color-stone)]">
                      <span>{formatSize(attachment.size)} ·</span>
                      <PersonInline
                        person={{
                          id: attachment.uploaded_by,
                          name: attachment.uploaded_by_name,
                          avatar_url: attachment.uploaded_by_avatar,
                        }}
                        avatarSize={20}
                      />
                      <span>· {formatTime(attachment.uploaded_at)}</span>
                    </span>
                  </div>
                  <Space size={4} className="shrink-0">
                    <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handlePreview(attachment)}>
                      预览
                    </Button>
                    <Button type="link" size="small" href={attachmentUrl(ledger.id, attachment.file_id)}>
                      下载
                    </Button>
                    {canEditInvestigation && (
                      <Popconfirm title="删除该文档？" onConfirm={() => handleDelete(attachment.file_id)}>
                        <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                          删除
                        </Button>
                      </Popconfirm>
                    )}
                  </Space>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {ledger.status === 'returned' && ledger.returned_step === 'investigation' && (
        <p className="mt-3 text-[13px] text-[var(--color-error)]">
          调查报告已被退回：请先补充调查报告内容，再到「审核与流转」区重新提交。
        </p>
      )}

      <AttachmentPreviewDrawer
        open={previewAttachment !== null}
        ledgerId={ledger.id}
        attachment={previewAttachment}
        frozen={commentsFrozen}
        onClose={closePreview}
        onCommentCountChange={handleCommentCountChange}
      />
    </Card>
  )
}