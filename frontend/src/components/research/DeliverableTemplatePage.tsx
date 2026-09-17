'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert,
  App,
  Button,
  Card,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tag,
  Tooltip,
  Upload,
} from 'antd'
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  HistoryOutlined,
  InboxOutlined,
  PlusOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { renderAsync } from 'docx-preview'
import { fetchDeliverableTemplates } from '@/lib/api/client/research/rd-project'
import {
  downloadDeliverableTemplate,
  downloadDeliverableTemplateVersion,
  fetchDocGenSlotProfiles,
  uploadDeliverableTemplateFile,
  uploadDeliverableTemplates,
  type DocGenSlotProfile,
  type DocGenTemplateVersion,
} from '@/lib/api/client/research/doc-gen'
import {
  DELIVERABLE_TYPES,
  STAGE_LABELS,
  RdDeliverableTemplate,
  RdProjectStage,
} from '@/types/research/rd-project'
import {
  createDeliverableTemplate,
  deleteDeliverableTemplate,
  updateDeliverableTemplate,
} from '@/actions/research/rd-project'
import { DeliverableTemplateVersionDrawer } from './DeliverableTemplateVersionDrawer'

const { TextArea } = Input

const WORD_ACCEPT = '.docx,.dotx,.doc'

/** 预览目标：模板当前生效母本，或某个历史版本（versionId 缺省即当前版本） */
interface PreviewSource {
  title: string
  templateId: string
  versionId?: string
  ext: string
  /** 下载时的默认文件名 */
  fileName: string
}

