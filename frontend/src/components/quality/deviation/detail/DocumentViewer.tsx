'use client'

import { useEffect, useRef, useState } from 'react'
import { Button, Empty, Spin } from 'antd'
import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons'

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|bmp)$/i

type PreviewKind = 'pdf' | 'docx' | 'image' | 'unsupported'
type ViewState = 'loading' | 'ready' | 'error' | 'unsupported'

export interface DocumentViewerProps {
  previewUrl: string
  downloadUrl: string
  fileName: string
  /** 滚动时回传当前浏览页，用于批注默认页码 */
  onActivePageChange?: (page: number, pageCount: number) => void
}

function detectKind(fileName: string): PreviewKind {
  const lower = fileName.toLowerCase()
  if (IMAGE_EXT.test(lower)) return 'image'
  if (lower.endsWith('.pdf')) return 'pdf'
  // .doc 由后端 libreoffice 转成 docx 后返回，前端同样按 docx 渲染
  if (lower.endsWith('.docx') || lower.endsWith('.doc')) return 'docx'
  return 'unsupported'
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { message?: string }
    return payload.message || `预览失败（HTTP ${response.status}）`
  } catch {
    return `预览失败（HTTP ${response.status}）`
  }
}

/**
 * 偏差附件文档预览：按文件类型分流渲染 PDF / Word / 图片。
 *
 * - PDF：pdfjs 逐页渲染 canvas，滚动时回传当前页
 * - DOCX/DOC：docx-preview 渲染为 A4 分页 DOM
 * - 图片：objectURL 直出
 * - 其它：降级为「下载原文件」
 */
