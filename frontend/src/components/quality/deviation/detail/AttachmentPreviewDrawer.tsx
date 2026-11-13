'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Drawer, Tabs, Tooltip } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import type { DeviationAttachment } from '@/types/quality'
import { AttachmentCommentPanel } from './AttachmentCommentPanel'
import { DocumentViewer } from './DocumentViewer'

interface AttachmentPreviewDrawerProps {
  open: boolean
  ledgerId: string
  attachment: DeviationAttachment | null
  /** 偏差已关闭 / 已取消：批注只读 */
  frozen: boolean
  onClose: () => void
  onCommentCountChange?: (fileId: string, openCount: number, total: number) => void
}

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|bmp)$/i

function describeType(fileName: string): string {
  const lower = fileName.toLowerCase()
  if (lower.endsWith('.pdf')) return 'PDF'
  if (lower.endsWith('.doc') || lower.endsWith('.docx')) return 'Word'
  if (IMAGE_EXT.test(lower)) return '图片'
  return '文件'
}

function useNarrowViewport(): boolean {
  const [narrow, setNarrow] = useState(false)
  useEffect(() => {
    const query = window.matchMedia('(max-width: 1023px)')
    const update = () => setNarrow(query.matches)
    update()
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])
  return narrow
}

/**
 * 附件预览抽屉：左侧文档渲染，右侧文档批注。
 *
 * 批注与流程审核意见（review_opinions）完全分离，仅用于文档评审协作。
 */
export function AttachmentPreviewDrawer({
  open,
  ledgerId,
  attachment,
  frozen,
  onClose,
  onCommentCountChange,
}: AttachmentPreviewDrawerProps) {
  const narrow = useNarrowViewport()
  const [pageInfo, setPageInfo] = useState<{ page: number; count: number }>({ page: 1, count: 0 })
  const [mobileTab, setMobileTab] = useState<'document' | 'comments'>('document')

  const handleActivePageChange = useCallback((page: number, count: number) => {
    setPageInfo((prev) => (prev.page === page && prev.count === count ? prev : { page, count }))
  }, [])

  const fileId = attachment?.file_id ?? ''
  const fileName = attachment?.file_name ?? ''

  const previewUrl = useMemo(
    () => `/api/v1/quality/deviation/ledger/${ledgerId}/attachments/${fileId}/preview`,
    [fileId, ledgerId],
  )
  const downloadUrl = useMemo(
    () => `/api/v1/quality/deviation/ledger/${ledgerId}/attachments/${fileId}/download`,
    [fileId, ledgerId],
  )

  const handleCountChange = useCallback(
    (openCount: number, total: number) => {
      if (fileId) onCommentCountChange?.(fileId, openCount, total)
    },
    [fileId, onCommentCountChange],
  )

  const viewer = attachment ? (
    <DocumentViewer
      key={`${fileId}`}
      previewUrl={previewUrl}
      downloadUrl={downloadUrl}
      fileName={fileName}
      onActivePageChange={handleActivePageChange}
    />
  ) : null

  const panel = attachment ? (
    <AttachmentCommentPanel
      key={`comments-${fileId}`}
      ledgerId={ledgerId}
      fileId={fileId}
      activePage={pageInfo.count > 0 ? pageInfo.page : 0}
      frozen={frozen}
      onCountChange={handleCountChange}
    />
  ) : null

  return (
    <Drawer
      open={open}
      onClose={onClose}
      size={narrow ? '100%' : 'min(1180px, 96vw)'}
      placement="right"
      destroyOnHidden
      closable={false}
      styles={{ body: { padding: 0, height: '100%', overflow: 'hidden' } }}
      title={
        <div className="flex items-center gap-3 pr-2">
          <span className="max-w-[46%] truncate text-[15px] font-semibold text-[var(--color-ink,#1a1a1a)]">
            {fileName || '文档预览'}
          </span>
          <span className="rounded bg-[#f1efec] px-1.5 py-0.5 text-[11px] text-[var(--color-slate,#5d5b54)]">
            {describeType(fileName)}
          </span>
          {pageInfo.count > 0 && (
            <Tooltip title="左侧当前浏览页，新增批注会自动带上该页码">
              <span className="text-[12px] text-[var(--color-stone,#a4a097)]">
                {pageInfo.page} / {pageInfo.count}
              </span>
            </Tooltip>
          )}
          <span className="ml-auto flex items-center gap-2">
            <a href={downloadUrl} target="_blank" rel="noreferrer">
              <Button size="small" icon={<DownloadOutlined />}>
                下载
              </Button>
            </a>
            <Button size="small" type="text" onClick={onClose}>
              关闭
            </Button>
          </span>
        </div>
      }
    >
      {narrow ? (
        <Tabs
          activeKey={mobileTab}
          onChange={(key) => setMobileTab(key as 'document' | 'comments')}
          className="h-full px-3 [&_.ant-tabs-content]:h-full"
          items={[
            { key: 'document', label: '文档', children: <div className="h-[calc(100vh-140px)]">{viewer}</div> },
            {
              key: 'comments',
              label: '批注',
              children: <div className="h-[calc(100vh-140px)]">{panel}</div>,
            },
          ]}
        />
      ) : (
        <div className="flex h-full min-h-0">
          <div className="flex min-w-0 flex-1 flex-col">
            <div className="min-h-0 flex-1">{viewer}</div>
          </div>
          <div className="w-[320px] shrink-0 border-l border-[var(--color-hairline,#e5e3df)]">{panel}</div>
        </div>
      )}
    </Drawer>
  )
}

export default AttachmentPreviewDrawer