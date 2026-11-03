'use client'

import { useEffect, useState } from 'react'
import { Alert, Descriptions, Drawer, Space, Spin, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { fetchVersionManifest } from '@/lib/api/client/agent'
import {
  formatDuration,
  type ManifestSlideItem,
  type VersionManifest,
} from '@/types/agent/ppt-video'

interface Props {
  open: boolean
  versionId: string | null
  versionNo?: number
  onClose: () => void
}

/** 短哈希：manifest 里的 sha256 是全部取证明细，界面只露前 12 位避免撑破表格 */
function shortSha(value: string): string {
  return value ? value.slice(0, 12) : '-'
}

const columns: ColumnsType<ManifestSlideItem> = [
  {
    title: '页',
    dataIndex: 'slide_no',
    width: 56,
    render: (value: number) => <span className="font-medium">{value}</span>,
  },
  {
    title: '时长',
    dataIndex: 'duration_ms',
    width: 76,
    render: (value: number) => formatDuration(value),
  },
  {
    title: '本页来源',
    dataIndex: 'cache_hit',
    width: 96,
    render: (hit: boolean) =>
      hit ? <Tag color="green">复用</Tag> : <Tag color="orange">本次重算</Tag>,
  },
  {
    title: '图片 sha256',
    dataIndex: 'image_sha256',
    render: (value: string) => (
      <Typography.Text copyable={{ text: value }} className="font-mono text-[12px]">
        {shortSha(value)}
      </Typography.Text>
    ),
  },
  {
    title: '旁白 sha256',
    dataIndex: 'audio_sha256',
    render: (value: string) => (
      <Typography.Text copyable={{ text: value }} className="font-mono text-[12px]">
        {shortSha(value)}
      </Typography.Text>
    ),
  },
  {
    title: '分段 sha256',
    dataIndex: 'segment_sha256',
    render: (value: string) => (
      <Typography.Text copyable={{ text: value }} className="font-mono text-[12px]">
        {shortSha(value)}
      </Typography.Text>
    ),
  },
]

/**
 * 版本复用取证：视频「没重跑」不是靠日志口述，而是靠这份 manifest
 * —— 每个分段带 sha256，命中缓存的页标记为「复用」，可逐页追溯。
 */
export default function ManifestDrawer({ open, versionId, versionNo, onClose }: Props) {
  const [manifest, setManifest] = useState<VersionManifest | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    if (!open || !versionId) return
    let alive = true
    fetchVersionManifest(versionId)
      .then((data) => {
        if (alive) setManifest(data)
      })
      .catch((err) => {
        if (alive) setError(err instanceof Error ? err.message : '复用记录加载失败')
      })
    return () => {
      alive = false
    }
  }, [open, versionId, reloadToken])

  const loading = open && Boolean(versionId) && !manifest && !error

  const reuse = manifest?.reuse

  return (
    <Drawer
      title={versionNo ? `v${versionNo} 复用记录` : '版本复用记录'}
      width={860}
      open={open}
      onClose={onClose}
      destroyOnHidden
    >
      {loading && (
        <div className="flex h-40 items-center justify-center gap-2">
          <Spin />
          <Typography.Text type="secondary">读取 manifest…</Typography.Text>
        </div>
      )}

      {error && (
        <Alert
          type="error"
          showIcon
          message="读取失败"
          description={error}
          action={
            versionId ? (
              <Typography.Link
                onClick={() => {
                  setError(null)
                  setReloadToken((value) => value + 1)
                }}
              >
                重试
              </Typography.Link>
            ) : undefined
          }
        />
      )}

      {manifest && (
        <Space direction="vertical" size={16} className="w-full">
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="版本 ID" span={2}>
              <Typography.Text copyable className="font-mono text-[12px]">
                {manifest.version_id}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="head_key" span={2}>
              <Typography.Text copyable className="font-mono text-[12px]">
                {manifest.head_key}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="body_key" span={2}>
              <Typography.Text copyable className="font-mono text-[12px]">
                {manifest.body_key}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="encoder_key" span={2}>
              <span className="font-mono text-[12px]">{manifest.encoder_key}</span>
            </Descriptions.Item>
            <Descriptions.Item label="成片时长">{formatDuration(manifest.total_duration_ms)}</Descriptions.Item>
            <Descriptions.Item label="共 N 页">{manifest.slides.length}</Descriptions.Item>
            {reuse && (
              <>
                <Descriptions.Item label="正文命中">
                  {reuse.body_reused_slides} / {reuse.total_slides} 页
                </Descriptions.Item>
                <Descriptions.Item label="正文重算">
                  {reuse.body_rendered_slides} / {reuse.total_slides} 页
                </Descriptions.Item>
                <Descriptions.Item label="片头复用">{reuse.head_reused ? '是' : '否'}</Descriptions.Item>
                <Descriptions.Item label="整体命中">
                  {reuse.reused_slides} / {reuse.total_slides} 页
                </Descriptions.Item>
              </>
            )}
          </Descriptions>

          <Alert
            type="info"
            showIcon
            message="怎么读这份记录"
            description="同一页的图片、旁白、分段三个 sha256 都相同才会被判为「复用」；任一项变化只重算该页，其余页仍走缓存。片头单独一份，改正文不影响它。"
          />

          <Table<ManifestSlideItem>
            size="small"
            rowKey="slide_no"
            columns={columns}
            dataSource={manifest.slides}
            pagination={false}
            scroll={{ y: 420 }}
          />
        </Space>
      )}
    </Drawer>
  )
}