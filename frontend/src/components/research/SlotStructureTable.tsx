'use client'

import { Button, Input, Popconfirm, Select, Space, Switch, Table, Tag } from 'antd'
import type { TableColumnsType } from 'antd'
import { DeleteOutlined, SwapOutlined } from '@ant-design/icons'
import {
  SLOT_VALUE_TYPE_OPTIONS,
  type DocGenSlot,
  type SlotDiffStatus,
} from '@/types/research/deliverable-template-slot'

/** 表格内部行标识：slot_key 允许重复，不能直接当 rowKey */
export type EditableSlot = DocGenSlot & { uid: string }

interface Props {
  slots: EditableSlot[]
  busy: boolean
  loading: boolean
  duplicateKeys: Set<string>
  diffStatus: Map<string, SlotDiffStatus | null>
  selectedKeys: React.Key[]
  onSelect: (keys: React.Key[]) => void
  onPatch: (uid: string, changes: Partial<DocGenSlot>) => void
  onRemove: (uid: string) => void
  onRebind: (uid: string) => void
}

/**
 * 槽位编辑表格：所有字段行内可改，停用行置灰但保留可读。
 *
 * 拆成独立组件是为了让抽屉只管状态与请求，表格只管呈现与行内交互。
 */
export function SlotStructureTable({
  slots,
  busy,
  loading,
  duplicateKeys,
  diffStatus,
  selectedKeys,
  onSelect,
  onPatch,
  onRemove,
  onRebind,
}: Props) {
  const columns: TableColumnsType<EditableSlot> = [
    {
      title: '使用',
      width: 60,
      render: (_, record) => (
        <Switch
          size="small"
          checked={record.is_enabled}
          disabled={busy}
          onChange={(checked) => onPatch(record.uid, { is_enabled: checked })}
        />
      ),
    },
    {
      title: '填充项名称',
      width: 180,
      render: (_, record) => (
        <Input
          size="small"
          value={record.label}
          disabled={busy}
          status={record.label.trim() ? undefined : 'error'}
          onChange={(e) => onPatch(record.uid, { label: e.target.value })}
        />
      ),
    },
    {
      title: '标识（英文短名）',
      width: 150,
      render: (_, record) => (
        <Input
          size="small"
          value={record.slot_key}
          disabled={busy}
          style={{ fontFamily: 'monospace' }}
          status={duplicateKeys.has(record.slot_key) ? 'error' : undefined}
          onChange={(e) => onPatch(record.uid, { slot_key: e.target.value })}
        />
      ),
    },
    {
      title: '内容类型',
      width: 110,
      render: (_, record) => (
        <Select
          size="small"
          value={record.value_type}
          disabled={busy}
          style={{ width: '100%' }}
          options={[...SLOT_VALUE_TYPE_OPTIONS]}
          onChange={(value) => onPatch(record.uid, { value_type: value })}
        />
      ),
    },
    {
      title: '由谁提供',
      width: 130,
      render: (_, record) => (
        <Input
          size="small"
          value={record.owner_hint ?? ''}
          placeholder="可空"
          disabled={busy}
          onChange={(e) => onPatch(record.uid, { owner_hint: e.target.value || null })}
        />
      ),
    },
    {
      title: '填写要求',
      width: 200,
      render: (_, record) => (
        <Input
          size="small"
          value={record.hint ?? ''}
          placeholder="告诉 AI 这一格该写什么内容"
          disabled={busy}
          onChange={(e) => onPatch(record.uid, { hint: e.target.value || null })}
        />
      ),
    },
    {
      title: '写入位置',
      width: 200,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<SwapOutlined />}
          disabled={busy}
          onClick={() => onRebind(record.uid)}
          style={{ padding: 0, whiteSpace: 'normal', textAlign: 'left' }}
        >
          {record.location || '还没定位'}
        </Button>
      ),
    },
    {
      title: '说明',
      width: 140,
      render: (_, record) => (
        <Space size={4} wrap>
          {!record.is_enabled && <Tag>已停用</Tag>}
          {diffStatus.get(record.uid) === 'added' && <Tag color="green">AI 新找到</Tag>}
          {diffStatus.get(record.uid) === 'kept' && <Tag color="blue">保留人工修改</Tag>}
          {duplicateKeys.has(record.slot_key) && <Tag color="red">标识重复</Tag>}
        </Space>
      ),
    },
    {
      title: '',
      width: 50,
      render: (_, record) => (
        <Popconfirm
          title="删除这个填充项？"
          description="只影响以后的生成，已经生成好的文档不变。删除后不可恢复。"
          okText="删除"
          okButtonProps={{ danger: true }}
          cancelText="取消"
          onConfirm={() => onRemove(record.uid)}
        >
          <Button type="link" size="small" danger disabled={busy} icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  return (
    <Table<EditableSlot>
      rowKey="uid"
      size="small"
      dataSource={slots}
      columns={columns}
      loading={loading}
      pagination={false}
      scroll={{ x: 1220, y: 'calc(100vh - 430px)' }}
      rowSelection={{ selectedRowKeys: selectedKeys, onChange: onSelect }}
      onRow={(record) => ({
        // 停用行整体降低透明度，一眼能看出哪些槽位不参与生成
        style: record.is_enabled ? undefined : { opacity: 0.55 },
      })}
      locale={{ emptyText: '还没有填充项：从右侧「可填位置」里挑，或点「重新分析结构」让系统先找一遍' }}
    />
  )
}