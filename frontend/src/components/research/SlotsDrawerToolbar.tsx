'use client'

import { Alert, Button, Flex, Input, Space } from 'antd'
import { ReloadOutlined, SaveOutlined, ThunderboltOutlined } from '@ant-design/icons'

interface Props {
  isStale: boolean
  total: number
  enabled: number
  analyzedAt: string | null | undefined
  stats: { added: number; kept: number; removed: number } | null
  removedLabels: string[]
  diffOnly: boolean
  keyword: string
  panelOpen: boolean
  busy: boolean
  saving: boolean
  reparsing: boolean
  dirty: boolean
  canSave: boolean
  onKeywordChange: (value: string) => void
  onToggleDiff: () => void
  onBatchToggle: (enabled: boolean) => void
  onFillUnused: () => void
  onTogglePanel: () => void
  onReparse: () => void
  onSave: () => void
}

/**
 * 槽位抽屉的摘要条与工具条：只负责呈现，状态与请求都在抽屉里。
 *
 * 重解析的差异摘要（新增/保留/移除）放这里，让「改了什么」在滚表格之前就能看到。
 */
export function SlotsDrawerToolbar({
  isStale,
  total,
  enabled,
  analyzedAt,
  stats,
  removedLabels,
  diffOnly,
  keyword,
  panelOpen,
  busy,
  saving,
  reparsing,
  dirty,
  canSave,
  onKeywordChange,
  onToggleDiff,
  onBatchToggle,
  onFillUnused,
  onTogglePanel,
  onReparse,
  onSave,
}: Props) {
  return (
    <>
      <Alert
        type={isStale ? 'error' : 'info'}
        showIcon
        title={isStale ? '母本已换版，当前槽位结构来自旧版本' : `共 ${total} 个槽位，启用 ${enabled} 个`}
        description={
          isStale
            ? '请先点「重新识别」重建结构，否则保存会被拒绝。'
            : `识别时间：${analyzedAt ? new Date(analyzedAt).toLocaleString() : '尚未识别'}。停用的槽位不会下发给模型，也不会写入生成结果。`
        }
      />
      {stats && (
        <Alert
          type="success"
          showIcon
          title={`本次重识别：新增 ${stats.added}、保留 ${stats.kept}、移除 ${stats.removed}`}
          description={
            removedLabels.length
              ? `已移除（AI 未识别且未人工修改）：${removedLabels.slice(0, 5).join('、')}${removedLabels.length > 5 ? ` 等 ${removedLabels.length} 个` : ''}`
              : '没有槽位被移除。'
          }
          action={
            <Button size="small" type="link" onClick={onToggleDiff}>
              {diffOnly ? '显示全部' : '只看变化'}
            </Button>
          }
        />
      )}
      <Flex justify="space-between" align="center" gap={8} wrap>
        <Space size={8} wrap>
          <Input.Search
            allowClear
            placeholder="搜索名称 / 标识 / 位置"
            value={keyword}
            onChange={(e) => onKeywordChange(e.target.value)}
            style={{ width: 220 }}
          />
          <Button size="small" onClick={() => onBatchToggle(true)} disabled={busy}>
            批量启用
          </Button>
          <Button size="small" onClick={() => onBatchToggle(false)} disabled={busy}>
            批量停用
          </Button>
          <Button size="small" icon={<ThunderboltOutlined />} onClick={onFillUnused} disabled={busy}>
            一键补齐未占用位置
          </Button>
          <Button size="small" type="link" onClick={onTogglePanel}>
            {panelOpen ? '收起候选位置' : '展开候选位置'}
          </Button>
        </Space>
        <Space size={8}>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={reparsing}
            disabled={busy && !reparsing}
            onClick={onReparse}
          >
            重新识别
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<SaveOutlined />}
            loading={saving}
            disabled={!canSave}
            onClick={onSave}
          >
            保存{dirty ? '（有未保存修改）' : ''}
          </Button>
        </Space>
      </Flex>
    </>
  )
}