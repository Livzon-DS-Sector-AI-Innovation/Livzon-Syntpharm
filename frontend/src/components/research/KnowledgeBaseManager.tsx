'use client'

/**
 * 项目知识库管理面板（可复用）。
 *
 * 两个入口共用同一份实现，避免行为走偏：
 * - 独立页面：`/research/knowledge-bases`（variant="page"，项目由页面选择器传进来）
 * - 新建报告弹窗内的嵌套弹窗（variant="modal"，projectId 由新建报告弹窗传入）
 */
import { useCallback, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  Popconfirm,
  Progress,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from 'antd'
import type { UploadFile } from 'antd'
import {
  CloudUploadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileSearchOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  downloadKbDocument,
  fetchKbLimits,
  uploadKbDocuments,
} from '@/lib/api/client/research/knowledge-base'
import {
  createKnowledgeBase,
  deleteKbDocument,
  deleteKnowledgeBase,
  reparseKbDocument,
} from '@/actions/research/knowledge-base'
import { KbDocumentPreviewModal } from './KbDocumentPreviewModal'
import {
  chunkMethodLabel,
  formatBytes,
  KB_RUN_COLORS,
  KB_RUN_LABELS,
  KB_STATUS_COLORS,
  KB_STATUS_LABELS,
  kbProgressPercent,
  type KbDocumentItem,
} from '@/types/research/knowledge-base'
import { summarizeKb, useKbDocuments, useKnowledgeBase } from './useKnowledgeBase'
import { KB_COPY } from '@/lib/ui/research-copy'

interface Props {
  projectId: string
  variant: 'page' | 'modal'
  /** 库/文档发生变化时通知父组件（例如新建报告弹窗刷新摘要） */
  onChanged?: () => void
}

export function KnowledgeBaseManager({ projectId, variant, onChanged }: Props) {
  const { message: msgApi } = App.useApp()
  const queryClient = useQueryClient()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [previewDoc, setPreviewDoc] = useState<KbDocumentItem | null>(null)
  const [downloadingId, setDownloadingId] = useState<string>('')
  const [reparsingId, setReparsingId] = useState<string>('')
  const [form] = Form.useForm<{ name?: string; description?: string }>()

  const { data: limits } = useQuery({
    queryKey: ['kb-limits'],
    queryFn: fetchKbLimits,
    staleTime: 5 * 60 * 1000,
  })

  const { data: knowledgeBases = [] } = useKnowledgeBase(projectId)
  const kb = knowledgeBases[0]

  const { data: documents = [], isFetching: documentsLoading } = useKbDocuments(kb?.id)
  const summary = summarizeKb(documents)

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['knowledge-bases', projectId] })
    queryClient.invalidateQueries({ queryKey: ['kb-documents', kb?.id] })
    onChanged?.()
  }, [queryClient, projectId, kb?.id, onChanged])

  const handleCreate = async () => {
    if (!projectId) {
      msgApi.warning('请先选择研发项目')
      return
    }
    const values = await form.validateFields()
    setCreating(true)
    try {
      await createKnowledgeBase({ project_id: projectId, name: values.name, description: values.description })
      msgApi.success('知识库已创建，可以开始上传资料')
      form.resetFields()
      invalidate()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '创建知识库失败')
    } finally {
      setCreating(false)
    }
  }

  const handleUpload = async () => {
    if (!kb) return
    const files = fileList.map((item) => item.originFileObj).filter(Boolean) as File[]
    if (!files.length) {
      msgApi.warning('请先选择要上传的文件')
      return
    }
    setUploading(true)
    try {
      const result = await uploadKbDocuments(kb.id, files)
      // 逐条说明哪份文件为什么没进去，避免用户反复重试同一个不支持的文件
      result.skipped?.forEach((item) => msgApi.warning(`${item.file_name}：${item.reason}`))
      msgApi.success(`已上传 ${result.uploaded?.length ?? 0} 份资料，正在入库处理`)
      setFileList([])
      invalidate()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteDocument = async (record: KbDocumentItem) => {
    if (!kb) return
    try {
      await deleteKbDocument(kb.id, record.id)
      msgApi.success('已从知识库移除')
      invalidate()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const handleDownload = async (record: KbDocumentItem) => {
    if (!kb) return
    setDownloadingId(record.id)
    try {
      await downloadKbDocument(kb.id, record.id, record.file_name)
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '下载失败')
    } finally {
      setDownloadingId('')
    }
  }

  const handleReparse = async (record: KbDocumentItem) => {
    if (!kb || reparsingId) return
    setReparsingId(record.id)
    try {
      await reparseKbDocument(kb.id, record.id)
      msgApi.success('已重新提交处理，稍等一会儿再看状态')
      invalidate()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '重新提交失败，请稍后重试')
    } finally {
      setReparsingId('')
    }
  }

  const handleDeleteKb = async () => {
    if (!kb) return
    try {
      await deleteKnowledgeBase(kb.id)
      msgApi.success('知识库已删除')
      invalidate()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除知识库失败')
    }
  }

  const columns = [
    {
      title: '资料名称',
      dataIndex: 'file_name',
      key: 'file_name',
      ellipsis: true,
      render: (name: string) => <Tooltip title={name}>{name}</Tooltip>,
    },
    {
      title: '大小',
      dataIndex: 'size_bytes',
      key: 'size_bytes',
      width: 90,
      render: (value: number) => formatBytes(value),
    },
    {
      title: '处理状态',
      key: 'run',
      width: 200,
      render: (_: unknown, record: KbDocumentItem) => (
        <Space direction="vertical" size={2} style={{ width: '100%' }}>
          <Tag color={KB_RUN_COLORS[record.run] ?? 'default'}>{KB_RUN_LABELS[record.run] ?? record.run}</Tag>
          {record.run === 'RUNNING' || record.run === 'UNSTART' ? (
            <Progress percent={kbProgressPercent(record)} size="small" status="active" />
          ) : null}
          {record.run === 'FAIL' && record.last_error ? (
            <Typography.Text type="danger" style={{ fontSize: 12 }} ellipsis={{ tooltip: record.last_error }}>
              {record.last_error}
            </Typography.Text>
          ) : null}
        </Space>
      ),
    },
    { title: '文字分段', dataIndex: 'chunk_count', key: 'chunk_count', width: 90 },
    {
      title: '操作',
      key: 'action',
      width: 300,
      render: (_: unknown, record: KbDocumentItem) => (
        <Space size={4}>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => setPreviewDoc(record)}>
            预览
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            loading={downloadingId === record.id}
            onClick={() => void handleDownload(record)}
          >
            下载
          </Button>
          <Button
            type="link"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => handleReparse(record)}
            loading={reparsingId === record.id}
            disabled={!['DONE', 'FAIL', 'CANCEL'].includes(record.run)}
            title={['DONE', 'FAIL', 'CANCEL'].includes(record.run) ? '重新处理这份资料' : '正在处理中，处理完才能重新提交'}
          >
            重新处理
          </Button>
          <Popconfirm
            title={KB_COPY.removeDocTitle}
            description={KB_COPY.removeDocDescription}
            okText="移除"
            okButtonProps={{ danger: true }}
            onConfirm={() => handleDeleteDocument(record)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              移除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  if (!projectId) {
    return (
      <Card>
        <Empty description="先在上面选一个项目，再来管理它的资料" />
      </Card>
    )
  }

  const uploadCard = (
    <Card
      title={KB_COPY.uploadTitle}
      size={variant === 'modal' ? 'small' : 'default'}
      style={{ marginBottom: 16 }}
      extra={
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          单次最多 {limits?.max_files ?? 10} 个，单文件 ≤ {limits?.max_file_mb ?? 100}MB
        </Typography.Text>
      }
    >
      <Upload.Dragger
        multiple
        fileList={fileList}
        beforeUpload={() => false}
        onChange={({ fileList: next }) => setFileList(next)}
        accept={(limits?.allowed_extensions ?? []).join(',')}
      >
        <p className="ant-upload-drag-icon">
          <CloudUploadOutlined />
        </p>
        <p className="ant-upload-text">点击或把资料拖到这里</p>
        <p className="ant-upload-hint">
          支持 PDF、Word、Excel、PPT、文本、图片等。选好文件后点下面的按钮，系统会自动处理成可检索的文字。
        </p>
      </Upload.Dragger>
      <Space style={{ marginTop: 12 }}>
        <Button type="primary" icon={<FileSearchOutlined />} loading={uploading} onClick={handleUpload}>
          上传并处理
        </Button>
        <Button disabled={!fileList.length || uploading} onClick={() => setFileList([])}>
          清空选择
        </Button>
      </Space>
    </Card>
  )

  return (
    <div>
      {limits && !limits.configured ? (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title={KB_COPY.notConfiguredTitle}
          description={KB_COPY.notConfiguredDescription}
        />
      ) : null}

      {!kb ? (
        <Card title="这个项目还没有知识库，先创建一个" size={variant === 'modal' ? 'small' : 'default'}>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            title="一个项目只需要建一个知识库"
            description="建好之后，这个项目的资料都传到里面，AI 写报告时会自动到这里找依据。"
          />
          <Form form={form} layout="vertical" style={{ maxWidth: 480 }}>
            <Form.Item name="name" label="知识库名称（可以不填）">
              <Input placeholder="留空就用项目名，例如「米诺地尔项目知识库」" maxLength={200} />
            </Form.Item>
            <Form.Item name="description" label="用途说明（可以不填）">
              <Input.TextArea rows={2} placeholder="简单写一句这里放什么资料，例如：工艺与注册资料" maxLength={1000} />
            </Form.Item>
            <Button type="primary" icon={<PlusOutlined />} loading={creating} onClick={handleCreate}>
              创建知识库
            </Button>
          </Form>
        </Card>
      ) : (
        <>
          <Card style={{ marginBottom: 16 }} size={variant === 'modal' ? 'small' : 'default'}>
            <Descriptions
              size="small"
              column={variant === 'modal' ? 3 : 4}
              title={
                <Space>
                  <span>{kb.name}</span>
                  <Tag color={KB_STATUS_COLORS[kb.status] ?? 'default'}>
                    {KB_STATUS_LABELS[kb.status] ?? kb.status}
                  </Tag>
                  <Popconfirm
                    title={KB_COPY.deleteTitle}
                    description={KB_COPY.deleteDescription}
                    okText="删除"
                    okButtonProps={{ danger: true }}
                    onConfirm={handleDeleteKb}
                  >
                    <Button type="link" size="small" danger>
                      删除知识库
                    </Button>
                  </Popconfirm>
                </Space>
              }
            >
              <Descriptions.Item label="资料数">{summary.total || kb.document_count}</Descriptions.Item>
              <Descriptions.Item label="已入库">{summary.parsed}</Descriptions.Item>
              <Descriptions.Item label="入库中">{summary.parsing}</Descriptions.Item>
              <Descriptions.Item label="排队中">{summary.queued}</Descriptions.Item>
              <Descriptions.Item label="处理失败">{summary.failed}</Descriptions.Item>
              <Descriptions.Item label="已取消">{summary.cancelled}</Descriptions.Item>
              <Descriptions.Item label="文字分段数">{kb.chunk_count}</Descriptions.Item>
              <Descriptions.Item label="分段方式">{chunkMethodLabel(kb.chunk_method)}</Descriptions.Item>
              <Descriptions.Item label="检索模型" span={2}>
                {kb.embedding_model || '-'}
              </Descriptions.Item>
            </Descriptions>
            {kb.description ? (
              <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                {kb.description}
              </Typography.Paragraph>
            ) : null}
          </Card>

          {uploadCard}

          <Card
            title="资料与处理进度"
            size={variant === 'modal' ? 'small' : 'default'}
            extra={
              <Space>
                {summary.pending > 0 ? <Tag color="processing">{summary.pending} 份处理中</Tag> : null}
                <Button size="small" icon={<ReloadOutlined />} loading={documentsLoading} onClick={invalidate}>
                  刷新
                </Button>
              </Space>
            }
          >
            <Table
              rowKey="id"
              size="small"
              loading={documentsLoading && !documents.length}
              dataSource={documents}
              columns={columns}
              pagination={{ pageSize: variant === 'modal' ? 5 : 20, hideOnSinglePage: true }}
              locale={{
                emptyText: (
                  <Empty description="还没有上传资料。上传后会排队自动处理，处理完 AI 就能检索到里面的内容。" />
                ),
              }}
            />
          </Card>
        </>
      )}

      {/* 预览原文与解析内容：文件本体在 RAGFlow，按需回源取流 */}
      <KbDocumentPreviewModal
        kbId={kb?.id ?? ''}
        document={previewDoc}
        open={previewDoc !== null}
        onClose={() => setPreviewDoc(null)}
      />
    </div>
  )
}
