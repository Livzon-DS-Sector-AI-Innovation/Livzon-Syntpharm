'use client'

import { useState } from 'react'
import { App, Table, Tag, Tooltip, Typography } from 'antd'
import { saveReportGenSlot } from '@/actions/research/report-gen'
import { slotStateMeta, type ReportGenSlot } from '@/types/research/report-gen'

interface Props {
  jobId: string
  slots: ReportGenSlot[]
  loading?: boolean
  /** 任务终态才允许人工修正，执行中改动会被后续写入覆盖 */
  editable: boolean
}

/** 槽位清单：填充值、状态、来源与原文证据；缺口行灰底并给出责任方。 */
export function ReportGenSlotTable({ jobId, slots, loading, editable }: Props) {
  const { message: msgApi } = App.useApp()
  const [savingKey, setSavingKey] = useState<string>('')

  const handleSave = async (slot: ReportGenSlot, value: string) => {
    if (value === (slot.value ?? '')) return
    setSavingKey(slot.slot_key)
    try {
      await saveReportGenSlot(jobId, slot.slot_key, { value })
      msgApi.success('已保存。Word 文档不会自动重写，需要最新内容请下载对照表，或点「重新生成」。')
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '保存失败')
      throw e
    } finally {
      setSavingKey('')
    }
  }

  const columns = [
    {
      title: '填充项',
      key: 'slot',
      width: 210,
      render: (_: unknown, slot: ReportGenSlot) => (
        <div>
          <div style={{ fontWeight: 500 }}>{slot.slot_label}</div>
          <div style={{ fontSize: 12, color: '#8C8C8C' }}>{slot.slot_key}</div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      width: 110,
      filters: ['filled', 'conflict', 'pending', 'gap', 'anchor_unresolved'].map((state) => ({
        text: slotStateMeta(state).label,
        value: state,
      })),
      onFilter: (value: boolean | React.Key, slot: ReportGenSlot) => slot.state === value,
      render: (state: string) => {
        const meta = slotStateMeta(state)
        return <Tag color={meta.color} style={{ margin: 0 }}>{meta.label}</Tag>
      },
    },
    {
      title: '填入内容',
      key: 'value',
      width: 260,
      render: (_: unknown, slot: ReportGenSlot) => {
        const text = slot.value || ''
        if (slot.state === 'gap' && !text) {
          return (
            <span style={{ color: '#8C8C8C' }}>
              待补充{slot.owner_hint ? `：${slot.owner_hint}` : ''}
            </span>
          )
        }
        if (!editable) {
          return <span style={{ whiteSpace: 'pre-wrap' }}>{text || '-'}</span>
        }
        return (
          <Typography.Text
            style={{ whiteSpace: 'pre-wrap', margin: 0 }}
            editable={{
              maxLength: 4000,
              text: text,
              tooltip: '手动改这里的内容',
              onChange: (next) => { void handleSave(slot, next) },
            }}
            disabled={savingKey === slot.slot_key}
          >
            {text || <span style={{ color: '#bfbfbf' }}>（空）</span>}
          </Typography.Text>
        )
      },
    },
    {
      title: '内容来源',
      dataIndex: 'source_name',
      key: 'source_name',
      width: 160,
      ellipsis: true,
      render: (v: string | null) => v || '-',
    },
    {
      title: '原文依据',
      dataIndex: 'evidence',
      key: 'evidence',
      width: 90,
      render: (v: string | null) =>
        v ? (
          <Tooltip title={<span style={{ whiteSpace: 'pre-wrap' }}>{v}</span>} overlayStyle={{ maxWidth: 420 }}>
            <span style={{ color: '#1677FF', cursor: 'help' }}>查看原文</span>
          </Tooltip>
        ) : (
          <span style={{ color: '#bfbfbf' }}>-</span>
        ),
    },
    {
      title: '责任方',
      dataIndex: 'owner_hint',
      key: 'owner_hint',
      width: 110,
      render: (v: string | null) => v || '-',
    },
  ]

  return (
    <Table
      dataSource={slots}
      columns={columns}
      rowKey="slot_key"
      size="small"
      loading={loading}
      scroll={{ x: 940 }}
      pagination={slots.length > 20 ? { pageSize: 20, size: 'small' } : false}
      onRow={(slot) => ({ style: slot.state === 'gap' ? { background: '#FAFAFA' } : undefined })}
      style={{ background: '#FFFFFF' }}
    />
  )
}