export function DocumentViewer({
  previewUrl,
  downloadUrl,
  fileName,
  onActivePageChange,
}: DocumentViewerProps) {
  const kind = detectKind(fileName)
  const legacyDoc = fileName.toLowerCase().endsWith('.doc')
  const scrollRef = useRef<HTMLDivElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<ViewState>(kind === 'unsupported' ? 'unsupported' : 'loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [pageCount, setPageCount] = useState(0)

  useEffect(() => {
    if (kind === 'unsupported') return undefined
    const controller = new AbortController()
    let disposed = false
    let objectUrl: string | null = null
    const container = bodyRef.current

    // 组件按 fileId 挂 key 复用，切换文件时整体重建，无需在此重置 React 状态
    if (container) container.innerHTML = ''

    const render = async () => {
      try {
        const response = await fetch(previewUrl, {
          signal: controller.signal,
          credentials: 'same-origin',
        })
        if (!response.ok) {
          throw new Error(await readErrorMessage(response))
        }
        if (disposed || !container) return

        if (kind === 'image') {
          objectUrl = URL.createObjectURL(await response.blob())
          if (disposed) return
          const img = document.createElement('img')
          img.src = objectUrl
          img.alt = fileName
          img.style.maxWidth = '100%'
          img.style.display = 'block'
          img.style.margin = '0 auto'
          img.style.borderRadius = '2px'
          container.appendChild(img)
          setState('ready')
          return
        }

        const buffer = await response.arrayBuffer()
        if (disposed) return

        if (kind === 'pdf') {
          const pdfjs = await import('pdfjs-dist')
          pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'
          const pdf = await pdfjs.getDocument({ data: new Uint8Array(buffer), useSystemFonts: true }).promise
          if (disposed) return
          setPageCount(pdf.numPages)

          for (let index = 1; index <= pdf.numPages; index += 1) {
            if (disposed) return
            const pdfPage = await pdf.getPage(index)
            const viewport = pdfPage.getViewport({ scale: 1.5 })
            const wrapper = document.createElement('div')
            wrapper.dataset.page = String(index)
            wrapper.style.maxWidth = '820px'
            wrapper.style.margin = '0 auto 16px'
            wrapper.style.background = '#fff'
            wrapper.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.08)'
            const canvas = document.createElement('canvas')
            canvas.width = viewport.width
            canvas.height = viewport.height
            canvas.style.width = '100%'
            canvas.style.height = 'auto'
            canvas.style.display = 'block'
            wrapper.appendChild(canvas)
            container.appendChild(wrapper)
            await pdfPage.render({ canvas, viewport }).promise
          }
        } else {
          const { renderAsync } = await import('docx-preview')
          await renderAsync(buffer, container, undefined, {
            className: 'docx',
            inWrapper: true,
            breakPages: true,
            ignoreLastRenderedPageBreak: false,
            renderHeaders: true,
            renderFooters: true,
            renderFootnotes: true,
            useBase64URL: true,
          })
          if (disposed) return
          container.querySelectorAll<HTMLElement>('.docx-wrapper > section').forEach((section, index) => {
            section.dataset.page = String(index + 1)
          })
          setPageCount(Math.max(1, container.querySelectorAll('.docx-wrapper > section').length))
        }

        if (!disposed) setState('ready')
      } catch (error) {
        if (disposed) return
        if (error instanceof DOMException && error.name === 'AbortError') return
        console.error('文档预览失败', error)
        setErrorMessage(error instanceof Error ? error.message : '文档渲染失败')
        setState('error')
      }
    }

    void render()

    return () => {
      disposed = true
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      if (container) container.innerHTML = ''
    }
  }, [previewUrl, kind, fileName])

  useEffect(() => {
    const scroller = scrollRef.current
    if (!scroller) return undefined
    const handleScroll = () => {
      const container = bodyRef.current
      if (!container) return
      const pages = Array.from(container.querySelectorAll<HTMLElement>('[data-page]'))
      if (pages.length === 0) return
      const top = scroller.getBoundingClientRect().top
      let current = 1
      for (const element of pages) {
        if (element.getBoundingClientRect().top - top <= 96) {
          current = Number(element.dataset.page) || current
        }
      }
      onActivePageChange?.(current, pages.length)
    }
    handleScroll()
    scroller.addEventListener('scroll', handleScroll, { passive: true })
    return () => scroller.removeEventListener('scroll', handleScroll)
  }, [onActivePageChange, state, pageCount])

  const downloadButton = (
    <a href={downloadUrl} target="_blank" rel="noreferrer">
      <Button icon={<DownloadOutlined />}>下载原文件</Button>
    </a>
  )

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--color-surface,#f6f5f4)]">
      <div
        ref={scrollRef}
        className="preview-scroll min-h-0 flex-1 overflow-auto px-6 py-5"
      >
        <div ref={bodyRef} className="deviation-doc-viewer" />
        {state === 'loading' && (
          <div className="flex h-64 flex-col items-center justify-center gap-3">
            <Spin />
            <span className="text-[13px] text-[var(--color-slate,#5d5b54)]">正在渲染文档…</span>
            {legacyDoc && (
              <span className="text-[12px] text-[var(--color-stone,#a4a097)]">
                首次预览需转换 .doc 格式，约需数秒
              </span>
            )}
          </div>
        )}
        {(state === 'error' || state === 'unsupported') && (
          <div className="flex h-64 items-center justify-center">
            <Empty
              image={<FileTextOutlined style={{ fontSize: 40, color: '#a4a097' }} />}
              description={
                <div className="space-y-1">
                  <div className="text-[13px] text-[var(--color-ink,#1a1a1a)]">
                    {state === 'unsupported' ? '该文件类型不支持在线预览' : '文档渲染失败'}
                  </div>
                  <div className="text-[12px] text-[var(--color-stone,#a4a097)]">
                    {state === 'unsupported' ? '可下载原文件后用本地应用打开' : errorMessage}
                  </div>
                </div>
              }
            >
              {downloadButton}
            </Empty>
          </div>
        )}
      </div>

      <style jsx global>{`
        .deviation-doc-viewer .docx-wrapper {
          background: transparent;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .deviation-doc-viewer .docx-wrapper > section {
          margin: 0 auto !important;
          background: #fff;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        }
        .deviation-doc-viewer table {
          border-collapse: collapse;
        }
        .deviation-doc-viewer td,
        .deviation-doc-viewer th {
          border-color: #d9d6d1 !important;
        }
        .preview-scroll::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .preview-scroll::-webkit-scrollbar-thumb {
          background: rgba(0, 0, 0, 0.16);
          border-radius: 4px;
        }
      `}</style>
    </div>
  )
}

export default DocumentViewer