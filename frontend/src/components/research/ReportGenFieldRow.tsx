'use client'

import { memo, useState } from 'react'
import { Flex, Tag } from 'antd'
import {
  fieldKeyLabel,
  fieldStateMeta,
  type ReportGenFieldItem,
} from '@/types/research/report-gen'

interface Props {
  item: ReportGenFieldItem
  selected: boolean
  onSelect: (item: ReportGenFieldItem) => void
}

/** 一行摘要：优先显示已写入内容，其次母本原文，最后退回「为什么空着」。 */
function summaryOf(item: ReportGenFieldItem): string {
  const value = (item.value ?? '').trim()
  if (value) return value.replace(/\s+/g, ' ')
  const text = (item.text ?? '').trim()
  if (text) return text
  return item.reason ?? '（空）'
}

/**
 * 位置清单里的一行。
 *
 * 独立成组件的原因是 hover 态：放在清单组件里时，鼠标每划过一行都会重渲染整份清单
 * （几百个按钮）。hover 收在行内后，鼠标移动只影响当前这一行。
 */
export const ReportGenFieldRow = memo(function ReportGenFieldRow({ item, selected, onSelect }: Props) {
  const [hovered, setHovered] = useState(false)
  const meta = fieldStateMeta(item.state, item.edit_source)

  return (
    <button
      type="button"
      data-field-key={item.key}
      onClick={() => onSelect(item)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'stretch',
        gap: 10,
        padding: '8px 12px',
        border: 'none',
        borderLeft: `3px solid ${meta.text}`,
        background: selected ? '#E6F4FF' : hovered ? '#F5F7FA' : 'transparent',
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'background-color 120ms ease',
      }}
    >
      <span style={{ flex: 1, minWidth: 0 }}>
        <Flex gap={6} align="center" wrap>
          <span style={{ fontSize: 13, fontWeight: 500, color: '#1F2329' }}>{item.label}</span>
          <Tag
            color={meta.color}
            style={{ margin: 0, fontSize: 11, lineHeight: '18px', borderStyle: meta.dashed ? 'dashed' : undefined }}
          >
            {meta.label}
          </Tag>
          {item.kind === 'table_cell' && (
            <Tag style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}>表格</Tag>
          )}
          {item.writable === false && (
            <Tag style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}>模板固定</Tag>
          )}
          {item.human_locked && (
            <Tag color="green" style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}>
              人工确认
            </Tag>
          )}
        </Flex>
        <div
          style={{
            marginTop: 3,
            fontSize: 12,
            color: item.state === 'blank' ? '#8C8C8C' : '#5A6472',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {summaryOf(item)}
        </div>
        {item.source_name && (
          <div style={{ marginTop: 2, fontSize: 11, color: '#8C8C8C' }}>
            来源：{item.source_name}
            {item.confidence !== null && item.confidence !== undefined
              ? ` · 置信度 ${Math.round(item.confidence * 100)}%`
              : ''}
          </div>
        )}
      </span>
      <span
        style={{
          alignSelf: 'center',
          fontSize: 11,
          color: '#8C8C8C',
          whiteSpace: 'nowrap',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        }}
      >
        {fieldKeyLabel(item.key)}
      </span>
    </button>
  )
})