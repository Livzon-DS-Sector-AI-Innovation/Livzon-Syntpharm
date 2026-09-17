'use client'

import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Modal, Space, Spin, Table } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { renderAsync } from 'docx-preview'
import * as XLSX from 'xlsx'
import ReactMarkdown from 'react-markdown'

export type PreviewKind = 'pdf' | 'docx' | 'text' | 'image' | 'excel' | 'markdown' | 'none'

function normalizeExt(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : ''
}

/** 根据扩展名判断文件预览方式 */
export function detectPreviewKind(filename: string): PreviewKind {
  const ext = normalizeExt(filename)
  if (ext === 'pdf') return 'pdf'
  if (['docx', 'dotx'].includes(ext)) return 'docx'
  if (['xlsx', 'xls', 'csv'].includes(ext)) return 'excel'
  if (ext === 'md') return 'markdown'
  if (['txt', 'log', 'json', 'xml', 'yaml', 'yml'].includes(ext)) return 'text'
  if (['png', 'jpg', 'jpeg', 'bmp', 'webp', 'gif', 'svg'].includes(ext)) return 'image'
  return 'none'
}

interface Props {
  /** 当前预览的文件，null 表示关闭弹窗 */
  file: File | null
  /** 外部控制的关闭回调 */
  onClose: () => void
  /** 可选：预加载的错误信息 */
  initialError?: string | null
  /** 可选：外部传入的 blob（用于服务端文件下载后预览） */
  blob?: Blob | null
}

/**
 * 文件预览弹窗：支持 pdf / docx / excel / markdown / text / image。
 * 从 CreateReportModal 拆出，供报告模块多处复用。
 */
