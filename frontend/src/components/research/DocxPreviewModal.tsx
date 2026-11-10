'use client'

import { useEffect, useRef, useState } from 'react'
import { Button, Modal, Skeleton, Tag } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { useDocxPreview } from './useDocxPreview'

interface Props {
  open: boolean
  /** 弹层标题，通常是报告名或交付物名 */
  title: string
  /** 版本/来源标签，如「AI 初稿」「人工重渲」 */
  versionLabel?: string
  /** 打开时按需拉取文档字节；失败时弹层内展示错误态，不阻断页面 */
  loadBlob: () => Promise<Blob>
  /** 底部下载入口；不传则只提供关闭 */
  onDownload?: () => void
  onClose: () => void
  /** 弹层宽度，默认 960 */
  width?: number
}

/**
 * Word 预览弹层：白纸页 + 浅灰底，按 docx 原版式渲染。
 * 报告详情、交付物向导、交付物附件都复用它，避免每个入口各写一套 Modal。
 */
export function DocxPreviewModal({
  open,
  title,
  versionLabel,
  loadBlob,
  onDownload,
  onClose,
  width = 960,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const { loading, error, renderDocx, reset } = useDocxPreview()
  const [fetchError, setFetchError] = useState<string | null>(null)

  // loadBlob 多半是内联箭头函数，存进 ref 避免它变化导致 effect 反复重跑、反复拉文档
  const loadBlobRef = useRef(loadBlob)
  loadBlobRef.current = loadBlob

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setFetchError(null)
    reset()
    // 等弹层真正挂载后再渲染：docx-preview 需要容器有尺寸，setTimeout(0) 是既有的防竞态写法
    const timer = window.setTimeout(() => {
      loadBlobRef
        .current()
        .then((blob) => {
          if (cancelled) return
          return renderDocx(blob, containerRef.current)
        })
        .catch((e: unknown) => {
          if (!cancelled) setFetchError(e instanceof Error ? e.message : '文档加载失败')
        })
    }, 0)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      reset()
    }
  }, [open, renderDocx, reset])

  const message = fetchError ?? error

  return (
    <Modal
      open={open}
      title={(
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <span>{title}</span>
          {versionLabel ? <Tag color="blue" style={{ marginInlineEnd: 0 }}>{versionLabel}</Tag> : null}
        </span>
      )}
      width={width}
      onCancel={onClose}
      destroyOnHidden
      footer={(
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          {onDownload ? (
            <Button icon={<DownloadOutlined />} onClick={onDownload}>
              下载 Word
            </Button>
          ) : null}
          <Button onClick={onClose}>关闭</Button>
        </div>
      )}
    >
      {message ? (
        <div style={{ color: '#ff4d4f', padding: '8px 0', fontSize: 12 }}>{message}</div>
      ) : null}
      {loading ? (
        <div style={{ padding: '8px 0' }}>
          <Skeleton active paragraph={{ rows: 8 }} title={false} />
        </div>
      ) : null}
      <div
        style={{
          maxHeight: '68vh',
          overflow: 'auto',
          background: '#f5f6f8',
          padding: 16,
          borderRadius: 6,
        }}
      >
        <div
          ref={containerRef}
          style={{
            background: '#fff',
            minHeight: 200,
            padding: '8px 0',
            border: '1px solid #e5e7eb',
            borderRadius: 4,
            boxShadow: '0 1px 2px rgba(16, 24, 40, 0.06)',
          }}
        />
      </div>
    </Modal>
  )
}