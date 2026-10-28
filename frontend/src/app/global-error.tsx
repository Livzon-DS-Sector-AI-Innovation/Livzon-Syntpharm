'use client'

import { useEffect } from 'react'

/**
 * 根布局崩溃兜底（`global-error`）。
 *
 * 这里**不能**用 antd 或任何自定义组件：根 layout（含 AntdProvider）已经崩了，
 * 依赖它的组件可能再次抛错 —— 所以用最朴素的内联样式 + 原生按钮，
 * 但文案与按钮语义与其他边界页保持一致（人话 + 编号 + 重试 / 返回首页）。
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('[app/global-error]', error)
  }, [error])

  return (
    <html lang="zh-CN">
      <body
        style={{
          margin: 0,
          fontFamily:
            'system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif',
        }}
      >
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            textAlign: 'center',
          }}
        >
          <h2 style={{ margin: 0, fontSize: 20 }}>应用暂时无法加载</h2>
          <p style={{ margin: 0, color: '#6b7280', maxWidth: 520 }}>
            页面初始化时发生错误。可以先重试；若持续出现，请把下面的编号发给管理员。
          </p>
          {error.digest && (
            <code style={{ color: '#9ca3af', fontSize: 12 }}>错误编号：{error.digest}</code>
          )}
          <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
            <button
              onClick={reset}
              style={{
                padding: '8px 20px',
                borderRadius: 6,
                border: 'none',
                background: '#1677ff',
                color: '#fff',
                cursor: 'pointer',
              }}
            >
              重试
            </button>
            <button
              onClick={() => {
                window.location.href = '/'
              }}
              style={{
                padding: '8px 20px',
                borderRadius: 6,
                border: '1px solid #d9d9d9',
                background: '#fff',
                cursor: 'pointer',
              }}
            >
              返回首页
            </button>
          </div>
        </div>
      </body>
    </html>
  )
}
