'use client'

import { useState } from 'react'
import { Alert, App, Button, Modal, Space, Tag, Typography, Upload } from 'antd'
import { InboxOutlined } from '@ant-design/icons'

import { applySourceReplace, previewSourceReplace } from '@/actions/agent/ppt-video'
import {
  DIFF_STATUS_LABEL,
  type DiffStatus,
  type SourceApplyResult,
  type SourceDiffEntry,
  type SourceDiffSummary,
} from '@/types/agent/ppt-video'

interface Props {
  open: boolean
  projectId: string
  onClose: () => void
  onApplied: (result: SourceApplyResult) => void
}

const STATUS_COLOR: Record<DiffStatus, string> = {
  unchanged: 'default',
  changed: 'orange',
  added: 'green',
  removed: 'red',
}

/** 分组顺序：先说保留了多少，再说要动哪些 */
const GROUPS: DiffStatus[] = ['unchanged', 'changed', 'added', 'removed']

const GROUP_HINT: Record<DiffStatus, string> = {
  unchanged: '讲稿与音频原样保留，不重新合成',
  changed: '页内容变了，旧讲稿标记待重写',
  added: '新页，需要补讲稿',
  removed: '这些页会从项目中移除',
}

function pageLabel(entry: SourceDiffEntry): string {
  if (entry.status === 'added') return `新第 ${entry.new_index ?? '-'} 页`
  if (entry.status === 'removed') return `原第 ${entry.old_index ?? '-'} 页`
  if (entry.old_index && entry.new_index && entry.old_index !== entry.new_index) {
    return `第 ${entry.old_index} → ${entry.new_index} 页`
  }
  return `第 ${entry.old_index ?? entry.new_index ?? '-'} 页`
}

/**
 * 换源：先比对、再应用。
 *
 * 比对阶段不改任何数据；应用后未变页的讲稿与音频保留，只有变更页与新增页进重写队列。
 */
export default function SourceReplaceModal({ open, projectId, onClose, onApplied }: Props) {
  const { message } = App.useApp()
  const [diff, setDiff] = useState<SourceDiffSummary | null>(null)
  const [filename, setFilename] = useState('')
  const [busy, setBusy] = useState(false)
  const [applying, setApplying] = useState(false)

  const reset = () => {
    setDiff(null)
    setFilename('')
    setBusy(false)
    setApplying(false)
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const handlePick = async (file: File) => {
    setBusy(true)
    const result = await previewSourceReplace(projectId, file)
    setBusy(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    setFilename(file.name)
    setDiff(result.data)
  }

  const handleApply = async () => {
    setApplying(true)
    const result = await applySourceReplace(projectId, true)
    setApplying(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    message.success(result.message)
    onApplied(result.data)
    handleClose()
  }

  const entries = diff?.entries ?? []
  const byStatus = (status: DiffStatus) => entries.filter((entry) => entry.status === status)

  return (
    <Modal
      open={open}
      title="更换 PPT 源文件"
      width={720}
      onCancel={handleClose}
      destroyOnHidden
      footer={
        <Space className="w-full justify-between">
          <Typography.Text type="secondary" className="text-[12px]">
            未变页的讲稿与音频会保留
          </Typography.Text>
          <Space>
            <Button onClick={handleClose}>取消</Button>
            <Button
              type="primary"
              loading={applying}
              disabled={!diff?.has_changes || busy}
              onClick={handleApply}
            >
              应用并重写变更页
            </Button>
          </Space>
        </Space>
      }
    >
      <div className="flex flex-col gap-3">
        {!diff ? (
          <Upload.Dragger
            accept=".ppt,.pptx"
            multiple={false}
            showUploadList={false}
            disabled={busy}
            beforeUpload={(file) => {
              void handlePick(file)
              return false
            }}
            className="!bg-[#FAFAF9]"
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined className="!text-[#5645D4]" />
            </p>
            <p className="ant-upload-text">点击或拖入新的 PPT 文件</p>
            <p className="ant-upload-hint">只做比对，不会改动现有讲稿与成片</p>
          </Upload.Dragger>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-[#F4F1FE] px-3.5 py-2.5">
              <span className="text-[13px] text-[#37352F]">
                {diff.old_count} 页 → <b>{diff.new_count} 页</b>，
                <span className="text-[#5645D4]">{diff.unchanged} 页保留</span>
              </span>
              <Typography.Text type="secondary" className="text-[11px]">
                {filename}
              </Typography.Text>
            </div>

            {!diff.has_changes && (
              <Alert type="success" showIcon message="页序列与当前完全一致，无需换源" />
            )}

            <div className="flex max-h-[46vh] flex-col gap-3 overflow-y-auto pr-1">
              {GROUPS.map((status) => {
                const rows = byStatus(status)
                if (!rows.length) return null
                return (
                  <div key={status}>
                    <div className="mb-1.5 flex items-center gap-2">
                      <Tag color={STATUS_COLOR[status]} className="!m-0">
                        {DIFF_STATUS_LABEL[status]} {rows.length}
                      </Tag>
                      <Typography.Text type="secondary" className="text-[11px]">
                        {GROUP_HINT[status]}
                      </Typography.Text>
                    </div>
                    <div className="overflow-hidden rounded-lg border border-[#E5E3DF] bg-white">
                      {rows.map((entry) => (
                        <div
                          key={`${status}-${entry.old_index ?? 'n'}-${entry.new_index ?? 'n'}`}
                          className="flex items-center gap-2 border-b border-[#F0EEEB] px-3 py-2 last:border-b-0"
                        >
                          <span className="w-[92px] shrink-0 font-mono text-[11px] text-[#A4A097]">
                            {pageLabel(entry)}
                          </span>
                          <span className="min-w-0 flex-1 truncate text-[12px] text-[#37352F]">
                            {entry.title || '（无标题）'}
                          </span>
                          <Tag color={STATUS_COLOR[status]} className="!m-0 !text-[11px]">
                            {DIFF_STATUS_LABEL[status]}
                          </Tag>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>

            <Button size="small" type="link" className="!px-0" onClick={reset}>
              换一个文件重新比对
            </Button>
          </>
        )}
      </div>
    </Modal>
  )
}