'use client'

import { useCallback, useRef, useState } from 'react'
import { renderAsync } from 'docx-preview'

interface UseDocxPreviewReturn {
  /** 是否正在加载 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 渲染 docx 到指定容器；返回是否渲染成功（失败时保留容器原有内容） */
  renderDocx: (blob: Blob, container: HTMLDivElement | null) => Promise<boolean>
  /** 重置状态 */
  reset: () => void
}

/**
 * docx 预览 hook：封装 docx-preview 的加载与渲染逻辑。
 * 供 DeliverableTemplatePage 等需要在线预览 Word 的组件复用。
 */
export function useDocxPreview(): UseDocxPreviewReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cancelRef = useRef(false)
  // 渲染序号：并发/过期的渲染直接丢弃，避免两次 renderAsync 往同一容器里交错写
  const seqRef = useRef(0)

  const renderDocx = useCallback(async (blob: Blob, container: HTMLDivElement | null) => {
    if (!container) return false
    cancelRef.current = false
    const seq = (seqRef.current += 1)
    setLoading(true)
    setError(null)
    try {
      const buf = await blob.arrayBuffer()
      if (cancelRef.current || seq !== seqRef.current || !container) return false
      // 先渲染到临时容器，成功后再整体换上去。
      // 直接清空原容器再渲染的话，渲染期间/渲染失败时用户看到的是一整块空白，
      // 只能靠「重新加载」重新触发一遍才能恢复。
      const staging = document.createElement('div')
      await renderAsync(buf, staging, undefined, { inWrapper: true, ignoreWidth: true })
      if (cancelRef.current || seq !== seqRef.current || !container) return false
      container.replaceChildren(...Array.from(staging.childNodes))
      return true
    } catch (e) {
      // 失败时保留上一版渲染结果，只提示错误，不清空文档
      if (seq === seqRef.current) {
        setError(e instanceof Error ? e.message : '文档渲染失败')
      }
      return false
    } finally {
      if (seq === seqRef.current) {
        setLoading(false)
      }
    }
  }, [])

  const reset = useCallback(() => {
    cancelRef.current = true
    seqRef.current += 1
    setLoading(false)
    setError(null)
  }, [])

  return { loading, error, renderDocx, reset }
}
