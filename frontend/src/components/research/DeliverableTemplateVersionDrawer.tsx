'use client'

import { useEffect, useState } from 'react'
import { Alert, App, Button, Drawer, Popconfirm, Space, Table, Tag, Tooltip } from 'antd'
import { DeleteOutlined, DownloadOutlined, EyeOutlined, UndoOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { fetchDeliverableTemplateVersions, type DocGenTemplateVersion } from '@/lib/api/client/research/doc-gen'
import { deleteDeliverableTemplateVersion, restoreDeliverableTemplateVersion } from '@/actions/research/doc-gen'

interface Props {
  open: boolean
  /** 目标模板 ID；关闭抽屉时为 null */
  templateId: string | null
  templateName: string
  onClose: () => void
  /** 回滚后当前生效母本已变，通知父组件刷新模板列表 */
  onChanged: () => void
  /** 预览某个历史版本（复用父组件的预览弹窗，避免重复实现 docx 渲染） */
  onPreview: (version: DocGenTemplateVersion) => void
  /** 下载某个历史版本（复用父组件的 blob 保存逻辑） */
  onDownload: (version: DocGenTemplateVersion) => void
}

function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * 交付物模板的版本历史。
 *
 * 只做「查看/下载/回滚/删除留档」：回滚由后端以目标版本内容新建一个版本并设为当前，
 * 历史记录不可改写，所以这里不存在「编辑某条历史」的操作。
 */
export function DeliverableTemplateVersionDrawer({
  open,
  templateId,
  templateName,
  onClose,
  onChanged,
  onPreview,
  onDownload,
}: Props) {
  const { message: msgApi } = App.useApp()
  const [versions, setVersions] = useState<DocGenTemplateVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  /** 递增即重新拉取列表（回滚/删除后刷新） */
  const [reloadKey, setReloadKey] = useState(0)

  // 父组件以模板 ID 作为 key 挂载本组件，切换模板时状态天然从零开始，无需在 effect 里清空
  useEffect(() => {
    if (!open || !templateId) return
    let cancelled = false
    const fetchVersions = async () => {
      setLoading(true)
      try {
        const data = await fetchDeliverableTemplateVersions(templateId)
        if (!cancelled) setVersions(data)
      } catch (e) {
        if (!cancelled) msgApi.error(e instanceof Error ? e.message : '加载版本历史失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void fetchVersions()
    return () => {
      cancelled = true
    }
  }, [open, templateId, reloadKey, msgApi])

  const handleRestore = async (version: DocGenTemplateVersion) => {
    if (!templateId) return
    setBusyId(version.id)
    try {
      const result = await restoreDeliverableTemplateVersion(templateId, version.id)
      msgApi.success(`已回滚到 v${result.from_version_no}，当前生效版本为 v${result.version_no}`)
      setReloadKey((k) => k + 1)
      onChanged()
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '回滚失败')
    } finally {
      setBusyId(null)
    }
  }

  const handleDelete = async (version: DocGenTemplateVersion) => {
    if (!templateId) return
    setBusyId(version.id)
    try {
      await deleteDeliverableTemplateVersion(templateId, version.id)
      msgApi.success(`已删除 v${version.version_no}`)
      setReloadKey((k) => k + 1)
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    } finally {
      setBusyId(null)
    }
  }

  const columns = [
    {
      title: '版本',
      key: 'version_no',
      width: 110,
      render: (_: unknown, record: DocGenTemplateVersion) => (
        <Space size={4}>
          <span style={{ fontWeight: 600 }}>v{record.version_no}</span>
          {record.is_current && <Tag color="green">当前生效</Tag>}
        </Space>
      ),
    },
    {
      title: 'Word 母本',
      key: 'file',
      width: 240,
      render: (_: unknown, record: DocGenTemplateVersion) => (
        <Space size={4} wrap>
          <span>{record.file_name || '—'}</span>
          <Tag>{record.file_ext ?? '.docx'}</Tag>
          <span style={{ color: '#999', fontSize: 12 }}>{formatFileSize(record.file_size)}</span>
        </Space>
      ),
    },
    {
      title: '填充项配置',
      key: 'template_code',
      width: 180,
      render: (_: unknown, record: DocGenTemplateVersion) =>
        record.template_code ? <Tag color="blue">{record.template_code}</Tag> : <span style={{ color: '#999' }}>—</span>,
    },
    {
      title: '版本说明',
      key: 'change_note',
      width: 220,
      render: (_: unknown, record: DocGenTemplateVersion) =>
        record.change_note ? (
          <Tooltip title={record.change_note}>
            <span style={{ display: 'inline-block', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {record.change_note}
            </span>
          </Tooltip>
        ) : (
          <span style={{ color: '#999' }}>—</span>
        ),
    },
    {
      title: '上传人',
      key: 'created_by',
      width: 130,
      render: (_: unknown, record: DocGenTemplateVersion) => record.created_by_name || <span style={{ color: '#999' }}>—</span>,
    },
    {
      title: '上传时间',
      key: 'created_at',
      width: 160,
      render: (_: unknown, record: DocGenTemplateVersion) => dayjs(record.created_at).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 210,
      fixed: 'right' as const,
      render: (_: unknown, record: DocGenTemplateVersion) => (
        <Space size={0}>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => onPreview(record)}>
            预览
          </Button>
          <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => onDownload(record)}>
            下载
          </Button>
          {!record.is_current && (
            <>
              <Popconfirm
                title={`回滚到 v${record.version_no}？`}
                description="将以该版本内容生成一个新的当前生效版本，历史记录不会被改写。"
                onConfirm={() => void handleRestore(record)}
              >
                <Button type="link" size="small" icon={<UndoOutlined />} loading={busyId === record.id}>
                  回滚
                </Button>
              </Popconfirm>
              <Popconfirm
                title={`删除 v${record.version_no}？`}
                description="仅移除该留档记录，不影响当前生效母本。"
                onConfirm={() => void handleDelete(record)}
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />} loading={busyId === record.id} />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Drawer
      title={`版本历史：${templateName}`}
      open={open}
      onClose={onClose}
      styles={{ wrapper: { width: 1080 } }}
      destroyOnHidden
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        title="每次上传或替换母本都会留档一个版本"
        description="回滚会以所选版本的内容新建一个版本并设为当前生效，因此历史可追溯、也可再回滚回来。当前生效版本不能删除。"
      />
      <Table
        rowKey="id"
        dataSource={versions}
        columns={columns}
        loading={loading}
        size="small"
        pagination={false}
        scroll={{ x: 1000 }}
        locale={{ emptyText: '该模板尚未上传 Word 母本，暂无版本记录' }}
      />
    </Drawer>
  )
}