export function DocGenFilePreview({ file, onClose, initialError, blob }: Props) {
  const [kind, setKind] = useState<PreviewKind>('none')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewText, setPreviewText] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Excel 专用
  const [excelSheets, setExcelSheets] = useState<{ name: string; data: unknown[][] }[]>([])
  const [excelActiveSheet, setExcelActiveSheet] = useState(0)

  const contentRef = useRef<HTMLDivElement | null>(null)
  const urlRef = useRef<string | null>(null)

  // 清理上一次的 objectURL
  const revokeUrl = () => {
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current)
      urlRef.current = null
    }
  }

  // 文件变化时重置并启动预览
  useEffect(() => {
    revokeUrl()
    setPreviewUrl(null)
    setPreviewText(null)
    setExcelSheets([])
    setExcelActiveSheet(0)
    setError(initialError ?? null)

    if (!file) {
      setKind('none')
      setLoading(false)
      return
    }

    const detected = detectPreviewKind(file.name)
    setKind(detected)

    if (detected === 'none') {
      setError(`.${normalizeExt(file.name)} 暂不支持在线预览，请下载后查看`)
      setLoading(false)
      return
    }

    if (detected === 'pdf' || detected === 'image') {
      const url = URL.createObjectURL(file)
      urlRef.current = url
      setPreviewUrl(url)
      setLoading(false)
      return
    }

    // text / markdown：读取文本
    if (detected === 'text' || detected === 'markdown') {
      setLoading(true)
      file.text()
        .then((t) => setPreviewText(t))
        .catch(() => setError('读取文件内容失败'))
        .finally(() => setLoading(false))
      return
    }

    // docx：渲染
    if (detected === 'docx') {
      setLoading(true)
      ;(async () => {
        try {
          const buf = await file.arrayBuffer()
          if (contentRef.current) {
            contentRef.current.innerHTML = ''
            await renderAsync(buf, contentRef.current, undefined, { inWrapper: true, ignoreWidth: true })
          }
        } catch {
          setError('docx 渲染失败')
        } finally {
          setLoading(false)
        }
      })()
      return
    }

    // excel：解析
    if (detected === 'excel') {
      setLoading(true)
      ;(async () => {
        try {
          const buf = await file.arrayBuffer()
          const wb = XLSX.read(buf)
          const sheets = wb.SheetNames.map((name) => {
            const ws = wb.Sheets[name]
            const data = XLSX.utils.sheet_to_json<unknown[]>(ws, { header: 1, defval: '' })
            return { name, data }
          })
          setExcelSheets(sheets)
          setExcelActiveSheet(0)
        } catch {
          setError('Excel 文件解析失败，请确认文件格式正确')
        } finally {
          setLoading(false)
        }
      })()
      return
    }
  }, [file]) // eslint-disable-line react-hooks/exhaustive-deps

  // 组件卸载时清理
  useEffect(() => {
    return () => revokeUrl()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleDownload = () => {
    if (!file) return
    const url = URL.createObjectURL(file)
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleClose = () => {
    revokeUrl()
    onClose()
  }

  // Excel 表格列动态计算
  const excelColumns = (() => {
    if (excelSheets.length === 0) return []
    const maxCols = Math.max(...(excelSheets[excelActiveSheet]?.data.map((r) => r.length) ?? [0]))
    return Array.from({ length: maxCols }, (_, i) => ({
      title: String.fromCharCode(65 + (i % 26)) + (i >= 26 ? String(Math.floor(i / 26)) : ''),
      dataIndex: ['row', i],
      key: i,
      width: 120,
      ellipsis: true,
      render: (v: unknown) => (v != null ? String(v) : ''),
    }))
  })()

  return (
    <Modal
      open={!!file}
      title={file ? `文件预览：${file.name}` : '文件预览'}
      width={900}
      onCancel={handleClose}
      footer={
        file ? (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button icon={<DownloadOutlined />} onClick={handleDownload}>
              下载文件
            </Button>
          </div>
        ) : null
      }
    >
      {error ? (
        <Alert
          type="warning"
          showIcon
          message="无法在线预览"
          description={
            <span>
              {error}
              {file && (
                <>
                  {'，请'}
                  <a onClick={handleDownload} style={{ margin: '0 4px' }}>
                    下载文件
                  </a>
                  后查看
                </>
              )}
            </span>
          }
        />
      ) : !file ? null : kind === 'docx' ? (
        <>
          {loading && <div style={{ textAlign: 'center', padding: '8px 0' }}><Spin /></div>}
          <div ref={contentRef} style={{ maxHeight: '70vh', overflow: 'auto', background: '#f5f5f5', padding: 8 }} />
        </>
      ) : kind === 'excel' ? (
        <>
          {loading && <div style={{ textAlign: 'center', padding: '24px 0' }}><Spin /></div>}
          {!loading && excelSheets.length > 0 && (
            <div>
              {excelSheets.length > 1 && (
                <div style={{ marginBottom: 12 }}>
                  <Space>
                    <span>工作表：</span>
                    {excelSheets.map((s, i) => (
                      <Button
                        key={s.name}
                        size="small"
                        type={i === excelActiveSheet ? 'primary' : 'default'}
                        onClick={() => setExcelActiveSheet(i)}
                      >
                        {s.name}
                      </Button>
                    ))}
                  </Space>
                </div>
              )}
              <div style={{ maxHeight: '65vh', overflow: 'auto', border: '1px solid #f0f0f0' }}>
                <Table
                  dataSource={excelSheets[excelActiveSheet]?.data.map((row, i) => ({ key: i, row })) ?? []}
                  columns={excelColumns}
                  pagination={false}
                  size="small"
                  scroll={{ x: 'max-content' }}
                  bordered
                />
              </div>
            </div>
          )}
          {!loading && excelSheets.length === 0 && !error && (
            <div style={{ textAlign: 'center', padding: '24px 0', color: '#999' }}>Excel 文件为空或无法解析</div>
          )}
        </>
      ) : loading ? (
        <div style={{ textAlign: 'center', padding: '24px 0' }}><Spin /></div>
      ) : kind === 'pdf' && previewUrl ? (
        <iframe src={previewUrl} title={file.name} style={{ width: '100%', height: '70vh', border: 0 }} />
      ) : kind === 'image' && previewUrl ? (
        <div style={{ textAlign: 'center', maxHeight: '70vh', overflow: 'auto' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={previewUrl} alt={file.name} style={{ maxWidth: '100%' }} />
        </div>
      ) : kind === 'markdown' ? (
        <div style={{ maxHeight: '70vh', overflow: 'auto', padding: '0 16px' }}>
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{previewText ?? ''}</ReactMarkdown>
          </div>
        </div>
      ) : (
        <pre style={{ maxHeight: '70vh', overflow: 'auto', whiteSpace: 'pre-wrap', margin: 0, padding: 16, background: '#fafafa', borderRadius: 4 }}>{previewText}</pre>
      )}
    </Modal>
  )
}
