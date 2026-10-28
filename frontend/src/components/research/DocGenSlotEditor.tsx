'use client'

import { useState } from 'react'
import { Button, Descriptions, Input, Space, Tag, Typography } from 'antd'
import { EditOutlined, UndoOutlined } from '@ant-design/icons'
import { DOC_GEN_SLOT_STATE_LABELS } from '@/types/research/doc-gen'
import type { DocGenExtractedSlot } from '@/lib/api/client/research/doc-gen'

const { Text } = Typography

/** 填充项状态颜色 */
const SLOT_STATE_COLORS: Record<string, string> = {
  ok: 'success',
  ai_draft: 'blue',
  pending: 'warning',
  conflict: 'orange',
  manual_only: 'processing',
  ai_failed: 'error',
  layout_overflow: 'gold',
  anchor_unresolved: 'red',
  needs_verify: 'gold',
}

interface Props {
  /** 提取到的槽位列表 */
  slots: DocGenExtractedSlot[]
  /** 用户已编辑的槽位值（key → 修正后的文本） */
  editedSlots: Record<string, string>
  /** 编辑变化回调 */
  onEditedSlotsChange: (slots: Record<string, string>) => void
}

/**
 * AI 提取结果槽位编辑器：展示所有槽位，支持行内编辑与重置。
 * 从 CreateReportModal 拆出，供报告模块复用。
 */
export function DocGenSlotEditor({ slots, editedSlots, onEditedSlotsChange }: Props) {
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const handleEdit = (slot: DocGenExtractedSlot) => {
    setEditingKey(slot.slot_key)
    setEditValue(slot.text || '')
  }

  const handleSaveEdit = () => {
    if (!editingKey) return
    onEditedSlotsChange({ ...editedSlots, [editingKey]: editValue })
    setEditingKey(null)
  }

  const handleReset = (key: string) => {
    const next = { ...editedSlots }
    delete next[key]
    onEditedSlotsChange(next)
  }

  const getSlotValue = (slot: DocGenExtractedSlot) =>
    editedSlots[slot.slot_key] !== undefined ? editedSlots[slot.slot_key] : slot.text || ''

  if (slots.length === 0) return <Text type="secondary">暂无提取结果</Text>

  return (
    <Descriptions size="small" column={1} bordered>
      {slots.map((slot) => {
        const isTable = (slot.rows?.length ?? 0) > 0
        return (
          <Descriptions.Item
            key={slot.slot_key}
            label={
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span>{slot.label || slot.slot_key}</span>
                <Tag color={SLOT_STATE_COLORS[slot.state] ?? 'default'}>
                  {DOC_GEN_SLOT_STATE_LABELS[slot.state] ?? slot.state}
                </Tag>
              </div>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {editingKey === slot.slot_key ? (
                <Input.TextArea
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  rows={3}
                  style={{ width: '100%' }}
                  onPressEnter={handleSaveEdit}
                />
              ) : (
                <Text style={{ whiteSpace: 'pre-wrap' }}>
                  {isTable ? `${slot.rows?.length ?? 0} 行（表格数据）` : getSlotValue(slot)}
                </Text>
              )}
              {!isTable && (
                <Space>
                  {editingKey !== slot.slot_key ? (
                    <Button type="text" icon={<EditOutlined />} size="small" onClick={() => handleEdit(slot)} />
                  ) : (
                    <Button type="primary" size="small" onClick={handleSaveEdit}>保存</Button>
                  )}
                  {editedSlots[slot.slot_key] !== undefined && (
                    <Button
                      type="text"
                      icon={<UndoOutlined />}
                      size="small"
                      onClick={() => handleReset(slot.slot_key)}
                    />
                  )}
                </Space>
              )}
            </div>
          </Descriptions.Item>
        )
      })}
    </Descriptions>
  )
}
