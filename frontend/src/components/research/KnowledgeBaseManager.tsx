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
  formatBytes,
  KB_RUN_COLORS,
  KB_RUN_LABELS,
  KB_STATUS_COLORS,
  KB_STATUS_LABELS,
  kbProgressPercent,
  type KbDocumentItem,
} from '@/types/research/knowledge-base'
import { summarizeKb, useKbDocuments, useKnowledgeBase } from './useKnowledgeBase'

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
      msgApi.success(`已上传 ${result.uploaded?.length ?? 0} 份资料，正在解析`)
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
    if (!kb) return
    try {
      await reparseKbDocument(kb.id, record.id)
      msgApi.success('已重新提交解析')
      invalidate()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '重新解析失败')
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
      title: '文件名',
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
      title: '解析状态',
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
    { title: '切片', dataIndex: 'chunk_count', key: 'chunk_count', width: 70 },
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
            disabled={!['DONE', 'FAIL', 'CANCEL'].includes(record.run)}
          >
            重新解析
          </Button>
          <Popconfirm
            title="确定从知识库移除这份资料？"
            description="移除后 AI 生成报告时将不再参考它"
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
        <Empty description="请先选择研发项目" />
      </Card>
    )
  }

  const uploadCard = (
    <Card
      title="上传资料"
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
        <p className="ant-upload-text">点击或拖拽文件到此处</p>
        <p className="ant-upload-hint">支持 PDF、Word、Excel、PPT、文本、图片等；上传后自动开始解析</p>
      </Upload.Dragger>
      <Space style={{ marginTop: 12 }}>
        <Button type="primary" icon={<FileSearchOutlined />} loading={uploading} onClick={handleUpload}>
          上传并解析
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
          message="知识库服务尚未配置"
          description="请联系管理员在后端环境变量中配置 RAGFLOW__BASE_URL 与 RAGFLOW__API_KEY 后再使用本页功能。"
        />
      ) : null}

      {!kb ? (
        <Card title="该项目还没有知识库" size={variant === 'modal' ? 'small' : 'default'}>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message="一个项目只能有一个知识库，创建后会同步在知识库服务中生成对应数据集"
          />
          <Form form={form} layout="vertical" style={{ maxWidth: 480 }}>
            <Form.Item name="name" label="知识库名称">
              <Input placeholder="留空则按项目名自动生成" maxLength={200} />
            </Form.Item>
            <Form.Item name="description" label="用途说明">
              <Input.TextArea rows={2} placeholder="例如：米诺地尔项目工艺与注册资料" maxLength={1000} />
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
                    title="删除知识库？"
                    description="会同时删除知识库服务中的数据集与全部已解析内容，不可恢复"
                    onConfirm={handleDeleteKb}
                  >
                    <Button type="link" size="small" danger>
                      删除知识库
                    </Button>
                  </Popconfirm>
                </Space>
              }
            >
              <Descriptions.Item label="文档数">{summary.total || kb.document_count}</Descriptions.Item>
              <Descriptions.Item label="已解析">{summary.parsed}</Descriptions.Item>
              <Descriptions.Item label="解析中">{summary.pending}</Descriptions.Item>
              <Descriptions.Item label="解析失败">{summary.failed}</Descriptions.Item>
              <Descriptions.Item label="切片数">{kb.chunk_count}</Descriptions.Item>
              <Descriptions.Item label="切片方式">{kb.chunk_method}</Descriptions.Item>
              <Descriptions.Item label="向量模型" span={2}>
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
            title="资料与解析进度"
            size={variant === 'modal' ? 'small' : 'default'}
            extra={
              <Space>
                {summary.pending > 0 ? <Tag color="processing">{summary.pending} 份解析中</Tag> : null}
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
              locale={{ emptyText: <Empty description="还没有资料，上传后自动开始解析" /> }}
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
