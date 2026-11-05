'use client'

import { useCallback, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Alert, App, Button, Input, Select, Space, Table, Tag, Tooltip, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  CloudDownloadOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  SearchOutlined,
} from '@ant-design/icons'

import AiConfigDrawer from './AiConfigDrawer'
import PptUploadModal from './PptUploadModal'
import VideoPreviewModal from './VideoPreviewModal'
import { deletePptVideoProject } from '@/actions/agent/ppt-video'
import { fetchPptVideoProjects } from '@/lib/api/client/agent'
import { PermissionGate } from '@/components/auth/PermissionGate'
import { PERM } from '@/lib/permissions/codes'
import {
  LANGUAGE_LABEL,
  PROJECT_STATUS_LABEL,
  voiceLabel,
  type AiConfigListResponse,
  type ProjectSummary,
  type VoiceOption,
} from '@/types/agent/ppt-video'

interface Props {
  initialItems: ProjectSummary[]
  initialTotal: number
  voices: VoiceOption[]
  initialError?: string | null
  /** AI 配置首屏；读取失败时为 null，抽屉打开后自行重取 */
  initialAiConfigs?: AiConfigListResponse | null
}

const STATUS_COLOR: Record<string, string> = {
  draft: 'default',
  rendering: 'processing',
  ready: 'green',
  failed: 'red',
}

/** 缩略图只在页面图已渲染时存在；未出图时后端返回的是同一条图片 URL（404），用 placehoder 兜住 */
function Thumb({ src, alt }: { src?: string | null; alt: string }) {
  const [broken, setBroken] = useState(false)
  if (!src || broken) {
    return (
      <span className="flex h-[42px] w-[74px] shrink-0 items-center justify-center rounded-md border border-dashed border-[#E5E3DF] bg-[#FAFAF9] text-[10px] text-[#A4A097]">
        无预览
      </span>
    )
  }
  return (
    // 缩略图走后端代理，浏览器带 cookie 鉴权
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      onError={() => setBroken(true)}
      className="h-[42px] w-[74px] shrink-0 rounded-md border border-[#E5E3DF] bg-black object-contain"
    />
  )
}

/**
 * 项目列表：按项目名搜索、按状态/语言筛选、翻页都走浏览器只读 GET；
 * 新建与删除走 Server Actions。
 */
