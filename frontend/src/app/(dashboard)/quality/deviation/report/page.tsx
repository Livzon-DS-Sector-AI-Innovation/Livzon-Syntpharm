'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Card,
  Button,
  Space,
  Upload,
  message,
  Spin,
  Divider,
  Tooltip,
  Modal,
  Input,
} from 'antd'
import {
  UploadOutlined,
  SaveOutlined,
  DownloadOutlined,
  ReloadOutlined,
  EditOutlined,
  RobotOutlined,
  CheckOutlined,
} from '@ant-design/icons'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import styles from './page.module.css'

const API_BASE = '/api/v1'

interface UploadResult {
  file_id: string
  file_name: string
  html_content: string
  file_path: string
  warnings?: string[]
}

export default function DeviationReportPage() {
  const [loading, setLoading] = useState(false)
  const [fileInfo, setFileInfo] = useState<UploadResult | null>(null)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  // AI 优化相关状态
  const [optimizing, setOptimizing] = useState(false)
  const [optimizeModalVisible, setOptimizeModalVisible] = useState(false)
  const [selectedText, setSelectedText] = useState('')
  const [optimizedText, setOptimizedText] = useState('')
  const [optimizeType, setOptimizeType] = useState('polish')

  // 右键菜单位置
  const [contextMenuVisible, setContextMenuVisible] = useState(false)
  const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 })

  const editorContainerRef = useRef<HTMLDivElement>(null)

  const editor = useEditor({
    extensions: [
      StarterKit,
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: '',
    onUpdate: () => {
      setHasChanges(true)
    },
    editorProps: {
      attributes: {
        class: styles.prose,
      },
    },
  })

  // 处理右键菜单
  useEffect(() => {
    const handleContextMenu = (e: MouseEvent) => {
      if (!editor || !editorContainerRef.current) return

      // 检查点击是否在编辑器内
      const target = e.target as HTMLElement
      if (!editorContainerRef.current.contains(target)) return

      // 检查是否有选中文本
      const selection = window.getSelection()
      if (!selection || selection.isCollapsed) return

      const text = selection.toString().trim()
      if (!text) return

      e.preventDefault()
      setSelectedText(text)
      setContextMenuPosition({ x: e.clientX, y: e.clientY })
      setContextMenuVisible(true)
    }

    const handleClick = () => {
      setContextMenuVisible(false)
    }

    document.addEventListener('contextmenu', handleContextMenu)
    document.addEventListener('click', handleClick)

    return () => {
      document.removeEventListener('contextmenu', handleContextMenu)
      document.removeEventListener('click', handleClick)
    }
  }, [editor])

  // AI 优化菜单项
  const aiMenuItems = [
    {
      key: 'polish',
      label: '润色优化',
      icon: <EditOutlined />,
    },
    {
      key: 'expand',
      label: '扩展内容',
      icon: <EditOutlined />,
    },
    {
      key: 'simplify',
      label: '简化内容',
      icon: <EditOutlined />,
    },
  ] as const

  // 处理 AI 优化
  const handleAIOptimize = async (type: string) => {
    setContextMenuVisible(false)
    setOptimizeType(type)
    setOptimizing(true)
    setOptimizedText('')

    try {
      const response = await fetch(`${API_BASE}/quality/deviation-report/ai/optimize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: selectedText,
          optimize_type: type,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '优化失败')
      }

      const result = await response.json()
      setOptimizedText(result.data.optimized_text)
      setOptimizeModalVisible(true)
      message.success('优化完成')
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : 'AI优化失败'))
      console.error('Optimize error:', error)
    } finally {
      setOptimizing(false)
    }
  }

  // 确认替换文本
  const handleConfirmReplace = () => {
    if (!editor || !optimizedText) return

    // 获取当前选择并替换
    const { from, to } = editor.state.selection
    editor.chain().focus().deleteRange({ from, to }).insertContent(optimizedText).run()

    setOptimizeModalVisible(false)
    setOptimizedText('')
    setHasChanges(true)
    message.success('文本已替换')
  }

  // 取消替换
  const handleCancelReplace = () => {
    setOptimizeModalVisible(false)
    setOptimizedText('')
  }

  // 上传并解析 Word
  const handleUpload = useCallback(async (file: File) => {
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_BASE}/quality/deviation-report/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '上传失败')
      }

      const result = await response.json()
      setFileInfo(result.data)

      if (editor) {
        editor.commands.setContent(result.data.html_content)
      }

      if (result.data.warnings?.length > 0) {
        message.warning(`文档解析完成，有 ${result.data.warnings.length} 个警告`)
      } else {
        message.success('文档解析成功')
      }
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : '文档解析失败'))
      console.error('Upload error:', error)
    } finally {
      setLoading(false)
    }

    return false
  }, [editor])

  // 保存文档
  const handleSave = useCallback(async () => {
    if (!fileInfo || !editor) return

    setSaving(true)
    try {
      const htmlContent = editor.getHTML()

      const response = await fetch(`${API_BASE}/quality/deviation-report/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_id: fileInfo.file_id,
          html_content: htmlContent,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '保存失败')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `偏差报告_${Date.now()}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      message.success('文档保存成功')
      setHasChanges(false)
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : '保存失败'))
      console.error('Save error:', error)
    } finally {
      setSaving(false)
    }
  }, [fileInfo, editor])

  // 直接下载原文档
  const handleDownloadOriginal = useCallback(() => {
    if (!fileInfo) return

    const link = document.createElement('a')
    link.href = `${API_BASE}/quality/deviation-report/download?file_id=${fileInfo.file_id}`
    link.download = fileInfo.file_name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }, [fileInfo])

  // 重新加载
  const handleReload = useCallback(() => {
    if (!fileInfo) return
    setFileInfo(null)
    setHasChanges(false)
    if (editor) {
      editor.commands.setContent('')
    }
  }, [fileInfo, editor])

  // 获取优化类型名称
  const getOptimizeTypeName = (type: string) => {
    const names: Record<string, string> = {
      polish: '润色优化',
      expand: '扩展内容',
      simplify: '简化内容',
    }
    return names[type] || type
  }

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="偏差报告编辑器"
        extra={
          <Space>
            <Upload
              accept=".docx,.doc"
              showUploadList={false}
              beforeUpload={handleUpload}
              disabled={loading}
            >
              <Button icon={<UploadOutlined />} loading={loading}>
                上传Word文档
              </Button>
            </Upload>
            {fileInfo && (
              <>
                <Button icon={<DownloadOutlined />} onClick={handleDownloadOriginal}>
                  下载原文档
                </Button>
                <Button icon={<ReloadOutlined />} onClick={handleReload}>
                  重新上传
                </Button>
                <Divider type="vertical" />
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={saving}
                  disabled={!hasChanges}
                >
                  保存并下载
                </Button>
              </>
            )}
          </Space>
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>正在解析文档...</div>
          </div>
        ) : !fileInfo ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Upload
              accept=".docx,.doc"
              showUploadList={false}
              beforeUpload={handleUpload}
            >
              <div style={{ cursor: 'pointer' }}>
                <UploadOutlined style={{ fontSize: 48, color: '#999' }} />
                <div style={{ marginTop: 16, color: '#666' }}>
                  点击上方按钮上传 Word 文档
                </div>
                <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                  支持 .docx 和 .doc 格式
                </div>
                <div style={{ marginTop: 16, color: '#52c41a', fontSize: 12 }}>
                  提示：选中文字后右键可使用 AI 优化功能
                </div>
              </div>
            </Upload>
          </div>
        ) : (
          <div>
            <div style={{ marginBottom: 8, color: '#666', fontSize: 12 }}>
              已加载文档：{fileInfo.file_name}
              {hasChanges && <span style={{ color: '#faad14', marginLeft: 8 }}>* 有未保存的修改</span>}
            </div>

            {/* 编辑器工具栏 */}
            {editor && (
              <div className={styles.toolbar}>
                <Space wrap>
                  <Tooltip title="粗体">
                    <Button
                      size="small"
                      type={editor.isActive('bold') ? 'primary' : 'default'}
                      icon={<EditOutlined style={{ fontWeight: 'bold' }} />}
                      onClick={() => editor.chain().focus().toggleBold().run()}
                    />
                  </Tooltip>
                  <Tooltip title="斜体">
                    <Button
                      size="small"
                      type={editor.isActive('italic') ? 'primary' : 'default'}
                      icon={<EditOutlined style={{ fontStyle: 'italic' }} />}
                      onClick={() => editor.chain().focus().toggleItalic().run()}
                    />
                  </Tooltip>
                  <Tooltip title="删除线">
                    <Button
                      size="small"
                      type={editor.isActive('strike') ? 'primary' : 'default'}
                      icon={<EditOutlined style={{ textDecoration: 'line-through' }} />}
                      onClick={() => editor.chain().focus().toggleStrike().run()}
                    />
                  </Tooltip>
                  <Divider type="vertical" />
                  <Tooltip title="标题1">
                    <Button
                      size="small"
                      type={editor.isActive('heading', { level: 1 }) ? 'primary' : 'default'}
                      onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                    >
                      H1
                    </Button>
                  </Tooltip>
                  <Tooltip title="标题2">
                    <Button
                      size="small"
                      type={editor.isActive('heading', { level: 2 }) ? 'primary' : 'default'}
                      onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                    >
                      H2
                    </Button>
                  </Tooltip>
                  <Tooltip title="标题3">
                    <Button
                      size="small"
                      type={editor.isActive('heading', { level: 3 }) ? 'primary' : 'default'}
                      onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
                    >
                      H3
                    </Button>
                  </Tooltip>
                  <Divider type="vertical" />
                  <Tooltip title="有序列表">
                    <Button
                      size="small"
                      type={editor.isActive('orderedList') ? 'primary' : 'default'}
                      onClick={() => editor.chain().focus().toggleOrderedList().run()}
                    >
                      1.
                    </Button>
                  </Tooltip>
                  <Tooltip title="无序列表">
                    <Button
                      size="small"
                      type={editor.isActive('bulletList') ? 'primary' : 'default'}
                      onClick={() => editor.chain().focus().toggleBulletList().run()}
                    >
                      •
                    </Button>
                  </Tooltip>
                  <Divider type="vertical" />
                  <Tooltip title="插入表格">
                    <Button
                      size="small"
                      onClick={() =>
                        editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
                      }
                    >
                      表格
                    </Button>
                  </Tooltip>
                </Space>
              </div>
            )}

            {/* 编辑器内容 */}
            <div
              className={styles.editorContainer}
              ref={editorContainerRef}
            >
              <EditorContent editor={editor} />
            </div>

            {/* 右键菜单 */}
            {contextMenuVisible && (
              <div
                className={styles.contextMenu}
                style={{
                  left: contextMenuPosition.x,
                  top: contextMenuPosition.y,
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div className={styles.contextMenuTitle}>
                  <RobotOutlined /> AI 优化
                </div>
                {aiMenuItems?.map((item) => (
                  <div
                    key={item?.key}
                    className={styles.contextMenuItem}
                    onClick={() => handleAIOptimize(item?.key as string)}
                  >
                    {item?.icon}
                    <span style={{ marginLeft: 8 }}>{item?.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* AI 优化结果弹窗 */}
      <Modal
        title={`${getOptimizeTypeName(optimizeType)}结果`}
        open={optimizeModalVisible}
        onCancel={handleCancelReplace}
        width={800}
        footer={
          <Space>
            <Button onClick={handleCancelReplace}>取消</Button>
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={handleConfirmReplace}
            >
              替换原文
            </Button>
          </Space>
        }
      >
        {optimizing ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>正在使用 AI {getOptimizeTypeName(optimizeType)}...</div>
          </div>
        ) : (
          <div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontWeight: 500, marginBottom: 8, color: '#666' }}>原文：</div>
              <div
                style={{
                  padding: 12,
                  background: '#f5f5f5',
                  borderRadius: 4,
                  maxHeight: 150,
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {selectedText}
              </div>
            </div>
            <div>
              <div style={{ fontWeight: 500, marginBottom: 8, color: '#52c41a' }}>优化后：</div>
              <Input.TextArea
                value={optimizedText}
                onChange={(e) => setOptimizedText(e.target.value)}
                rows={8}
                style={{ whiteSpace: 'pre-wrap' }}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
