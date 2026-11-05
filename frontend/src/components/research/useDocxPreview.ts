'use client'

import { useCallback, useRef, useState } from 'react'
import { renderAsync } from 'docx-preview'

interface UseDocxPreviewReturn {
  /** 是否正在加载 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 渲染 docx 到指定容器 */
  renderDocx: (blob: Blob, container: HTMLDivElement | null) => Promise<void>
  /** 重置状态 */
  reset: () => void
}

/**
 * docx 预览 hook：封装 docx-preview 的加载与渲染逻辑。
 * 供 ReportPage、DeliverableTemplatePage、CreateReportModal 等组件复用。
 */
export function useDocxPreview(): UseDocxPreviewReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cancelRef = useRef(false)

  const renderDocx = useCallback(async (blob: Blob, container: HTMLDivElement | null) => {
    if (!container) return
    cancelRef.current = false
    setLoading(true)
    setError(null)
    try {
      const buf = await blob.arrayBuffer()
      if (cancelRef.current || !container) return
      container.innerHTML = ''
      await renderAsync(buf, container, undefined, { inWrapper: true, ignoreWidth: true })
    } catch (e) {
      if (!cancelRef.current) {
        setError(e instanceof Error ? e.message : '文档渲染失败')
      }
    } finally {
      if (!cancelRef.current) {
        setLoading(false)
      }
    }
  }, [])

  const reset = useCallback(() => {
    cancelRef.current = true
    setLoading(false)
    setError(null)
  }, [])

  return { loading, error, renderDocx, reset }
}