export default function PptVideoTable({
  initialItems,
  initialTotal,
  voices,
  initialError,
  initialAiConfigs,
}: Props) {
  const { message, modal } = App.useApp()
  const router = useRouter()

  const [items, setItems] = useState<ProjectSummary[]>(initialItems)
  const [total, setTotal] = useState(initialTotal)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(initialError ?? null)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [language, setLanguage] = useState<string | undefined>(undefined)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)
  const [aiConfigs, setAiConfigs] = useState<AiConfigListResponse | null>(initialAiConfigs ?? null)
  // 列表页只播最新版本：`preview_url` 由后端按 latest_version 派生，前端不拼路径
  const [preview, setPreview] = useState<{ src: string; title: string } | null>(null)

  const load = useCallback(
    async (nextPage = page, nextPageSize = pageSize) => {
      setLoading(true)
      setError(null)
      try {
        const result = await fetchPptVideoProjects({
          keyword: keyword.trim() || undefined,
          status,
          language,
          page: nextPage,
          page_size: nextPageSize,
        })
        setItems(result.items)
        setTotal(result.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载项目列表失败')
      } finally {
        setLoading(false)
      }
    },
    [keyword, status, language, page, pageSize],
  )

  const handleDelete = (record: ProjectSummary) => {
    modal.confirm({
      title: '删除项目',
      content: `将删除「${record.name}」以及它的讲稿和设置，已生成的视频文件会保留。是否继续？`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        const result = await deletePptVideoProject(record.id)
        if (!result.success) {
          message.error(result.message)
          return
        }
        message.success(result.message)
        await load()
      },
    })
  }

  const columns: ColumnsType<ProjectSummary> = [
    {
      title: '项目',
      dataIndex: 'name',
      render: (_value, record) => (
        <div className="flex items-center gap-2.5">
          <Thumb src={record.thumbnail_url} alt={record.name} />
          <div className="min-w-0">
            <Typography.Link onClick={() => router.push(`/agent/ppt-videos/${record.id}`)} className="block truncate">
              {record.name}
            </Typography.Link>
            <Typography.Text type="secondary" className="block truncate text-[11px]">
              {record.source_filename}
            </Typography.Text>
          </div>
        </div>
      ),
    },
    {
      title: '页数',
      dataIndex: 'slide_count',
      width: 72,
      render: (value: number) => `${value} 页`,
    },
    {
      title: '默认配音',
      width: 150,
      render: (_value, record) => (
        <Space size={4} wrap>
          <Tag className="!m-0">{LANGUAGE_LABEL[record.default_language]}</Tag>
          <Typography.Text type="secondary" className="text-[12px]">
            {voiceLabel(voices.find((voice) => voice.voice_id === record.default_voice_id)?.display_name)} ·{' '}
            {record.speed.toFixed(2)} 倍
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (value: string, record) => {
        const tag = <Tag color={STATUS_COLOR[value]}>{PROJECT_STATUS_LABEL[value] ?? value}</Tag>
        if (value === 'failed' && record.latest_error) {
          return <Tooltip title={record.latest_error}>{tag}</Tooltip>
        }
        return tag
      },
    },
    {
      title: '版本',
      dataIndex: 'version_count',
      width: 72,
      render: (value: number) => `${value} 个`,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 160,
      render: (value: string | null) => (
        <Typography.Text type="secondary" className="text-[12px]">
          {value ? new Date(value).toLocaleString('zh-CN') : '-'}
        </Typography.Text>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      render: (_value, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => router.push(`/agent/ppt-videos/${record.id}`)}>
            继续制作
          </Button>
          {record.preview_url && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => setPreview({ src: record.preview_url, title: record.name })}
            >
              预览
            </Button>
          )}
          {record.latest_version_id && (
            <Button
              type="link"
              size="small"
              icon={<CloudDownloadOutlined />}
              href={`/api/v1/agent/ppt-videos/versions/${record.latest_version_id}/file`}
              download
            >
              下载
            </Button>
          )}
          <PermissionGate code={PERM.pptVideoManage}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>
              删除
            </Button>
          </PermissionGate>
        </Space>
      ),
    },
  ]

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Space size={8} wrap>
          <Input
            allowClear
            prefix={<SearchOutlined className="text-[#A4A097]" />}
            placeholder="按项目名搜索"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onPressEnter={() => {
              setPage(1)
              void load(1)
            }}
            style={{ width: 220 }}
          />
          <Select
            allowClear
            placeholder="全部状态"
            value={status}
            onChange={(value) => {
              setStatus(value)
              setPage(1)
              void load(1)
            }}
            style={{ width: 120 }}
            options={Object.entries(PROJECT_STATUS_LABEL).map(([value, label]) => ({ value, label }))}
          />
          <Select
            allowClear
            placeholder="全部语言"
            value={language}
            onChange={(value) => {
              setLanguage(value)
              setPage(1)
              void load(1)
            }}
            style={{ width: 120 }}
            options={[
              { value: 'zh', label: '中文' },
              { value: 'en', label: '英文' },
            ]}
          />
          <Button
            onClick={() => {
              setPage(1)
              void load(1)
            }}
          >
            查询
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => void load()} />
        </Space>

        <PermissionGate code={PERM.pptVideoManage}>
          <Space size={8}>
            <Button icon={<RobotOutlined />} onClick={() => setAiOpen(true)}>
              模型配置
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setUploadOpen(true)}>
              新建配音视频
            </Button>
          </Space>
        </PermissionGate>
      </div>

      {error && (
        <Alert
          type="error"
          showIcon
          message="列表加载失败"
          description={error}
          action={
            <Button size="small" onClick={() => void load()}>
              重试
            </Button>
          }
        />
      )}

      <Table<ProjectSummary>
        rowKey="id"
        size="middle"
        loading={loading}
        columns={columns}
        dataSource={items}
        scroll={{ x: 980 }}
        locale={{ emptyText: '还没有项目，点右上角「新建配音视频」上传 PPT' }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (value) => `共 ${value} 个项目`,
          onChange: (nextPage, nextPageSize) => {
            setPage(nextPage)
            setPageSize(nextPageSize)
            void load(nextPage, nextPageSize)
          },
        }}
        footer={
          total > 0
            ? () => (
                <Typography.Text type="secondary" className="text-[12px]">
                  共 {total} 个项目；单个项目可保留多个版本，旧版本不自动清理
                </Typography.Text>
              )
            : undefined
        }
      />

      {uploadOpen && <PptUploadModal open voices={voices} onClose={() => setUploadOpen(false)} />}

      <AiConfigDrawer
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        mode="global"
        configs={aiConfigs}
        onConfigsChange={setAiConfigs}
      />

      <VideoPreviewModal
        open={preview !== null}
        src={preview?.src}
        title={preview?.title}
        fileName={preview?.title}
        onClose={() => setPreview(null)}
      />
    </div>
  )
}