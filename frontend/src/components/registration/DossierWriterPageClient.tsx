'use client'

import { useEffect, useState } from 'react'
import {
  Table, Space, Modal, Form, Input, Select, Popconfirm, App,
} from 'antd'
import { FileWordOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import dayjs from 'dayjs'
import { useDossierWriterStore } from '@/stores/dossier-writer'
import {
  createProductDossier, deleteProductDossier, parseTemplates,
} from '@/actions/dossier-writer'
import { uploadTemplates } from '@/actions/dossier-writer'
import type { ProductDossier, ProductDossierCreate } from '@/types/dossier-writer'
import type { UploadResponse } from '@/types/dossier-writer'
import { RegistrationPageHeader } from './RegistrationPageHeader'
import ui from './registration-ui.module.css'
import { IconEdit, IconPlus, IconTrash } from './registration-icons'

const STERILE_OPTIONS = [
  { label: '无菌', value: '无菌' },
  { label: '非无菌', value: '非无菌' },
]

// 状态语义：紫=品牌/蓝=信息/橙=进行中/绿=完成/红=失败，灰=初始
const STATUS_MAP: Record<string, { className: string; label: string }> = {
  draft: { className: ui.tagPlain, label: '草稿' },
  template_uploaded: { className: ui.tagBrand, label: '模板已上传' },
  parsed: { className: ui.tagInfo, label: '已解析' },
  editing: { className: ui.tagWarn, label: '撰写中' },
  exported: { className: ui.tagOk, label: '已导出' },
  failed: { className: ui.tagRisk, label: '处理失败' },
}

const PARSE_STATUS_MAP: Record<string, { className: string; label: string }> = {
  pending: { className: ui.tagPlain, label: '待上传' },
  template_uploaded: { className: ui.tagBrand, label: '待解析' },
  parsing: { className: ui.tagWarn, label: '解析中' },
  parsed: { className: ui.tagOk, label: '已解析' },
  failed: { className: ui.tagRisk, label: '解析失败' },
}

export function DossierWriterPageClient() {
  const { message } = App.useApp()
  const router = useRouter()
  const { dossiers, dossiersTotal, dossiersLoading, loadDossiers } = useDossierWriterStore()
  
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [parsingId, setParsingId] = useState<string | null>(null)
  const [currentDossier, setCurrentDossier] = useState<ProductDossier | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadDossiers()
  }, [loadDossiers])

  // 新增品种资料
  const handleAdd = async (values: ProductDossierCreate) => {
    setSubmitting(true)
    try {
      const dossier = await createProductDossier(values)
      message.success('创建成功')
      setAddModalOpen(false)
      form.resetFields()
      
      // 打开上传模板弹窗
      setCurrentDossier(dossier)
      setUploadModalOpen(true)
      loadDossiers()
    } catch (err: unknown) {
      const msg = (err instanceof Error ? err.message : null) || (err as { detail?: string })?.detail || '创建失败'
      message.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  // 上传模板（支持多文件）
  const handleUploadTemplate = async (files: FileList | null) => {
    if (!currentDossier || !files || files.length === 0) return
    
    try {
      const _fileArray = Array.from(files)
      const result: UploadResponse = await uploadTemplates(currentDossier.id, files)
      
      if (result.success_count > 0) {
        message.success(`上传成功 ${result.success_count} 个文件`)
      }
      if (result.failed_count > 0) {
        const failedFiles = result.results.filter(r => r.status === 'failed').map(r => r.filename).join(', ')
        message.warning(`${result.failed_count} 个文件上传失败: ${failedFiles}`)
      }
      
      setUploadModalOpen(false)
      loadDossiers()
    } catch (err: unknown) {
      const msg = (err instanceof Error ? err.message : null) || (err as { detail?: string })?.detail || '上传失败'
      message.error(msg)
    }
  }

  // 删除品种资料
  const handleDelete = async (id: string) => {
    try {
      await deleteProductDossier(id)
      message.success('删除成功')
      loadDossiers()
    } catch {
      message.error('删除失败')
    }
  }

  // 查看详情
  const handleView = (id: string) => {
    router.push(`/registration/dossier-writer/${id}`)
  }

  // 重新解析（绑定到当前品种）
  const handleReparse = async (dossier: ProductDossier) => {
    setParsingId(dossier.id)
    try {
      const result = await parseTemplates(dossier.id)
      if (result.success) {
        message.success(result.message)
        // 解析成功后自动进入详情页
        router.push(`/registration/dossier-writer/${dossier.id}`)
      } else {
        message.error(result.message || result.error || '解析失败')
      }
      loadDossiers()
    } catch (err: unknown) {
      const msg = (err instanceof Error ? err.message : null) || (err as { detail?: string })?.detail || '解析失败'
      message.error(msg)
    } finally {
      setParsingId(null)
    }
  }

  const columns = [
    {
      title: '品种名称',
      dataIndex: 'product_name',
      key: 'product_name',
      width: '25%',
      render: (text: string) => <span className="font-medium">{text}</span>,
    },
    {
      title: '无菌类型',
      dataIndex: 'sterile_type',
      key: 'sterile_type',
      width: '12%',
      render: (text: string) => <span className={ui.tagInfo}>{text}</span>,
    },
    {
      title: '生产商',
      dataIndex: 'manufacturer',
      key: 'manufacturer',
      width: '25%',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '10%',
      render: (status: string) => {
        const s = STATUS_MAP[status] || { className: ui.tagPlain, label: status }
        return <span className={s.className}>{s.label}</span>
      },
    },
    {
      title: '解析状态',
      dataIndex: 'parse_status',
      key: 'parse_status',
      width: '12%',
      render: (status: string, record: ProductDossier) => {
        const s = PARSE_STATUS_MAP[status] || { className: ui.tagPlain, label: status }
        return (
          <Space size={6}>
            <span className={s.className}>{s.label}</span>
            {record.chapter_count > 0 && (
              <span className="text-xs text-gray-500">{record.chapter_count}章</span>
            )}
          </Space>
        )
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: '15%',
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: '15%',
      render: (_: unknown, record: ProductDossier) => (
        <Space size={10}>
          <button
            type="button"
            className={ui.opLink}
            onClick={() => {
              setCurrentDossier(record)
              setUploadModalOpen(true)
            }}
          >
            上传模板
          </button>
          <button
            type="button"
            className={ui.opLink}
            onClick={() => handleView(record.id)}
            disabled={record.parse_status !== 'parsed'}
            style={record.parse_status !== 'parsed' ? { color: 'var(--ink-3)', cursor: 'not-allowed' } : undefined}
          >
            查看
          </button>
          <button
            type="button"
            className={ui.opLink}
            onClick={() => handleReparse(record)}
            disabled={parsingId === record.id || record.parse_status === 'pending'}
            style={record.parse_status === 'pending' ? { color: 'var(--ink-3)', cursor: 'not-allowed' } : undefined}
          >
            {parsingId === record.id ? '解析中…' : '解析'}
          </button>
          <Popconfirm
            title="确定删除此品种资料？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <button type="button" className={ui.opDel} title="删除">
              {IconTrash}
            </button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <App>
    <div className={ui.regUi}>
      <RegistrationPageHeader
        icon={IconEdit}
        title="申报资料撰写"
        sub="基于模板的原料药申报资料撰写工具"
        actions={
          <button type="button" className={ui.btnPrimary} onClick={() => setAddModalOpen(true)}>
            {IconPlus}
            新增品种资料
          </button>
        }
      />

      {/* 列表 */}
      <div className={ui.panel}>
        <div className={`${ui.tableWrap} ${ui.tableStd}`}>
          <Table
            columns={columns}
            dataSource={dossiers}
            rowKey="id"
            loading={dossiersLoading}
            pagination={{
              total: dossiersTotal,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条`,
            }}
          />
        </div>
      </div>

      {/* 新增品种资料弹窗 */}
      <Modal
        title="新增品种资料"
        open={addModalOpen}
        onCancel={() => { setAddModalOpen(false); form.resetFields() }}
        onOk={() => form.submit()}
        confirmLoading={submitting}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item
            name="product_name"
            label="品种名称"
            rules={[{ required: true, message: '请输入品种名称' }]}
          >
            <Input placeholder="请输入品种名称" />
          </Form.Item>
          
          <Form.Item
            name="sterile_type"
            label="无菌/非无菌"
            rules={[{ required: true, message: '请选择无菌类型' }]}
          >
            <Select placeholder="请选择" options={STERILE_OPTIONS} />
          </Form.Item>
          
          <Form.Item
            name="manufacturer"
            label="生产商"
            rules={[{ required: true, message: '请输入生产商名称' }]}
          >
            <Input placeholder="请输入生产商名称" />
          </Form.Item>
          
          <Form.Item
            name="template_original_product_name"
            label="模板原品种名称（可选）"
          >
            <Input placeholder="模板中的原品种名称，用于替换" />
          </Form.Item>
          
          <Form.Item
            name="template_original_manufacturer"
            label="模板原生产商（可选）"
          >
            <Input placeholder="模板中的原生产商名称，用于替换" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 上传模板弹窗 */}
      <Modal
        title="上传申报资料模板"
        open={uploadModalOpen}
        onCancel={() => setUploadModalOpen(false)}
        footer={null}
        width={500}
      >
        <div className="py-4">
          <p className="mb-4 text-gray-600">
            请上传 Word 格式的申报资料模板文件（.docx），支持多文件批量上传
          </p>
          <div className="border-2 border-dashed rounded-lg p-8 text-center" style={{ borderColor: 'var(--line)' }}>
            <FileWordOutlined className="text-4xl mb-4" style={{ color: 'var(--brand-500)' }} />
            <p className="mb-4">点击或拖拽文件到此处上传（可多选）</p>
            <input
              type="file"
              accept=".docx"
              multiple
              onChange={(e) => {
                handleUploadTemplate(e.target.files)
              }}
              className="hidden"
              id="template-upload"
            />
            <label htmlFor="template-upload" className={ui.btnPrimary} style={{ cursor: 'pointer' }}>
              选择文件
            </label>
          </div>
        </div>
      </Modal>
    </div>
    </App>
  )
}
