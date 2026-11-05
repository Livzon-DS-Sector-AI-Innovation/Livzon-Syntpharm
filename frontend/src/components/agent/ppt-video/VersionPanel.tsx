'use client'

import { useState } from 'react'
import { Button, Empty, Space, Tag, Tooltip, Typography } from 'antd'
import { CloudDownloadOutlined, FileSearchOutlined, HistoryOutlined, PlayCircleOutlined } from '@ant-design/icons'

import ManifestDrawer from './ManifestDrawer'
import VideoPreviewModal from './VideoPreviewModal'
import { formatDuration, formatFileSize, type ProjectDetail, type VersionItem } from '@/types/agent/ppt-video'

interface Props {
  detail: ProjectDetail
}

/** 版本号高的排前面：detail.versions 由后端按 version_no 倒序返回 */
function versionHint(version: VersionItem, isLatest: boolean): string {
  if (isLatest) return '当前版本'
  return `历史版本 v${version.version_no}`
}

/**
 * 右栏版本区：常驻播放器 + 成片列表 + 下载 + 复用记录入口。
 *
 * 播放器与下载共用后端同一个媒体端点（前者带 `inline=1`），浏览器可边下边播；
 * 不复用 URL 到前端拼字符串，避免项目路径规则变更后两处不同步。
 */
export default function VersionPanel({ detail }: Props) {
  const [manifestOpen, setManifestOpen] = useState(false)
  const [activeVersion, setActiveVersion] = useState<VersionItem | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  // 用户点过哪个版本就播哪个；没点过时跟最新版本走，避免新出片后播放器还停在旧版本
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const versions = detail.versions ?? []
  const latestId = versions[0]?.id
  const playing = versions.find((version) => version.id === selectedId) ?? versions[0]

  const openManifest = (version: VersionItem) => {
    setActiveVersion(version)
    setManifestOpen(true)
  }

  const openPreview = (version: VersionItem) => {
    setSelectedId(version.id)
    setActiveVersion(version)
    setPreviewOpen(true)
  }

  return (
    <div className="rounded-xl border border-[#E5E3DF] bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <Space size={6}>
          <HistoryOutlined className="text-[#5D5B54]" />
          <Typography.Text strong>版本</Typography.Text>
        </Space>
        <Tag className="!m-0">{versions.length} 个</Tag>
      </div>

      {!versions.length && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={<span className="text-[12px] text-[#A4A097]">还没有成片，点上方「生成视频」</span>}
        />
      )}

      {playing && (
        <div className="mb-1.5">
          {/* key 绑版本：切换版本时强制换源，不沿用上一个成片的缓冲与进度 */}
          <video
            key={playing.id}
            src={playing.preview_url || undefined}
            controls
            preload="metadata"
            playsInline
            className="block w-full rounded-lg bg-black"
            style={{ maxHeight: 220 }}
          />
          <div className="mt-1 flex items-center justify-between gap-2">
            <Typography.Text type="secondary" className="text-[11px]">
              正在播放 v{playing.version_no}
              {playing.id === latestId ? '（当前版本）' : ''}
            </Typography.Text>
            <Button size="small" type="link" icon={<PlayCircleOutlined />} onClick={() => openPreview(playing)}>
              大屏播放
            </Button>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-2">
        {versions.map((version) => {
          const isLatest = version.id === latestId
          const isSelected = playing?.id === version.id
          return (
            <div
              key={version.id}
              role="button"
              tabIndex={0}
              onClick={() => setSelectedId(version.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setSelectedId(version.id)
                }
              }}
              className={[
                'cursor-pointer rounded-lg border p-2.5 transition-colors',
                isSelected
                  ? 'border-[#6C5CE7] bg-[#FAF8FF]'
                  : 'border-[#EFEDE9] bg-white hover:border-[#D9D4F5]',
              ].join(' ')}
            >
              <div className="flex items-center justify-between gap-2">
                <Space size={6} wrap>
                  <Typography.Text strong className="text-[13px]">
                    v{version.version_no}
                  </Typography.Text>
                  {isLatest && (
                    <Tag color="purple" className="!m-0 !px-1 !text-[11px]">
                      当前
                    </Tag>
                  )}
                  <Typography.Text type="secondary" className="text-[11px]">
                    {formatDuration(version.duration_ms)} · {formatFileSize(version.file_size)}
                  </Typography.Text>
                </Space>
              </div>

              <Tooltip title={version.file_name}>
                <Typography.Text type="secondary" className="mt-1 block truncate text-[11px]">
                  {version.file_name}
                </Typography.Text>
              </Tooltip>

              <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[#A4A097]">
                <span title={versionHint(version, isLatest)}>
                  正文复用 {version.reuse.body_reused_slides}/{version.reuse.total_slides} 页
                </span>
                {version.reuse.head_reused > 0 && <Tag className="!m-0 !px-1 !text-[10px]">片头复用</Tag>}
                <span>{version.created_at ? new Date(version.created_at).toLocaleString('zh-CN') : '-'}</span>
              </div>

              <Space className="mt-1.5" size={4}>
                <Button
                  size="small"
                  type="link"
                  icon={<PlayCircleOutlined />}
                  onClick={(event) => {
                    event.stopPropagation()
                    openPreview(version)
                  }}
                >
                  预览
                </Button>
                <Button size="small" type="link" icon={<CloudDownloadOutlined />} href={version.download_url} download>
                  下载
                </Button>
                <Button
                  size="small"
                  type="link"
                  icon={<FileSearchOutlined />}
                  onClick={(event) => {
                    event.stopPropagation()
                    openManifest(version)
                  }}
                >
                  复用记录
                </Button>
              </Space>
            </div>
          )
        })}
      </div>

      <ManifestDrawer
        key={activeVersion?.id ?? 'none'}
        open={manifestOpen}
        versionId={activeVersion?.id ?? null}
        versionNo={activeVersion?.version_no}
        onClose={() => setManifestOpen(false)}
      />

      <VideoPreviewModal
        open={previewOpen}
        src={activeVersion?.preview_url}
        title={activeVersion ? `v${activeVersion.version_no} · ${activeVersion.file_name}` : undefined}
        fileName={activeVersion?.file_name}
        downloadUrl={activeVersion?.download_url}
        onClose={() => setPreviewOpen(false)}
      />
    </div>
  )
}