/** 交付物模板管理：模板一律以 Word 模板原件（docx/dotx/doc）为准，支持在线预览与下载。 */
export function DeliverableTemplatePage() {
  const { message: msgApi } = App.useApp()
  const [templates, setTemplates] = useState<RdDeliverableTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [profiles, setProfiles] = useState<DocGenSlotProfile[]>([])

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<RdDeliverableTemplate | null>(null)
  const [form] = Form.useForm()

  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const [batchUploading, setBatchUploading] = useState(false)
  const [uploadingFile, setUploadingFile] = useState(false)

  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewSource, setPreviewSource] = useState<PreviewSource | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const previewRef = useRef<HTMLDivElement>(null)

  /** 版本历史抽屉的目标模板 */
  const [versionDrawer, setVersionDrawer] = useState<RdDeliverableTemplate | null>(null)

  /** 替换母本前收集版本说明（仅已有母本的模板需要，首次上传无需说明） */
  const [pendingNote, setPendingNote] = useState<{ record: RdDeliverableTemplate; file: File } | null>(null)
  const [pendingNoteText, setPendingNoteText] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      setTemplates(await fetchDeliverableTemplates())
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '加载模板列表失败')
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const init = async () => {
      await loadData()
      try {
        setProfiles(await fetchDocGenSlotProfiles())
      } catch {
        msgApi.error('加载填充项配置失败，可能是后端服务不可用')
      }
    }
    void init()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /** .doc 是旧二进制格式，docx-preview 无法渲染，由渲染分支直接给出提示 */
  const previewUnsupported = previewSource?.ext === '.doc'
  const previewNotice = previewUnsupported
    ? '该模板文件是 .doc 旧格式，浏览器无法在线预览，请下载后用 Word 打开'
    : previewError

  /** 预览：拉取模板原件字节流后交给 docx-preview 渲染 */
  useEffect(() => {
    if (!previewSource || previewSource.ext === '.doc') return
    let cancelled = false
    setPreviewLoading(true)
    setPreviewError(null)
    void (async () => {
      try {
        const blob = previewSource.versionId
          ? await downloadDeliverableTemplateVersion(previewSource.templateId, previewSource.versionId)
          : await downloadDeliverableTemplate(previewSource.templateId)
        if (cancelled || !previewRef.current) return
        previewRef.current.innerHTML = ''
        await renderAsync(blob, previewRef.current, undefined, { inWrapper: true, ignoreWidth: true })
      } catch (e) {
        if (!cancelled) setPreviewError(e instanceof Error ? e.message : '预览失败')
      } finally {
        if (!cancelled) setPreviewLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [previewSource])

  const openPreview = (source: PreviewSource) => {
    setPreviewSource(source)
    setPreviewOpen(true)
  }

  /** 预览当前生效母本 */
  const openTemplatePreview = (record: RdDeliverableTemplate) => {
    openPreview({
      title: record.name,
      templateId: record.id,
      ext: record.file_ext ?? '.docx',
      fileName: record.file_name ?? `${record.name}.docx`,
    })
  }

  /** 预览历史版本：标题带版本号，避免与当前生效版本混淆 */
  const openVersionPreview = (version: DocGenTemplateVersion) => {
    if (!versionDrawer) return
    openPreview({
      title: `${versionDrawer.name} · v${version.version_no}`,
      templateId: versionDrawer.id,
      versionId: version.id,
      ext: version.file_ext ?? '.docx',
      fileName: version.file_name ?? `${versionDrawer.name}-v${version.version_no}`,
    })
  }

  const saveBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const stageOptions = Object.keys(STAGE_LABELS).map((s) => ({ value: s, label: STAGE_LABELS[s as RdProjectStage] }))

  const deliverableOptions = Object.entries(DELIVERABLE_TYPES).flatMap(([stage, items]) =>
    items.map((item) => ({ value: item.type, label: `${STAGE_LABELS[stage as RdProjectStage]} - ${item.label}` })),
  )

  const openCreate = () => {
    setEditingTemplate(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true })
    setDrawerOpen(true)
  }

  const openEdit = (template: RdDeliverableTemplate) => {
    setEditingTemplate(template)
    form.setFieldsValue({
      name: template.name,
      stage: template.stage,
      deliverable_type: template.deliverable_type,
      description: template.description,
      template_code: template.template_code,
      template_content: template.template_content,
      is_active: template.is_active,
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingTemplate) {
        await updateDeliverableTemplate(editingTemplate.id, values)
        msgApi.success('更新成功')
      } else {
        await createDeliverableTemplate(values)
        msgApi.success('创建成功，请在列表中为该模板上传 Word 模板')
      }
      setDrawerOpen(false)
      void loadData()
    } catch (e) {
      // 表单校验失败：antd 会在字段下方标红，但不弹提示时用户会误以为「保存没反应」
      if (e && typeof e === 'object' && 'errorFields' in e) {
        msgApi.warning('请检查表单必填项后再保存')
        return
      }
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteDeliverableTemplate(id)
      msgApi.success('删除成功')
      void loadData()
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  /** 批量上传：拖进来的文件先攒着，确认无误再一次性提交，避免误触即写库 */
  const collectFile = (file: File) => {
    const ext = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
    if (!['.docx', '.dotx', '.doc'].includes(ext)) {
      msgApi.error(`不支持的格式：${file.name}（仅 .docx/.dotx/.doc）`)
      return Upload.LIST_IGNORE
    }
    setPendingFiles((prev) => [...prev, file])
    return false
  }

  /** 上传即提交：文档类型由后端按模板原件结构自动匹配，用户无需理解「填充项配置」 */
  const handleBatchSubmit = async () => {
    setBatchUploading(true)
    try {
      const result = await uploadDeliverableTemplates(pendingFiles)
      if (result.created.length > 0) {
        msgApi.success(`已识别并创建 ${result.created.length} 个模板，可直接用于 AI 生成`)
      }
      // 同名文件不再跳过，而是归档为已有模板的新版本，需要明确告知用户「更新」而非「新建」
      if (result.versioned.length > 0) {
        msgApi.info(`${result.versioned.length} 个同名文件已作为已有模板的新版本归档`)
      }
      result.skipped.forEach((reason) => msgApi.warning(reason))
      setPendingFiles([])
      void loadData()
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '批量上传失败')
    } finally {
      setBatchUploading(false)
    }
  }

  const doUploadToTemplate = async (record: RdDeliverableTemplate, file: File, changeNote?: string) => {
    setUploadingFile(true)
    try {
      const replaced = Boolean(record.file_object_key)
      await uploadDeliverableTemplateFile(record.id, file, changeNote)
      msgApi.success(replaced ? `已上传新版本：${file.name}` : `已上传 Word 模板：${file.name}`)
      void loadData()
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '上传失败')
    } finally {
      setUploadingFile(false)
    }
  }

  /**
   * 选定文件后先不提交：替换已有母本会产生新版本，先让用户写一句版本说明，
   * 否则版本历史里只剩「谁在什么时候传的」，事后无法回溯改了什么。
   */
  const handleUploadToTemplate = (record: RdDeliverableTemplate, file: File) => {
    if (record.file_object_key) {
      setPendingNoteText('')
      setPendingNote({ record, file })
    } else {
      void doUploadToTemplate(record, file)
    }
    return false
  }

  const handleDownload = async (record: RdDeliverableTemplate) => {
    try {
      saveBlob(await downloadDeliverableTemplate(record.id), record.file_name ?? `${record.name}.docx`)
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '下载失败')
    }
  }

  /** 下载版本历史里的指定版本 */
  const handleVersionDownload = async (version: DocGenTemplateVersion) => {
    if (!versionDrawer) return
    try {
      const blob = await downloadDeliverableTemplateVersion(versionDrawer.id, version.id)
      const ext = version.file_ext ?? '.docx'
      saveBlob(blob, `${versionDrawer.name}-v${version.version_no}${ext}`)
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '下载历史版本失败')
    }
  }

  /** 预览弹窗底部的下载：按当前预览目标（当前版本或历史版本）取字节流 */
  const handlePreviewDownload = async () => {
    if (!previewSource) return
    try {
      const blob = previewSource.versionId
        ? await downloadDeliverableTemplateVersion(previewSource.templateId, previewSource.versionId)
        : await downloadDeliverableTemplate(previewSource.templateId)
      saveBlob(blob, previewSource.fileName)
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '下载失败')
    }
  }

  const columns = [
    { title: '模板名称', dataIndex: 'name', key: 'name', width: 220 },
    {
      title: '阶段',
      dataIndex: 'stage',
      key: 'stage',
      width: 100,
      render: (stage: string) => <Tag>{STAGE_LABELS[stage as RdProjectStage] || stage}</Tag>,
    },
    { title: '交付物类型', dataIndex: 'deliverable_type', key: 'deliverable_type', width: 180 },
    {
      title: '填充项识别',
      key: 'profile',
      width: 220,
      render: (_: unknown, record: RdDeliverableTemplate) => {
        if (!record.file_object_key) return <Tag color="orange">待上传 Word 母本</Tag>
        const profile = profiles.find((p) => p.code === record.template_code)
        if (profile) {
          return (
            <Space size={4} wrap>
              <Tag color="blue">{profile.name}</Tag>
              <span style={{ color: '#999', fontSize: 12 }}>{profile.slot_count} 个填充项</span>
            </Space>
          )
        }
        // 母本结构自动识别出来的配置：不需要用户理解细节，只提示「已可用」
        return (
          <Space size={4} wrap>
            <Tag color="purple">已按母本结构自动识别</Tag>
            <Tooltip title={record.description ?? ''}>
              <span style={{ color: '#999', fontSize: 12 }}>可直接用于 AI 生成</span>
            </Tooltip>
          </Space>
        )
      },
    },
    {
      title: 'Word 模板原件',
      key: 'file',
      width: 320,
      render: (_: unknown, record: RdDeliverableTemplate) =>
        record.file_object_key ? (
          <Space size={4} wrap>
            <Tag color="green">{record.file_ext ?? '.docx'}</Tag>
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openTemplatePreview(record)}>
              预览
            </Button>
            <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => void handleDownload(record)}>
              下载
            </Button>
            <Tooltip title="查看历史版本，可回滚或删除留档">
              <Button type="link" size="small" icon={<HistoryOutlined />} onClick={() => setVersionDrawer(record)}>
                版本历史
              </Button>
            </Tooltip>
          </Space>
        ) : (
          <Upload beforeUpload={(f) => handleUploadToTemplate(record, f)} showUploadList={false} accept={WORD_ACCEPT} disabled={uploadingFile}>
            <Button type="link" size="small" icon={<UploadOutlined />}>
              上传 Word 模板
            </Button>
          </Upload>
        ),
    },
    {
      title: '当前版本',
      key: 'current_version',
      width: 100,
      render: (_: unknown, record: RdDeliverableTemplate) => {
        // 没上传母本的模板不存在版本链，用占位符而不是 v1，避免看起来已经有版本
        if (!record.file_object_key || !record.current_version_no) return <span style={{ color: '#bbb' }}>—</span>
        return (
          <Tooltip title={`共 ${record.version_count ?? 1} 个版本，点「版本历史」可查看与回滚`}>
            <Tag color="blue">v{record.current_version_no}</Tag>
          </Tooltip>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => <Tag color={active ? 'green' : 'default'}>{active ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      fixed: 'right' as const,
      render: (_: unknown, record: RdDeliverableTemplate) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="确定删除该模板？" onConfirm={() => void handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>交付物模板管理</h1>
        <p style={{ color: '#666', margin: '4px 0 0 0' }}>
          管理各阶段交付物的 Word 报告模板（docx/dotx/doc），用于 AI 生成初版文档
        </p>
      </div>

      <Card
        title="批量上传 Word 模板"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建模板
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          title="上传后系统自动匹配文档类型"
          description="按模板原件的表格与标签结构匹配填充项配置，并在结果里显示匹配数；无法匹配的文件不会入库。"
        />
        <Upload.Dragger
          multiple
          beforeUpload={collectFile}
          showUploadList={false}
          accept={WORD_ACCEPT}
          style={{ padding: '12px 0' }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ fontSize: 30, color: '#1677ff' }} />
          </p>
          <p className="ant-upload-text">点击或拖拽 Word 模板文件到此区域</p>
          <p className="ant-upload-hint">
            支持 .docx、.dotx、.doc；文件名即模板名称，同名不会覆盖；可一次选多个，选完点「提交上传」
          </p>
        </Upload.Dragger>
        {pendingFiles.length > 0 && (
          <Space style={{ marginTop: 12 }} wrap>
            <span>已选 {pendingFiles.length} 个文件</span>
            <Button type="primary" loading={batchUploading} onClick={() => void handleBatchSubmit()}>
              提交上传
            </Button>
            <Button onClick={() => setPendingFiles([])}>清空</Button>
          </Space>
        )}
      </Card>

      <Card title="模板列表">
        <Table
          rowKey="id"
          dataSource={templates}
          columns={columns}
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1290 }}
        />
      </Card>

      <Drawer
        title={editingTemplate ? '编辑交付物模板' : '新建交付物模板'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        styles={{ wrapper: { width: 720 } }}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={() => void handleSave()}>
              保存
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input placeholder="如：工艺验证报告" maxLength={200} />
          </Form.Item>
          <Space wrap size={16} style={{ display: 'flex' }}>
            <Form.Item name="stage" label="所属阶段" rules={[{ required: true, message: '请选择阶段' }]}>
              <Select style={{ width: 220 }} options={stageOptions} placeholder="选择阶段" />
            </Form.Item>
            <Form.Item name="deliverable_type" label="交付物类型" rules={[{ required: true, message: '请选择类型' }]}>
              <Select style={{ width: 300 }} options={deliverableOptions} placeholder="选择类型" showSearch optionFilterProp="label" />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="模板描述">
            <TextArea rows={2} placeholder="模板用途说明" />
          </Form.Item>
          {editingTemplate && (
            <Form.Item label="Word 模板原件">
              <Space wrap>
                <Upload
                  beforeUpload={(f) => handleUploadToTemplate(editingTemplate, f)}
                  showUploadList={false}
                  accept={WORD_ACCEPT}
                  disabled={uploadingFile}
                >
                  <Button icon={<UploadOutlined />} loading={uploadingFile}>
                    {editingTemplate.file_object_key ? '替换 Word 模板' : '上传 Word 模板'}
                  </Button>
                </Upload>
                {editingTemplate.file_object_key ? (
                  <>
                    <Tag color="green">{editingTemplate.file_ext ?? '.docx'}</Tag>
                    <Button
                      type="link"
                      icon={<EyeOutlined />}
                      onClick={() => openTemplatePreview(editingTemplate)}
                    >
                      预览
                    </Button>
                    <Button
                      type="link"
                      icon={<DownloadOutlined />}
                      onClick={() => void handleDownload(editingTemplate)}
                    >
                      下载
                    </Button>
                  </>
                ) : (
                  <span style={{ color: '#999' }}>尚未上传</span>
                )}
              </Space>
            </Form.Item>
          )}
          <Form.Item name="template_content" label="文本备份（可选）" extra="一般无需填写。AI 生成只读取上方上传的 Word 模板原件">
            <TextArea rows={5} placeholder="可留空" style={{ fontFamily: 'monospace' }} />
          </Form.Item>
          <Form.Item name="is_active" label="是否启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>

      <Modal
        title={`模板预览：${previewSource?.title ?? ''}`}
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        afterOpenChange={(visible) => {
          // 关闭动画结束后再清空目标，避免关闭过程中内容被提前卸载
          if (!visible) {
            setPreviewSource(null)
            setPreviewError(null)
            setPreviewLoading(false)
          }
        }}
        footer={
          previewSource ? (
            <Button icon={<DownloadOutlined />} onClick={() => void handlePreviewDownload()}>
              下载模板
            </Button>
          ) : null
        }
        width={860}
        destroyOnClose
      >
        {previewNotice && <Alert type="warning" showIcon title={previewNotice} style={{ marginBottom: 12 }} />}
        {previewLoading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="正在渲染模板…" />
          </div>
        )}
        {!previewNotice && (
          <div
            ref={previewRef}
            style={{ border: '1px solid #f0f0f0', padding: 12, minHeight: 320, maxHeight: 560, overflow: 'auto' }}
          />
        )}
      </Modal>

      <DeliverableTemplateVersionDrawer
        key={versionDrawer?.id ?? 'none'}
        open={versionDrawer !== null}
        templateId={versionDrawer?.id ?? null}
        templateName={versionDrawer?.name ?? ''}
        onClose={() => setVersionDrawer(null)}
        onChanged={() => void loadData()}
        onPreview={openVersionPreview}
        onDownload={(version) => void handleVersionDownload(version)}
      />

      <Modal
        title={`上传新版本：${pendingNote?.record.name ?? ''}`}
        open={pendingNote !== null}
        onCancel={() => setPendingNote(null)}
        onOk={() => {
          if (!pendingNote) return
          const { record, file } = pendingNote
          setPendingNote(null)
          void doUploadToTemplate(record, file, pendingNoteText.trim() || undefined)
        }}
        okText="上传"
        okButtonProps={{ loading: uploadingFile }}
        destroyOnHidden
      >
        <p style={{ color: '#666', marginTop: 0 }}>
          原母本会留档为历史版本，可随时回滚。填写版本说明便于日后追溯本次改了什么。
        </p>
        <TextArea
          rows={3}
          maxLength={200}
          value={pendingNoteText}
          onChange={(e) => setPendingNoteText(e.target.value)}
          placeholder="如：补充稳定性数据表头（可留空）"
        />
      </Modal>
    </div>
  )
}
