'use client'

import {useState, useRef, useEffect} from 'react'
import {
  Table,
  Button,
  Input,
  message,
  Modal,
  Form,
  Tag,
  Space,
  Popconfirm,
  Select,
} from 'antd'
import {
  UploadOutlined,
  SearchOutlined,
  FileTextOutlined,
  DeleteOutlined,
  EyeOutlined,
  EditOutlined,
} from '@ant-design/icons'
import { useRegulationStore } from '@/stores/regulation'
import type { Regulation } from '@/lib/api/client/administration/regulation'
import { extractRegulationText } from '@/actions/administration'
import type { ColumnsType } from 'antd/es/table'

const API_BASE = '/api/v1'

function isEmbeddedBrowser(): boolean {
  const ua = navigator.userAgent.toLowerCase()
  return (
    ua.includes('electron') ||
    ua.includes('vscode') ||
    (window as unknown as { __vscodeWebview?: unknown }).__vscodeWebview !== undefined
  )
}

const CATEGORY_OPTIONS = [
  { value: '人事', label: '人事' },
  { value: '行政', label: '行政' },
  { value: '其它', label: '其它' },
]

const CATEGORY_COLORS: Record<string, string> = {
  人事: 'blue',
  行政: 'green',
  其它: 'default',
}

export default function RegulationClient() {
  const {
    regulations,
    loading,
    total: _total,
    keyword,
    setKeyword,
    loadRegulations,
    addRegulation,
    removeRegulation,
    updateRegulationItem,
    searchRegulations,
  } = useRegulationStore()

  const [uploading, setUploading] = useState(false)
  const [previewRegulation, setPreviewRegulation] = useState<Regulation | null>(null)
  const [editRegulation, setEditRegulation] = useState<Regulation | null>(null)
  const [editForm] = Form.useForm()
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<Array<{
    id: string
    file: File
    title: string
    category: string
    version: string
    content: string
    extracting: boolean
  }>>([])
  const fileInputRef = useRef<HTMLInputElement>(null)


  useEffect(() => {
    loadRegulations()
  }, [loadRegulations])

  const filteredRegulations = keyword.trim() ? searchRegulations(keyword) : regulations

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        const result = reader.result as string
        resolve(result.split(',')[1])
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const newItems = await Promise.all(
      files.map(async (file) => {
        let content = ''
        // 文本文件自动读取
        if (file.type.startsWith('text/') || file.name.endsWith('.md') || file.name.endsWith('.txt')) {
          content = await new Promise<string>((resolve) => {
            const reader = new FileReader()
            reader.onload = () => resolve(String(reader.result || ''))
            reader.onerror = () => resolve('')
            reader.readAsText(file)
          })
        }
        return {
          id: `${Date.now()}_${Math.random().toString(36).slice(2)}`,
          file,
          title: file.name.replace(/\.[^/.]+$/, ''),
          category: '其它',
          version: '',
          content,
          extracting: false,
        }
      })
    )
    setPendingFiles((prev) => [...prev, ...newItems])
    e.target.value = ''
  }

  const updatePendingFile = (id: string, field: 'title' | 'category' | 'version' | 'content', value: string) => {
    setPendingFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    )
  }

  const removePendingFile = (id: string) => {
    setPendingFiles((prev) => prev.filter((item) => item.id !== id))
  }

  const handleAiExtract = async (id: string) => {
    const item = pendingFiles.find((f) => f.id === id)
    if (!item) return
    setPendingFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, extracting: true } : f))
    )
    try {
      const base64 = await fileToBase64(item.file)
      const { data } = await extractRegulationText({
        file_name: item.file.name,
        file_type: item.file.type || 'application/octet-stream',
        file_data: base64,
      })
      if (data?.text) {
        setPendingFiles((prev) =>
          prev.map((f) => (f.id === id ? { ...f, content: data.text } : f))
        )
        message.success(data.source === 'ai' ? 'AI识别完成' : '文本提取完成')
      } else {
        message.warning('未能提取到文本，请手动输入')
      }
    } catch (err: unknown) {
      message.error((err instanceof Error ? (err instanceof Error ? err.message : null) : null) || '识别失败')
    } finally {
      setPendingFiles((prev) =>
        prev.map((f) => (f.id === id ? { ...f, extracting: false } : f))
      )
    }
  }

  const handleSubmitUpload = async () => {
    if (pendingFiles.length === 0) {
      message.warning('请先选择文件')
      return
    }
    setUploading(true)
    try {
      for (const item of pendingFiles) {
        const base64 = await fileToBase64(item.file)
        await addRegulation({
          title: item.title,
          content: item.content,
          category: item.category,
          version: item.version,
          file_name: item.file.name,
          file_type: item.file.type || 'application/octet-stream',
          file_data: base64,
        })
      }
      message.success(`已上传 ${pendingFiles.length} 个文件`)
      setUploadModalOpen(false)
      setPendingFiles([])
    } catch (err: unknown) {
      message.error((err instanceof Error ? (err instanceof Error ? err.message : null) : null) || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleSaveEdit = async () => {
    const values = await editForm.validateFields()
    if (editRegulation) {
      await updateRegulationItem(editRegulation.id, {
        title: values.title,
        category: values.category,
        version: values.version,
      })
      message.success('保存成功')
      setEditRegulation(null)
    }
  }

  const handleDelete = async (record: Regulation) => {
    try {
      await removeRegulation(record.id)
      message.success('已删除')
    } catch (err: unknown) {
      message.error((err instanceof Error ? (err instanceof Error ? err.message : null) : null) || '删除失败')
    }
  }

  const handleView = (record: Regulation) => {
    if (!record.file_data) {
      // 无附件，直接显示文本内容
      setPreviewRegulation(record)
      return
    }

    // 嵌入浏览器肯定打不开，直接弹提示
    if (isEmbeddedBrowser()) {
      setPreviewRegulation(record)
      return
    }

    // 正常浏览器尝试直接打开
    const url = `${API_BASE}/administration/regulations/${record.id}/file`
    const newWindow = window.open(url, '_blank')
    if (!newWindow) {
      // 被弹窗拦截，弹出提示
      setPreviewRegulation(record)
    }
  }

  const downloadFile = (record: Regulation) => {
    if (!record.file_data) return
    const binary = atob(record.file_data)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    const blob = new Blob([bytes], { type: record.file_type || 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = record.file_name || 'file.pdf'
    a.click()
    URL.revokeObjectURL(url)
  }

  const columns: ColumnsType<Regulation> = [
    {
      title: '制度名称',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => (
        <div className="flex items-center gap-2 text-base">
          <FileTextOutlined className="text-blue-500 text-base" />
          <span className="font-medium">{text}</span>
        </div>
      ),
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (text: string) => (
        <Tag color={CATEGORY_COLORS[text] || 'default'} className="text-base px-3 py-1">{text}</Tag>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 120,
      sorter: (a: Regulation, b: Regulation) => {
        const va = parseInt(a.version || '0', 10)
        const vb = parseInt(b.version || '0', 10)
        return va - vb
      },
      defaultSortOrder: 'descend',
      render: (text: string | null) => (
        <span className="text-lg text-gray-600">{text || '-'}</span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 320,
      render: (_: unknown, record: Regulation) => (
        <Space size="middle">
          <Button
            size="middle"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          <Button
            size="middle"
            icon={<EditOutlined />}
            onClick={() => {
              setEditRegulation(record)
              editForm.setFieldsValue({
                title: record.title,
                category: record.category,
                version: record.version,
              })
            }}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除「${record.title}」吗？`}
            onConfirm={() => handleDelete(record)}
          >
            <Button size="middle" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">公告通知</h1>
      <div className="flex justify-between items-center">
        <div className="flex gap-3 items-center">
          <Input
            placeholder="搜索制度名称或内容"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            prefix={<SearchOutlined />}
            className="w-72 text-base"
            size="large"
            allowClear
          />
          <Button
            icon={<UploadOutlined />}
            type="primary"
            size="large"
            onClick={() => {
              setUploadModalOpen(true)
              setTimeout(() => fileInputRef.current?.click(), 100)
            }}
          >
            上传制度文件
          </Button>
        </div>
      </div>

      <div className="max-w-6xl">
        <Table
          columns={columns}
          dataSource={filteredRegulations}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
          size="large"
          bordered
          className="[&_thead_th]:text-4xl [&_thead_th]:font-semibold"
        />
      </div>

      {/* Upload Modal */}
      <Modal
        open={uploadModalOpen}
        onCancel={() => {
          setUploadModalOpen(false)
          setPendingFiles([])
        }}
        title="上传制度文件"
        width={700}
        footer={null}
      >
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <Button icon={<UploadOutlined />} onClick={() => fileInputRef.current?.click()}>
              添加文件
            </Button>
            <span className="text-sm text-gray-500">已选择 {pendingFiles.length} 个文件</span>
          </div>

          <input
            type="file"
            ref={fileInputRef}
            accept=".txt,.md,.docx,.pdf"
            multiple
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />

          {pendingFiles.length === 0 && (
            <div className="text-center text-gray-400 py-8 border border-dashed rounded bg-gray-50">
              点击上方按钮选择文件
            </div>
          )}

          {pendingFiles.map((item) => (
            <div key={item.id} className="border rounded p-3 space-y-2 bg-gray-50">
              <div className="flex justify-between items-center">
                <span className="font-medium text-sm truncate max-w-[400px]">{item.file.name}</span>
                <Button size="small" danger onClick={() => removePendingFile(item.id)}>
                  删除
                </Button>
              </div>
              <Input
                placeholder="制度名称"
                value={item.title}
                onChange={(e) => updatePendingFile(item.id, 'title', e.target.value)}
                size="middle"
              />
              <div className="flex gap-2">
                <Select
                  placeholder="类别"
                  options={CATEGORY_OPTIONS}
                  value={item.category}
                  onChange={(value) => updatePendingFile(item.id, 'category', value)}
                  className="w-32"
                />
                <Input
                  placeholder="版本号，如 2025版"
                  value={item.version}
                  onChange={(e) => updatePendingFile(item.id, 'version', e.target.value)}
                  className="flex-1"
                />
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">制度内容（AI识别或手动输入）</span>
                  {(!item.content || item.content.length < 50) && (
                    <Button
                      size="small"
                      type="primary"
                      ghost
                      loading={item.extracting}
                      onClick={() => handleAiExtract(item.id)}
                    >
                      {item.extracting ? '识别中...' : 'AI识别内容'}
                    </Button>
                  )}
                </div>
                <Input.TextArea
                  placeholder="可手动输入制度内容，或点击上方按钮让AI自动识别"
                  value={item.content}
                  onChange={(e) => updatePendingFile(item.id, 'content', e.target.value)}
                  autoSize={{ minRows: 3, maxRows: 8 }}
                  className="text-sm"
                />
              </div>
            </div>
          ))}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              onClick={() => {
                setUploadModalOpen(false)
                setPendingFiles([])
              }}
            >
              取消
            </Button>
            <Button type="primary" loading={uploading} onClick={handleSubmitUpload}>
              提交上传
            </Button>
          </div>
        </div>
      </Modal>

      {/* Preview Modal */}
      <Modal
        open={!!previewRegulation}
        onCancel={() => setPreviewRegulation(null)}
        footer={null}
        title={<span className="text-lg font-semibold">{previewRegulation?.title}</span>}
        width={900}
      >
        {previewRegulation?.file_data ? (
          <div className="space-y-4">
            <div className="border rounded p-3 bg-yellow-50 text-sm text-gray-700 space-y-2">
              <p className="font-medium text-center">当前环境无法直接打开 PDF，建议在浏览器中打开</p>
              <div className="space-y-1 text-xs text-gray-600">
                <p className="font-medium">Edge 浏览器：</p>
                <p>地址栏输入 <code className="bg-gray-100 px-1 rounded">edge://settings/content/pdfDocuments</code> 回车</p>
                <p>关闭「下载 PDF 文件而不是在 Microsoft Edge 中自动打开它们」</p>
                <p className="font-medium mt-1">Chrome 浏览器：</p>
                <p>地址栏输入 <code className="bg-gray-100 px-1 rounded">chrome://settings/content/pdfDocuments</code> 回车</p>
                <p>关闭「下载 PDF 文件而不是在 Chrome 中自动打开它们」</p>
              </div>
              <div className="text-center pt-1">
                <Button
                  type="primary"
                  size="middle"
                  onClick={() => previewRegulation && downloadFile(previewRegulation)}
                >
                  下载文件
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="text-base text-gray-500 mb-2">
              文件：{previewRegulation?.file_name || '-'}
            </div>
            <div className="whitespace-pre-wrap text-base bg-gray-50 p-4 rounded max-h-[60vh] overflow-y-auto border">
              {previewRegulation?.content}
            </div>
          </>
        )}
      </Modal>

      {/* Edit Modal */}
      <Modal
        open={!!editRegulation}
        onCancel={() => setEditRegulation(null)}
        onOk={handleSaveEdit}
        title={<span className="text-lg font-semibold">编辑制度</span>}
        width={800}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="title"
            label="制度名称"
            rules={[{ required: true, message: '请输入制度名称' }]}
          >
            <Input placeholder="制度名称" />
          </Form.Item>
          <div className="flex gap-4">
            <Form.Item
              name="category"
              label="类别"
              className="flex-1"
              rules={[{ required: true, message: '请选择类别' }]}
            >
              <Select placeholder="选择类别" options={CATEGORY_OPTIONS} />
            </Form.Item>
            <Form.Item
              name="version"
              label="版本"
              className="flex-1"
            >
              <Input placeholder="版本号，如 2025版" />
            </Form.Item>
          </div>
        </Form>
      </Modal>

    </div>
  )
}
