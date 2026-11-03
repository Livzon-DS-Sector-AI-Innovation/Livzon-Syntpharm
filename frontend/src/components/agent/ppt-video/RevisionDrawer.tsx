'use client'

import { useCallback, useEffect, useState } from 'react'
import { App, Button, Drawer, Empty, Popconfirm, Space, Spin, Tag, Typography } from 'antd'
import { HistoryOutlined, UndoOutlined } from '@ant-design/icons'

import { loadScriptRevisions, rollbackRevision } from '@/actions/agent/ppt-video'
import {
  REVISION_MODE_LABEL,
  REVISION_STATUS_LABEL,
  type ProjectDetail,
  type RevisionItem,
} from '@/types/agent/ppt-video'

interface Props {
  open: boolean
  projectId: string
  onClose: () => void
  onRolledBack: (detail: ProjectDetail) => void
}

const STATUS_COLOR: Record<string, string> = {
  queued: 'default',
  running: 'processing',
  succeeded: 'green',
  failed: 'red',
}

/**
 * 修订记录：每次改写（含换源重写）留一条，可回滚到改写前。
 *
 * 回滚只把 before 快照写回讲稿并把记录置为已回滚，不删记录，便于追溯。
 */
export default function RevisionDrawer({ open, projectId, onClose, onRolledBack }: Props) {
  const { message } = App.useApp()
  const [items, setItems] = useState<RevisionItem[]>([])
  const [loading, setLoading] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    const result = await loadScriptRevisions(projectId)
    setLoading(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    setItems(result.data ?? [])
  }, [projectId, message])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- 抽屉打开即拉一次列表，setLoading 是同步反馈而非派生状态
    if (open) void load()
  }, [open, load])

  const handleRollback = async (revision: RevisionItem) => {
    setBusyId(revision.id)
    const result = await rollbackRevision(projectId, revision.id)
    setBusyId(null)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    message.success(result.message)
    onRolledBack(result.data)
    await load()
  }

  return (
    <Drawer
      forceRender
      size={480}
      open={open}
      onClose={onClose}
      destroyOnHidden
      title={
        <span className="flex items-center gap-2">
          <HistoryOutlined className="text-[#5645D4]" />
          讲稿修订记录
        </span>
      }
      styles={{
        header: { borderBottom: '1px solid #e5e3df', padding: '16px 24px' },
        body: { padding: '16px 24px', background: '#FCFCFB' },
      }}
      extra={
        <Button size="small" onClick={() => void load()} loading={loading}>
          刷新
        </Button>
      }
    >
      {loading && !items.length ? (
        <div className="py-16 text-center">
          <Spin />
        </div>
      ) : items.length === 0 ? (
        <Empty description="还没有改写记录；每次 AI 改写都会在这里留一条可回滚的快照" />
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((item) => {
            const rollbackable = item.applied && item.status === 'succeeded'
            return (
              <div
                key={item.id}
                className="rounded-xl border border-[#E5E3DF] bg-white px-3.5 py-3 transition-colors hover:border-[#5645D4]/40"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[13px] font-semibold text-[#37352F]">
                        {REVISION_MODE_LABEL[item.mode] ?? item.mode}
                      </span>
                      <Tag color={STATUS_COLOR[item.status]} className="!m-0 !text-[11px]">
                        {REVISION_STATUS_LABEL[item.status] ?? item.status}
                      </Tag>
                      {!item.applied && (
                        <Tag className="!m-0 !text-[11px]">已回滚</Tag>
                      )}
                    </div>
                    <div className="mt-1 text-[12px] text-[#5D5B54]">
                      {item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : '-'}
                      <span className="mx-1.5 text-[#D5D1CB]">·</span>
                      影响 {item.scope_count} 页
                      <span className="mx-1.5 text-[#D5D1CB]">·</span>
                      {item.model_name || '未记录模型'}
                    </div>
                    {item.instruction && (
                      <div className="mt-1 truncate text-[11px] text-[#A4A097]">指令：{item.instruction}</div>
                    )}
                    {item.status === 'failed' && item.error_message && (
                      <div className="mt-1 text-[11px] text-[#D93025]">{item.error_message}</div>
                    )}
                  </div>

                  {rollbackable ? (
                    <Popconfirm
                      title="回滚到这次改写之前？"
                      description="只恢复讲稿文字，已生成的音频需要重新渲染"
                      okText="回滚"
                      cancelText="取消"
                      onConfirm={() => handleRollback(item)}
                    >
                      <Button
                        type="text"
                        size="small"
                        icon={<UndoOutlined />}
                        loading={busyId === item.id}
                        className="!text-[#5645D4]"
                      >
                        回滚
                      </Button>
                    </Popconfirm>
                  ) : (
                    <Space size={2}>
                      <Typography.Text type="secondary" className="text-[11px]">
                        {item.applied ? '不可回滚' : '已回滚'}
                      </Typography.Text>
                    </Space>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Drawer>
  )
}