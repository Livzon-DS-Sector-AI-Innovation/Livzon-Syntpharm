'use client'

import { useState } from 'react'
import { App, Button, Drawer, Empty, Flex, Popconfirm, Skeleton, Tag, Tooltip } from 'antd'
import { DownloadOutlined, HistoryOutlined, RollbackOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { restoreReportGenVersion } from '@/actions/research/report-gen'
import { downloadReportGenVersion, fetchReportGenVersions } from '@/lib/api/client/research/report-gen'
import { versionKindLabel, type ReportGenDocumentVersion } from '@/types/research/report-gen'

interface Props {
  jobId: string
  open: boolean
  onClose: () => void
  currentVersionId?: string | null
  onRestored: () => void
}

const KIND_COLOR: Record<string, string> = {
  ai_draft: 'processing',
  manual_edit: 'success',
  manual_upload: 'warning',
  manual_render: 'default',
}

function formatTime(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatSize(value?: number | null): string {
  if (!value) return ''
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

/**
 * 版本时间线：AI 初稿、在线编辑、人工上传都在这里。
 *
 * 回滚不是「把旧文件恢复成当前」而是「用旧文件再落一个新版本」，
 * 所以回滚之后仍然可以再回滚回来，历史版本永不被改写。
 */
export function ReportGenVersionList({ jobId, open, onClose, currentVersionId, onRestored }: Props) {
  const { message } = App.useApp()
  const [restoring, setRestoring] = useState<string | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['report-gen-versions', jobId],
    queryFn: () => fetchReportGenVersions(jobId),
    enabled: open,
    staleTime: 10_000,
  })

  const versions = data?.items ?? []

  const handleDownload = async (version: ReportGenDocumentVersion) => {
    setDownloading(version.id)
    try {
      const name = await downloadReportGenVersion(version.id, version.file_name || '报告.docx')
      message.success(`已下载 ${name}`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '下载失败')
    } finally {
      setDownloading(null)
    }
  }

  const handleRestore = async (version: ReportGenDocumentVersion) => {
    setRestoring(version.id)
    try {
      await restoreReportGenVersion(jobId, version.id, currentVersionId ?? null)
      message.success(`已回滚到第 ${version.version_no} 版`)
      await refetch()
      onRestored()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '回滚失败')
    } finally {
      setRestoring(null)
    }
  }

  return (
    <Drawer
      title={
        <Flex gap={8} align="center">
          <HistoryOutlined style={{ color: '#1677FF' }} />
          <span style={{ fontSize: 15, fontWeight: 600 }}>版本记录</span>
        </Flex>
      }
      width={520}
      open={open}
      onClose={onClose}
      styles={{ body: { padding: 0, background: '#FAFBFC' } }}
    >
      {isLoading && (
        <div style={{ padding: 16 }}>
          <Skeleton active paragraph={{ rows: 6 }} title={false} />
        </div>
      )}
      {!isLoading && versions.length === 0 && (
        <div style={{ padding: 32 }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有版本记录" />
        </div>
      )}
      {!isLoading &&
        versions.map((version) => {
          return (
            <div
              key={version.id}
              style={{
                padding: '12px 16px',
                borderBottom: '1px solid #EDEFF2',
                background: '#FFFFFF',
              }}
            >
              <Flex align="center" gap={8} wrap>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#1F2329' }}>第 {version.version_no} 版</span>
                <Tag color={KIND_COLOR[version.kind] ?? 'default'} style={{ margin: 0 }}>
                  {versionKindLabel(version.kind)}
                </Tag>
                {version.is_current && (
                  <Tag color="blue" style={{ margin: 0 }}>
                    当前
                  </Tag>
                )}
                <span style={{ marginLeft: 'auto', fontSize: 11, color: '#8C8C8C' }}>
                  {formatTime(version.created_at)}
                </span>
              </Flex>
              <div style={{ marginTop: 4, fontSize: 12, color: '#5A6472' }}>
                {version.note || version.file_name || '—'}
                {version.file_size ? ` · ${formatSize(version.file_size)}` : ''}
              </div>
              <Flex gap={8} style={{ marginTop: 8 }}>
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  loading={downloading === version.id}
                  onClick={() => void handleDownload(version)}
                >
                  下载
                </Button>
                {!version.is_current && (
                  <Popconfirm
                    title={`回滚到第 ${version.version_no} 版？`}
                    description="会以这一版文件生成一个新版本，当前版本不会被删除，之后还能再回滚。"
                    okText="回滚"
                    cancelText="取消"
                    onConfirm={() => void handleRestore(version)}
                  >
                    <Button
                      size="small"
                      icon={<RollbackOutlined />}
                      loading={restoring === version.id}
                      disabled={!!restoring}
                    >
                      回滚到这一版
                    </Button>
                  </Popconfirm>
                )}
                {version.is_current && (
                  <Tooltip title="当前版本，无需回滚">
                    <span style={{ fontSize: 11, color: '#8C8C8C', lineHeight: '24px' }}>正在使用</span>
                  </Tooltip>
                )}
              </Flex>
            </div>
          )
        })}
    </Drawer>
  )
}