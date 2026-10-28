'use client'

import { useState, type ReactNode } from 'react'
import { Alert, Button, Input, Modal, Typography } from 'antd'
import { CloseOutlined } from '@ant-design/icons'

const { Text } = Typography

export interface BatchFailureItem {
  key: string
  label?: string | null
  reason: string
}

export interface BatchResult {
  succeeded: string[]
  failed: BatchFailureItem[]
}

/** 多选后出现在工具栏顶部的批量操作条。 */
export function BatchActionBar({
  count,
  loading,
  onClear,
  children,
}: {
  count: number
  loading?: boolean
  onClear: () => void
  children: ReactNode
}) {
  if (!count) return null
  return (
    <div className="flex w-full flex-wrap items-center gap-2 rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface-soft)] px-3 py-2">
      <Text strong>已选 {count} 项</Text>
      {children}
      <Button size="small" type="link" icon={<CloseOutlined />} onClick={onClear} disabled={loading}>
        取消选择
      </Button>
    </div>
  )
}

/** 批量操作结果：成功数 + 失败项逐条原因。 */
export function BatchResultModal({ result, onClose }: { result: BatchResult | null; onClose: () => void }) {
  return (
    <Modal
      title="批量操作结果"
      open={!!result}
      onCancel={onClose}
      footer={[
        <Button key="ok" type="primary" onClick={onClose}>
          知道了
        </Button>,
      ]}
      width="min(560px, calc(100vw - 24px))"
    >
      {result && (
        <>
          <Alert
            type={result.failed.length ? 'warning' : 'success'}
            showIcon
            title={
              result.failed.length
                ? `成功 ${result.succeeded.length} 项，失败 ${result.failed.length} 项`
                : `成功 ${result.succeeded.length} 项`
            }
            className="mb-3"
          />
          {result.failed.length > 0 && (
            <ul className="max-h-[300px] space-y-1 overflow-auto text-[13px]">
              {result.failed.map((item) => (
                <li key={item.key}>
                  <Text code>{item.label || item.key}</Text>：{item.reason}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Modal>
  )
}

/** 批量删除的强确认：列出影响项 + 输入「删除」才可执行。 */
export function BatchDeleteConfirmModal({
  open,
  items,
  loading,
  onCancel,
  onConfirm,
}: {
  open: boolean
  items: { key: string; label: string }[]
  loading?: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  const [text, setText] = useState('')

  return (
    <Modal
      title="批量删除"
      open={open}
      onCancel={onCancel}
      onOk={onConfirm}
      // 关闭动画结束后再清理输入，避免每次打开都用 effect 重置 state
      afterClose={() => setText('')}
      okText="确认删除"
      cancelText="取消"
      okButtonProps={{ danger: true, disabled: text !== '删除', loading }}
      width="min(560px, calc(100vw - 24px))"
    >
      <Alert
        type="error"
        showIcon
        title="删除后不可恢复"
        description={`将删除以下 ${items.length} 项，请确认没有误选：`}
        className="mb-3"
      />
      <ul className="mb-3 max-h-[240px] space-y-1 overflow-auto text-[13px]">
        {items.map((item) => (
          <li key={item.key}>· {item.label}</li>
        ))}
      </ul>
      <div className="text-[13px]">
        请输入 <Text code>删除</Text> 以确认：
      </div>
      <Input
        className="mt-2"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="输入 删除"
        autoComplete="off"
      />
    </Modal>
  )
}
