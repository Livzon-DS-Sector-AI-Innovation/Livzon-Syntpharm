'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import * as pdfjsLib from 'pdfjs-dist'

// Disable worker to force main-thread parsing
pdfjsLib.GlobalWorkerOptions.workerSrc = ''

interface PDFViewerProps {
  base64: string
  fileName?: string | null
  fileType?: string | null
}

export default function PDFViewer({ base64, fileName, fileType }: PDFViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<'loading' | 'done' | 'error'>('loading')
  const [errMsg, setErrMsg] = useState('')
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)

  useEffect(() => {
    let disposed = false
    let blobUrl: string | null = null
    const renderTasks: any[] = []

    async function render() {
      try {
        setStatus('loading')

        const binary = atob(base64)
        const bytes = new Uint8Array(binary.length)
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i)
        }

        const blob = new Blob([bytes], { type: fileType || 'application/pdf' })
        blobUrl = URL.createObjectURL(blob)
        if (!disposed) setDownloadUrl(blobUrl)

        const loadingTask = pdfjsLib.getDocument({
          data: bytes,
          useSystemFonts: true,
        })

        const pdf = await loadingTask.promise
        if (disposed) return

        const container = containerRef.current
        if (!container) return
        container.innerHTML = ''

        for (let i = 1; i <= pdf.numPages; i++) {
          if (disposed) break
          const page = await pdf.getPage(i)
          const scale = 1.5
          const viewport = page.getViewport({ scale })

          const canvas = document.createElement('canvas')
          canvas.width = viewport.width
          canvas.height = viewport.height
          canvas.style.width = '100%'
          canvas.style.height = 'auto'
          canvas.style.display = 'block'
          canvas.style.marginBottom = '12px'
          container.appendChild(canvas)

          const ctx = canvas.getContext('2d')
          if (!ctx) continue

          const renderTask = page.render({ canvas, viewport })
          renderTasks.push(renderTask)

          // Wait for render with a timeout safeguard
          await Promise.race([
            renderTask.promise,
            new Promise<void>((resolve) => setTimeout(resolve, 3000)),
          ])
        }

        if (!disposed) setStatus('done')
      } catch (err: any) {
        console.error('PDF render error:', err)
        if (!disposed) {
          setStatus('error')
          setErrMsg('浏览器无法直接预览此 PDF，请下载后查看')
        }
      }
    }

    render()
    return () => {
      disposed = true
      renderTasks.forEach((task) => {
        try { task.cancel() } catch {}
      })
      if (blobUrl) URL.revokeObjectURL(blobUrl)
    }
  }, [base64, fileType])

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <span className="text-gray-500">PDF 加载中...</span>
        {downloadUrl && (
          <a href={downloadUrl} download={fileName || 'file.pdf'}>
            <Button icon={<DownloadOutlined />}>下载原文件查看</Button>
          </a>
        )}
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <span className="text-red-500">{errMsg}</span>
        {downloadUrl && (
          <a href={downloadUrl} download={fileName || 'file.pdf'}>
            <Button icon={<DownloadOutlined />}>下载原文件查看</Button>
          </a>
        )}
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="w-full"
      style={{ maxHeight: '75vh', overflowY: 'auto' }}
    />
  )
}
