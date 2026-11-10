'use client'

import { Button, Modal } from 'antd'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  open: boolean
  title: string
  /** Markdown 原文；空内容按占位提示处理 */
  markdown: string
  onClose: () => void
  width?: number
}

/** 表格与长文本的通用样式：与研发模块正文保持同一套字号与行高 */
const CONTENT_STYLE = {
  fontSize: 13,
  lineHeight: 1.75,
  color: '#1F2329',
} as const

/**
 * Markdown 预览弹层：对照表、交付物正文都用它渲染，
 * 避免把 Markdown 原文直接塞进 TextArea / 纯文本区域。
 */
export function MarkdownPreviewModal({ open, title, markdown, onClose, width = 860 }: Props) {
  const empty = !markdown.trim()

  return (
    <Modal
      open={open}
      title={title}
      width={width}
      onCancel={onClose}
      destroyOnHidden
      footer={<Button onClick={onClose}>关闭</Button>}
    >
      <div
        style={{
          maxHeight: '70vh',
          overflow: 'auto',
          background: '#f5f6f8',
          padding: 16,
          borderRadius: 6,
        }}
      >
        <div
          style={{
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: 4,
            boxShadow: '0 1px 2px rgba(16, 24, 40, 0.06)',
            padding: '20px 24px',
            ...CONTENT_STYLE,
          }}
        >
          {empty ? (
            <span style={{ color: '#8c8c8c' }}>暂无内容</span>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: (props) => <h1 style={{ fontSize: 20, fontWeight: 600, margin: '16px 0 8px' }} {...props} />,
                h2: (props) => <h2 style={{ fontSize: 16, fontWeight: 600, margin: '16px 0 8px' }} {...props} />,
                h3: (props) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: '12px 0 6px' }} {...props} />,
                p: (props) => <p style={{ margin: '8px 0' }} {...props} />,
                ul: (props) => <ul style={{ paddingLeft: 20, margin: '8px 0' }} {...props} />,
                ol: (props) => <ol style={{ paddingLeft: 20, margin: '8px 0' }} {...props} />,
                li: (props) => <li style={{ margin: '4px 0' }} {...props} />,
                code: (props) => (
                  <code
                    style={{ background: '#f5f6f8', borderRadius: 3, padding: '1px 4px', fontSize: 12 }}
                    {...props}
                  />
                ),
                table: (props) => (
                  <table
                    style={{ borderCollapse: 'collapse', width: '100%', margin: '12px 0', fontSize: 12 }}
                    {...props}
                  />
                ),
                th: (props) => (
                  <th
                    style={{
                      border: '1px solid #e5e7eb',
                      background: '#fafafa',
                      padding: '6px 8px',
                      textAlign: 'left',
                      fontWeight: 600,
                    }}
                    {...props}
                  />
                ),
                td: (props) => (
                  <td style={{ border: '1px solid #e5e7eb', padding: '6px 8px' }} {...props} />
                ),
              }}
            >
              {markdown}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </Modal>
  )
}