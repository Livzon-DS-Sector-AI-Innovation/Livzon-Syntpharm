'use client'

import { useState } from 'react'
import { Button, Empty, Space, Tag, Tooltip, Typography } from 'antd'
import { CloudDownloadOutlined, FileSearchOutlined, HistoryOutlined } from '@ant-design/icons'

import ManifestDrawer from './ManifestDrawer'
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
 * 右栏版本区：成片列表 + 下载 + 复用记录入口。
 *
 * 下载链接直接指向后端媒体流（支持 Range），浏览器可边下边播；
 * 不复用 URL 到前端拼字符串，避免项目路径规则变更后两处不同步。
 */
export default function VersionPanel({ detail }: Props) {
  const [manifestOpen, setManifestOpen] = useState(false)
  const [activeVersion, setActiveVersion] = useState<VersionItem | null>(null)

  const versions = detail.versions ?? []
  const latestId = versions[0]?.id

  const openManifest = (version: VersionItem) => {
    setActiveVersion(version)
    setManifestOpen(true)
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

      <div className="flex flex-col gap-2">
        {versions.map((version) => {
          const isLatest = version.id === latestId
          return (
            <div
              key={version.id}
              className={[
                'rounded-lg border p-2.5',
                isLatest ? 'border-[#C9C1F0] bg-[#FAF8FF]' : 'border-[#EFEDE9] bg-white',
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
                <Button size="small" type="link" icon={<CloudDownloadOutlined />} href={version.download_url} download>
                  下载
                </Button>
                <Button size="small" type="link" icon={<FileSearchOutlined />} onClick={() => openManifest(version)}>
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
    </div>
  )
}