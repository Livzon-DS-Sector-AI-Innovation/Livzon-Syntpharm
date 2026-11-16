'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { App, Avatar, Button, Empty, Input, Popconfirm, Segmented, Spin, Tooltip } from 'antd'
import { CheckCircleOutlined, DeleteOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons'
import {
  createDeviationAttachmentComment,
  deleteDeviationAttachmentComment,
  updateDeviationAttachmentComment,
} from '@/actions/quality'
import { usePermission } from '@/hooks/usePermission'
import { fetchDeviationAttachmentComments } from '@/lib/api/client/quality'
import type { DeviationAttachmentComment } from '@/types/quality'

interface AttachmentCommentPanelProps {
  ledgerId: string
  fileId: string
  /** 左侧预览当前页，作为新增批注的默认页码 */
  activePage: number
  /** 偏差已关闭 / 已取消：批注只读 */
  frozen: boolean
  onCountChange?: (openCount: number, total: number) => void
}

type CommentFilter = 'all' | 'open'

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function CommentCard({
  comment,
  canDelete,
  frozen,
  onToggleStatus,
  onDelete,
}: {
  comment: DeviationAttachmentComment
  canDelete: boolean
  frozen: boolean
  onToggleStatus: (comment: DeviationAttachmentComment) => void
  onDelete: (comment: DeviationAttachmentComment) => void
}) {
  const resolved = comment.status === 'resolved'
  return (
    <div
      className={`group relative mb-2 rounded-md border border-transparent bg-[var(--color-surface-soft,#fafaf9)] px-3 py-2.5 transition-all duration-150 hover:border-[var(--color-hairline,#e5e3df)] hover:bg-white hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)] ${
        resolved ? 'opacity-70' : ''
      }`}
    >
      <span
        className={`absolute left-0 top-2.5 h-4 w-[2px] rounded-full transition-all duration-150 ${
          resolved ? 'bg-[var(--color-success,#1aae39)]' : 'bg-[var(--color-primary,#5645d4)]'
        }`}
      />
      <div className="flex items-center gap-2">
        <Avatar size={24} src={comment.author_avatar || undefined} className="shrink-0 bg-[#5645d4] text-[11px]">
          {(comment.author_name || '?').slice(0, 1)}
        </Avatar>
        <span className="text-[13px] font-medium text-[var(--color-ink,#1a1a1a)]">
          {comment.author_name || '未知用户'}
        </span>
        <span className="text-[12px] text-[var(--color-stone,#a4a097)]">{formatTime(comment.created_at)}</span>
        <span className="ml-auto flex items-center gap-1">
          {comment.page_no ? (
            <span className="rounded bg-[#f1efec] px-1.5 py-0.5 text-[11px] text-[var(--color-slate,#5d5b54)]">
              P{comment.page_no}
            </span>
          ) : null}
          {resolved ? (
            <span className="rounded bg-[#eaf7ec] px-1.5 py-0.5 text-[11px] text-[#1aae39]">已解决</span>
          ) : (
            <span className="rounded border border-[#f0c48a] px-1.5 py-0.5 text-[11px] text-[#dd5b00]">待处理</span>
          )}
        </span>
      </div>
      <p
        className={`mt-1.5 whitespace-pre-wrap break-words pl-8 text-[13px] leading-[1.6] ${
          resolved ? 'text-[var(--color-stone,#a4a097)]' : 'text-[var(--color-slate,#5d5b54)]'
        }`}
      >
        {comment.content}
      </p>
      {!frozen && (
        <div className="mt-1 flex items-center justify-end gap-1 opacity-0 transition-opacity duration-150 group-hover:opacity-100 focus-within:opacity-100">
          <Button type="text" size="small" onClick={() => onToggleStatus(comment)} className="!text-[12px]">
            {resolved ? <ReloadOutlined /> : <CheckCircleOutlined />}
            <span className="ml-1">{resolved ? '重新打开' : '标记已解决'}</span>
          </Button>
          {canDelete && (
            <Popconfirm
              title="删除这条批注？"
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
              onConfirm={() => onDelete(comment)}
            >
              <Button type="text" size="small" danger icon={<DeleteOutlined />} className="!text-[12px]">
                删除
              </Button>
            </Popconfirm>
          )}
        </div>
      )}
    </div>
  )
}

/** 附件批注侧栏：列表 + 状态流转 + 新增输入。 */
export function AttachmentCommentPanel({
  ledgerId,
  fileId,
  activePage,
  frozen,
  onCountChange,
}: AttachmentCommentPanelProps) {
  const { message } = App.useApp()
  const { user, isSuperuser } = usePermission()
  const [filter, setFilter] = useState<CommentFilter>('all')
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  // 批注默认挂在左侧正在浏览的页，跟随预览滚动自动更新
  const pageNo = activePage > 0 ? activePage : null

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['deviation-attachment-comments', ledgerId, fileId],
    queryFn: () => fetchDeviationAttachmentComments(ledgerId, fileId),
    staleTime: 10_000,
  })

  const comments = useMemo(() => data?.items ?? [], [data])
  const openCount = data?.open_count ?? 0
  const total = data?.total ?? comments.length

  useEffect(() => {
    onCountChange?.(openCount, total)
  }, [onCountChange, openCount, total])

  const visibleComments = useMemo(
    () => (filter === 'open' ? comments.filter((item) => item.status === 'open') : comments),
    [comments, filter],
  )

  // 删除仅限作者本人或超管，与后端校验一致
  const currentUserId = user?.id
  const canDelete = (comment: DeviationAttachmentComment) =>
    isSuperuser || (!!currentUserId && comment.author_id === currentUserId)

  const handleSubmit = useCallback(async () => {
    const content = draft.trim()
    if (!content || pending || frozen) return
    setPending(true)
    const result = await createDeviationAttachmentComment(ledgerId, fileId, {
      content,
      page_no: pageNo,
    })
    setPending(false)
    if (result.code !== 200 || !result.data) {
      message.error(result.message || '批注提交失败')
      return
    }
    setDraft('')
    message.success('批注已添加')
    await refetch()
  }, [draft, fileId, frozen, ledgerId, message, pageNo, pending, refetch])

  const handleToggleStatus = useCallback(
    async (comment: DeviationAttachmentComment) => {
      const result = await updateDeviationAttachmentComment(ledgerId, fileId, comment.id, {
        status: comment.status === 'open' ? 'resolved' : 'open',
      })
      if (result.code !== 200) {
        message.error(result.message || '批注更新失败')
        return
      }
      await refetch()
    },
    [fileId, ledgerId, message, refetch],
  )

  const handleDelete = useCallback(
    async (comment: DeviationAttachmentComment) => {
      const result = await deleteDeviationAttachmentComment(ledgerId, fileId, comment.id)
      if (result.code !== 200) {
        message.error(result.message || '批注删除失败')
        return
      }
      message.success('批注已删除')
      await refetch()
    },
    [fileId, ledgerId, message, refetch],
  )

  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-white">
      <div className="flex items-center justify-between border-b border-[var(--color-hairline,#e5e3df)] px-4 py-3">
        <div className="flex items-baseline gap-2">
          <span className="text-[15px] font-semibold text-[var(--color-ink,#1a1a1a)]">文档批注</span>
          <span className="text-[12px] text-[var(--color-stone,#a4a097)]">
            待处理 {openCount} · 全部 {total}
          </span>
        </div>
        <Segmented<CommentFilter>
          size="small"
          value={filter}
          onChange={setFilter}
          options={[
            { label: '全部', value: 'all' },
            { label: '待处理', value: 'open' },
          ]}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {isLoading ? (
          <div className="flex h-32 items-center justify-center">
            <Spin size="small" />
          </div>
        ) : isError ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span className="text-[12px]">批注加载失败</span>}
          >
            <Button size="small" onClick={() => void refetch()}>
              重试
            </Button>
          </Empty>
        ) : visibleComments.length === 0 ? (
          <div className="px-4 py-10 text-center">
            <div className="text-[13px] text-[var(--color-slate,#5d5b54)]">
              {filter === 'open' ? '没有待处理的批注' : '还没有批注'}
            </div>
            <div className="mt-1 text-[12px] leading-relaxed text-[var(--color-stone,#a4a097)]">
              看到需要修改的地方，在下方输入意见即可，批注会挂在当前附件上并默认记录页码
            </div>
          </div>
        ) : (
          visibleComments.map((comment) => (
            <CommentCard
              key={comment.id}
              comment={comment}
              canDelete={canDelete(comment)}
              frozen={frozen}
              onToggleStatus={handleToggleStatus}
              onDelete={handleDelete}
            />
          ))
        )}
      </div>

      <div className="border-t border-[var(--color-hairline,#e5e3df)] px-3 py-3">
        {frozen ? (
          <div className="rounded-md bg-[var(--color-surface-soft,#fafaf9)] px-3 py-3 text-center text-[12px] text-[var(--color-stone,#a4a097)]">
            偏差已关闭，批注仅供查阅
          </div>
        ) : (
          <>
            <Input.TextArea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="输入批注，Ctrl/⌘ + Enter 快速提交"
              autoSize={{ minRows: 3, maxRows: 6 }}
              maxLength={2000}
              showCount
              disabled={pending}
              onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                  event.preventDefault()
                  void handleSubmit()
                }
              }}
            />
            <div className="mt-2 flex items-center justify-between">
              <Tooltip title="批注默认记录左侧当前浏览页">
                <span className="text-[12px] text-[var(--color-stone,#a4a097)]">
                  {pageNo ? `关联第 ${pageNo} 页` : '不关联页码'}
                </span>
              </Tooltip>
              <Button
                type="primary"
                size="small"
                icon={<SendOutlined />}
                loading={pending}
                disabled={!draft.trim()}
                onClick={() => void handleSubmit()}
              >
                添加批注
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default AttachmentCommentPanel