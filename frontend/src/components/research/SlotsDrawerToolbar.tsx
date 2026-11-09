'use client'

import { Alert, Button, Flex, Input, Space, Tooltip } from 'antd'
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
 * 填充项抽屉的摘要条与工具条：只负责呈现，状态与请求都在抽屉里。
 *
 * 重新分析的差异摘要（新增/保留/移除）放这里，让「改了什么」在滚表格之前就能看到。
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
  /** 保存按钮为什么点不了：原先只有禁用状态，用户不知道哪里没填对 */
  const saveHint = canSave
    ? ''
    : isStale
      ? '模板文件换过版本，先点「重新分析结构」再保存'
      : !dirty
        ? '还没有改动，不需要保存'
        : '有标识重复或必填项为空，先修正后再保存'

  return (
    <>
      <Alert
        type={isStale ? 'error' : 'info'}
        showIcon
        title={
          isStale
            ? '模板文件已经换过版本，现在的填充项还是上一版的分析结果'
            : `共 ${total} 个填充项，已启用 ${enabled} 个`
        }
        description={
          isStale
            ? '请先点「重新分析结构」重新生成，否则保存会被拒绝。'
            : `分析时间：${analyzedAt ? new Date(analyzedAt).toLocaleString() : '还没分析过'}。停用的填充项不会被 AI 填写，也不会写进生成的文档。`
        }
      />
      {stats && (
        <Alert
          type="success"
          showIcon
          title={`本次重新分析：新增 ${stats.added}、保留 ${stats.kept}、移除 ${stats.removed}`}
          description={
            removedLabels.length
              ? `已移除（AI 没找到且人工没改过）：${removedLabels.slice(0, 5).join('、')}${removedLabels.length > 5 ? ` 等 ${removedLabels.length} 个` : ''}`
              : '这次没有填充项被移除。'
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
            全部启用
          </Button>
          <Button size="small" onClick={() => onBatchToggle(false)} disabled={busy}>
            全部停用
          </Button>
          <Tooltip title="把系统找到、但还没变成填充项的位置一次性补进来（单次最多 60 个）">
            <Button size="small" icon={<ThunderboltOutlined />} onClick={onFillUnused} disabled={busy}>
              一键补齐未使用的位置
            </Button>
          </Tooltip>
          <Button size="small" type="link" onClick={onTogglePanel}>
            {panelOpen ? '收起可填位置' : '展开可填位置'}
          </Button>
        </Space>
        <Space size={8}>
          <Tooltip title="让系统重新读一遍模板文件，重新找出可填位置；人工改过的字段会保留">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              loading={reparsing}
              disabled={busy && !reparsing}
              onClick={onReparse}
            >
              重新分析结构
            </Button>
          </Tooltip>
          <Tooltip title={saveHint}>
            <span>
              <Button
                type="primary"
                size="small"
                icon={<SaveOutlined />}
                loading={saving}
                disabled={!canSave}
                onClick={onSave}
              >
                保存{dirty ? '（有未保存的修改）' : ''}
              </Button>
            </span>
          </Tooltip>
        </Space>
      </Flex>
    </>
  )
}