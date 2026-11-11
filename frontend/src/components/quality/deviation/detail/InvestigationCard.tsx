'use client'

import { useState } from 'react'
import { App, Button, Card, Empty, Input, Modal, Popconfirm, Space, Timeline, Upload } from 'antd'
import { DeleteOutlined, EyeOutlined, UploadOutlined } from '@ant-design/icons'
import {
  deleteDeviationAttachment,
  submitDeviationInvestigation,
  uploadDeviationAttachment,
} from '@/actions/quality'
import type { DeviationAttachment, DeviationLedgerDetail } from '@/types/quality'
import { PersonInline } from '../PersonInline'

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

/** 调查记录：过程记录 + 调查文档（上传的文档在此呈现），提交后进入部门负责人审核 */
export function InvestigationCard({ ledger, onUpdated }: InvestigationCardProps) {
  const { message } = App.useApp()
  const [content, setContent] = useState('')
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState<{ url: string; type: string; name: string } | null>(null)

  const actions = ledger.allowed_actions ?? []
  const canInvestigate = actions.includes('investigate')
  const records = ledger.investigation_records ?? []
  const attachments = ledger.attachments ?? []
  const canEditAttachments = ledger.can_operate && ledger.current_step === 'investigation'

  const handleSubmit = async () => {
    if (!content.trim()) {
      message.warning('请填写调查内容')
      return
    }
    setBusy(true)
    const result = await submitDeviationInvestigation(ledger.id, { content: content.trim() })
    setBusy(false)
    if (result.code === 200 && result.data) {
      setContent('')
      onUpdated(result.data)
      message.success('调查已提交，进入部门负责人审核')
    } else {
      message.error(result.message)
    }
  }

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

  const handlePreview = async (attachment: DeviationAttachment) => {
    try {
      const response = await fetch(attachmentUrl(ledger.id, attachment.file_id))
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const blob = await response.blob()
      setPreview({
        url: URL.createObjectURL(blob),
        type: attachment.content_type || blob.type,
        name: attachment.file_name,
      })
    } catch (error) {
      console.error('调查文档预览失败', error)
      message.error('文档预览失败，请改用下载')
    }
  }

  const closePreview = () => {
    if (preview) URL.revokeObjectURL(preview.url)
    setPreview(null)
  }

  return (
    <Card
      id="investigation"
      size="small"
      title="调查记录"
      className="scroll-mt-40 shadow-sm"
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
                <p className="whitespace-pre-wrap break-words text-[13px] leading-5 text-[var(--color-ink)]">
                  {record.content}
                </p>
              </div>
            ),
          }))}
        />
      )}

      {canInvestigate && (
        <div className="mt-3 flex flex-col gap-2 border-t border-[var(--color-hairline)] pt-3">
          <Input.TextArea
            rows={4}
            value={content}
            maxLength={4000}
            showCount
            placeholder="填写调查过程与结论（不符合项、根因、风险、紧急措施等），提交后进入部门负责人审核"
            onChange={(event) => setContent(event.target.value)}
          />
          <div className="flex flex-wrap justify-end gap-2">
            <Button type="primary" loading={busy} onClick={handleSubmit}>
              提交调查
            </Button>
          </div>
        </div>
      )}

      <div className="mt-4 border-t border-[var(--color-hairline)] pt-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-[13px] font-semibold text-[var(--color-ink)]">调查文档</h3>
          {canEditAttachments && (
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
            {attachments.map((attachment) => (
              <div key={attachment.file_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <div className="min-w-0">
                  <p className="truncate text-[13px] text-[var(--color-ink)]">{attachment.file_name}</p>
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
                  <Button
                    type="link"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => handlePreview(attachment)}
                  >
                    预览
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    href={attachmentUrl(ledger.id, attachment.file_id)}
                  >
                    下载
                  </Button>
                  {canEditAttachments && (
                    <Popconfirm title="删除该文档？" onConfirm={() => handleDelete(attachment.file_id)}>
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  )}
                </Space>
              </div>
            ))}
          </div>
        )}
      </div>

      {ledger.status === 'returned' && ledger.returned_step === 'investigation' && (
        <p className="mt-3 text-[13px] text-[var(--color-error)]">
          调查报告已被退回：请先补充调查报告内容，再到「审核与流转」区重新提交。
        </p>
      )}

      <Modal
        open={preview !== null}
        title={preview?.name}
        footer={null}
        width={880}
        style={{ maxWidth: 'calc(100vw - 24px)' }}
        onCancel={closePreview}
      >
        {preview && preview.type.startsWith('image/') && (
          // eslint-disable-next-line @next/next/no-img-element -- 附件是鉴权后的 blob URL，无法走 next/image 优化
          <img src={preview.url} alt={preview.name} className="mx-auto max-h-[70vh] w-auto" />
        )}
        {preview && preview.type === 'application/pdf' && (
          <iframe src={preview.url} title={preview.name} className="h-[70vh] w-full" />
        )}
        {preview && !preview.type.startsWith('image/') && preview.type !== 'application/pdf' && (
          <p className="py-6 text-center text-[13px] text-[var(--color-slate)]">
            该文件类型不支持在线预览，请使用「下载」查看。
          </p>
        )}
      </Modal>
    </Card>
  )
}