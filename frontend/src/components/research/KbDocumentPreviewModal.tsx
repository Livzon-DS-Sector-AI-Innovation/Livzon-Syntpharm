'use client'

/**
 * 知识库资料预览弹窗：原文 + 解析内容两个页签。
 *
 * 浏览器只能原生渲染 pdf / 图片 / 纯文本，其余格式按下面两条路走：
 * - `.docx/.dotx` → docx-preview（复用 useDocxPreview，与报告/模板预览同一套）
 * - `.doc/.xls(x)/.ppt(x)` → 请求后端 `as_pdf=true`，由 LibreOffice 转 PDF 后内联显示
 *   （这是「源文件无法在线预览」的根因：这类格式内联打开只会触发下载）
 *
 * 渲染器按**后端实际返回的 MIME** 选择，而不是只看扩展名：转换失败时后端会回退
 * 原件，此时不会误当 PDF 渲染。文件本体在 RAGFlow，这里按需回源取流，用完即 revoke。
 *
 * 弹窗只负责外壳（标题/页脚），内容交给按资料 id 重新挂载的 KbPreviewBody，
 * 这样换资料时状态天然重置，不需要在 effect 里「先清空再加载」。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert,
  App,
  Button,
  Empty,
  Modal,
  Pagination,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { DownloadOutlined, ExportOutlined } from '@ant-design/icons'
import type { WorkBook, WorkSheet } from 'xlsx'
import {
  documentFileUrl,
  downloadKbDocument,
  fetchKbDocumentBlob,
  fetchKbDocumentChunks,
  kbImageUrl,
} from '@/lib/api/client/research/knowledge-base'
import {
  kbPreviewKind,
  type KbChunkItem,
  type KbDocumentItem,
  type KbPreviewKind,
} from '@/types/research/knowledge-base'
import { useDocxPreview } from './useDocxPreview'

interface Props {
  kbId: string
  /** 待预览的资料；null 表示没有选中（弹窗只做关闭动画） */
  document: KbDocumentItem | null
  open: boolean
  onClose: () => void
}

const CHUNK_PAGE_SIZE = 20
// 表格只渲染前若干行/列：几千行的表格整份塞进 DOM 会直接把页面拖死
const SHEET_MAX_ROWS = 100
const SHEET_MAX_COLS = 30

/** 能不能在浏览器标签页里渲染：表格走弹窗网格，未知格式只能下载 */
function canOpenInNewTab(fileExt: string): boolean {
  const kind = kbPreviewKind(fileExt)
  return kind !== 'sheet' && kind !== 'unsupported'
}

/** 浏览器没法在标签页里渲染的类型：新窗口打开时让后端转 PDF */
function newTabNeedsPdf(fileExt: string): boolean {
  return !['pdf', 'image', 'text'].includes(kbPreviewKind(fileExt))
}

/** 解析切片的页码：RAGFlow 的 positions 形如 [[页序号, x0, x1, y0, y1], ...] */
function chunkPages(chunk: KbChunkItem): number[] {
  const pages = (chunk.positions ?? [])
    .map((position) => (Array.isArray(position) ? Number(position[0]) : NaN))
    .filter((page) => Number.isFinite(page))
  return Array.from(new Set(pages))
}

interface SheetGrid {
  columns: { title: string; dataIndex: number }[]
  rows: string[][]
  totalRows: number
  totalCols: number
  truncated: boolean
}

/** A1 引用 → 行列下标（0 基）：不依赖 XLSX.utils，省一次动态导入的耦合 */
function decodeRef(ref: string): { row: number; col: number } | null {
  const match = /^([A-Z]+)(\d+)$/.exec(ref.toUpperCase())
  if (!match) return null
  const col = match[1].split('').reduce((acc, ch) => acc * 26 + (ch.charCodeAt(0) - 64), 0) - 1
  return { row: Number(match[2]) - 1, col }
}

/** 单元格文本：优先用格式化结果（w），否则原始值 */
function cellText(cell: unknown): string {
  if (!cell || typeof cell !== 'object') return ''
  const record = cell as { w?: unknown; v?: unknown }
  if (record.w !== undefined) return String(record.w)
  return record.v === undefined || record.v === null ? '' : String(record.v)
}

/** 列序号 → 字母（0 → A，26 → AA） */
function encodeCol(index: number): string {
  let letters = ''
  let n = index + 1
  while (n > 0) {
    const rem = (n - 1) % 26
    letters = String.fromCharCode(65 + rem) + letters
    n = Math.floor((n - 1) / 26)
  }
  return letters
}

/** 把一张工作表转成可渲染的网格（行列都截断到上限） */
function readSheetGrid(sheet: WorkSheet): SheetGrid {
  const ref = typeof sheet['!ref'] === 'string' ? sheet['!ref'] : ''
  const [startRef, endRef] = ref.split(':')
  const start = decodeRef(startRef || 'A1') ?? { row: 0, col: 0 }
  const end = decodeRef(endRef || startRef || 'A1') ?? start
  const lastRow = Math.min(end.row, start.row + SHEET_MAX_ROWS)
  const lastCol = Math.min(end.col, start.col + SHEET_MAX_COLS)

  const cells = sheet as Record<string, unknown>
  const grid: string[][] = []
  for (let row = start.row; row <= lastRow; row += 1) {
    const line: string[] = []
    for (let col = start.col; col <= lastCol; col += 1) {
      line.push(cellText(cells[`${encodeCol(col)}${row + 1}`]))
    }
    grid.push(line)
  }

  // 首行未必是表头：很多业务表第一行是标题/说明（整行只有一个非空单元格），
  // 那种情况用通用列名并把首行当数据，免得表头变成一大段说明文字
  const first = grid[0] ?? []
  const headLike = first.filter((cell) => cell.trim()).length > 1
  return {
    columns: Array.from({ length: grid[0]?.length ?? 0 }, (_, index) => ({
      title: headLike ? first[index] || `列${encodeCol(index)}` : `列${encodeCol(index)}`,
      dataIndex: index,
    })),
    rows: headLike ? grid.slice(1) : grid,
    totalRows: Math.max(0, end.row - start.row + 1),
    totalCols: Math.max(0, end.col - start.col + 1),
    truncated: lastRow < end.row || lastCol < end.col,
  }
}

export function KbDocumentPreviewModal({ kbId, document: doc, open, onClose }: Props) {
  const { message: msgApi } = App.useApp()
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    if (!doc) return
    setDownloading(true)
    try {
      await downloadKbDocument(kbId, doc.id, doc.file_name)
      msgApi.success('已开始下载')
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '下载失败')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Modal
      title={`资料预览：${doc?.file_name ?? ''}`}
      open={open}
      onCancel={onClose}
      width={900}
      destroyOnClose
      footer={
        doc ? (
          <Space>
            {canOpenInNewTab(doc.file_ext) ? (
              <Button
                icon={<ExportOutlined />}
                onClick={() =>
                  window.open(
                    documentFileUrl(kbId, doc.id, { inline: true, asPdf: newTabNeedsPdf(doc.file_ext) }),
                    '_blank',
                    'noopener',
                  )
                }
              >
                新窗口打开
              </Button>
            ) : null}
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={downloading}
              onClick={() => void handleDownload()}
            >
              下载原件
            </Button>
          </Space>
        ) : null
      }
    >
      {doc ? <KbPreviewBody key={doc.id} kbId={kbId} doc={doc} /> : null}
    </Modal>
  )
}

type RenderMode = 'loading' | 'docx' | 'pdf' | 'image' | 'text' | 'sheet' | 'unsupported'

/** 后端实际返回什么就按什么渲染：转换失败回退原件时不会渲染错 */
function resolveRenderMode(blob: Blob, kind: KbPreviewKind): RenderMode {
  const type = (blob.type || '').toLowerCase()
  if (type.includes('pdf')) return 'pdf'
  if (type.startsWith('image/')) return 'image'
  if (type.includes('wordprocessingml')) return 'docx'
  if (type.includes('spreadsheet') || type.includes('excel')) return 'sheet'
  if (type.startsWith('text/')) return 'text'
  // MIME 缺失时按扩展名兜底（部分代理会吃掉 Content-Type）
  if (kind === 'docx') return 'docx'
  if (kind === 'pdf') return 'pdf'
  if (kind === 'image') return 'image'
  if (kind === 'text') return 'text'
  if (kind === 'sheet') return 'sheet'
  return 'unsupported'
}

function KbPreviewBody({ kbId, doc }: { kbId: string; doc: KbDocumentItem }) {
  const kind = kbPreviewKind(doc.file_ext)
  const { loading: docxLoading, error: docxError, renderDocx } = useDocxPreview()
  const [mode, setMode] = useState<RenderMode>(kind === 'unsupported' ? 'unsupported' : 'loading')
  const [docxContainer, setDocxContainer] = useState<HTMLDivElement | null>(null)
  const [docxBlob, setDocxBlob] = useState<Blob | null>(null)
  const [objectUrl, setObjectUrl] = useState('')
  const [textContent, setTextContent] = useState('')
  const [sourceError, setSourceError] = useState('')
  const [tab, setTab] = useState(kind === 'unsupported' ? 'chunks' : 'source')
  // 表格预览：保留 workbook 以便切换工作表，网格按行列上限截断
  const [workbook, setWorkbook] = useState<WorkBook | null>(null)
  const [sheetNames, setSheetNames] = useState<string[]>([])
  const [activeSheet, setActiveSheet] = useState('')
  const [sheetGrid, setSheetGrid] = useState<SheetGrid | null>(null)

  const applySheet = useCallback((book: WorkBook, name: string) => {
    const sheet = book.Sheets[name]
    setSheetGrid(sheet ? readSheetGrid(sheet) : null)
  }, [])

  const [chunks, setChunks] = useState<KbChunkItem[]>([])
  const [chunkTotal, setChunkTotal] = useState(0)
  const [chunkPage, setChunkPage] = useState(1)
  const [chunkLoading, setChunkLoading] = useState(false)
  const [chunkError, setChunkError] = useState('')
  // 取图失败的切片：隐藏破图并给出提示（图片在对象存储里可能已被清理）
  const [brokenImages, setBrokenImages] = useState<Set<string>>(new Set())
  const chunkRequestedRef = useRef(false)

  // 加载原文（只在挂载时跑一次：换资料靠上层的 key 重挂载）
  useEffect(() => {
    if (kind === 'unsupported') return
    let cancelled = false
    void fetchKbDocumentBlob(kbId, doc.id, { asPdf: kind === 'office' })
      .then(async (blob) => {
        if (cancelled) return
        const resolved = resolveRenderMode(blob, kind)
        setMode(resolved)
        if (resolved === 'docx') {
          setDocxBlob(blob)
        } else if (resolved === 'text') {
          setTextContent(await blob.text())
        } else if (resolved === 'sheet') {
          // 表格在前端解析：服务端转 PDF 对这种大表要一两分钟，网格几秒就出来了
          const buffer = await blob.arrayBuffer()
          if (cancelled) return
          const XLSX = await import('xlsx')
          const book = XLSX.read(buffer, { type: 'array' })
          if (cancelled) return
          const first = book.SheetNames[0] ?? ''
          setWorkbook(book)
          setSheetNames(book.SheetNames)
          setActiveSheet(first)
          applySheet(book, first)
        } else if (resolved === 'pdf' || resolved === 'image') {
          setObjectUrl(URL.createObjectURL(blob))
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setSourceError(e instanceof Error ? e.message : '加载资料文件失败')
      })
    return () => {
      cancelled = true
    }
  }, [kbId, doc.id, kind, applySheet])

  // 对象 URL 生命周期跟着状态走：换文件或卸载时释放
  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [objectUrl])

  // docx 要等容器挂载后再渲染
  useEffect(() => {
    if (mode !== 'docx' || !docxBlob || !docxContainer) return
    void renderDocx(docxBlob, docxContainer)
  }, [mode, docxBlob, docxContainer, renderDocx])

  // 切到「解析内容」页签时加载一次（不可渲染的格式默认就在这个页签）
  const loadChunks = useCallback(
    async (page: number) => {
      setChunkLoading(true)
      setChunkError('')
      try {
        const data = await fetchKbDocumentChunks(kbId, doc.id, page, CHUNK_PAGE_SIZE)
        setChunks(data.items ?? [])
        setChunkTotal(data.total ?? 0)
        setChunkPage(data.page ?? page)
      } catch (e: unknown) {
        setChunkError(e instanceof Error ? e.message : '加载解析内容失败')
      } finally {
        setChunkLoading(false)
      }
    },
    [kbId, doc.id],
  )

  useEffect(() => {
    if (tab !== 'chunks' || chunkRequestedRef.current) return
    chunkRequestedRef.current = true
    void loadChunks(1)
  }, [tab, loadChunks])

  const sourcePane = (() => {
    if (sourceError) {
      return <Alert type="error" showIcon message="原文加载失败" description={sourceError} />
    }
    if (mode === 'loading') {
      const tip =
        kind === 'office'
          ? '正在转换文档（首次较慢，请稍候）…'
          : kind === 'sheet'
            ? '正在解析表格…'
            : '正在加载原文…'
      return (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin tip={tip} />
        </div>
      )
    }
    if (mode === 'unsupported') {
      return (
        <Alert
          type="info"
          showIcon
          message="该格式无法在线预览"
          description={
            kind === 'office'
              ? '服务端转换未成功，可切换到「解析内容」查看解析出的文字，或下载原件后用本地软件打开。'
              : '可切换到「解析内容」查看解析出来的文字，或直接下载原件后用本地软件打开。'
          }
        />
      )
    }
    if (mode === 'sheet') {
      if (!sheetGrid) {
        return <Empty description="该表格没有可显示的内容" />
      }
      return (
        <div>
          <Space style={{ marginBottom: 12 }} wrap>
            <span>工作表：</span>
            {sheetNames.length > 1 ? (
              <Select
                size="small"
                style={{ minWidth: 220 }}
                value={activeSheet}
                onChange={(name) => {
                  setActiveSheet(name)
                  if (workbook) applySheet(workbook, name)
                }}
                options={sheetNames.map((name) => ({ value: name, label: name }))}
              />
            ) : (
              <Typography.Text>{activeSheet || '-'}</Typography.Text>
            )}
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {sheetGrid.truncated
                ? `仅显示前 ${SHEET_MAX_ROWS} 行 / ${SHEET_MAX_COLS} 列（共 ${sheetGrid.totalRows} 行 × ${sheetGrid.totalCols} 列），完整数据请下载原件`
                : `共 ${sheetGrid.totalRows} 行 × ${sheetGrid.totalCols} 列`}
            </Typography.Text>
          </Space>
          <Table
            size="small"
            bordered
            rowKey={(_, index) => String(index)}
            dataSource={sheetGrid.rows}
            columns={sheetGrid.columns}
            pagination={false}
            scroll={{ x: 'max-content', y: '50vh' }}
          />
        </div>
      )
    }
    if (mode === 'docx') {
      return docxError ? (
        <Alert type="warning" showIcon message="文档渲染失败" description={docxError} />
      ) : (
        <Spin spinning={docxLoading} tip="正在渲染文档…">
          <div
            ref={setDocxContainer}
            style={{ border: '1px solid #f0f0f0', padding: 12, minHeight: 320, maxHeight: '65vh', overflow: 'auto' }}
          />
        </Spin>
      )
    }
    if (mode === 'pdf') {
      return (
        <iframe
          src={objectUrl}
          title={doc.file_name}
          style={{ width: '100%', height: '65vh', border: '1px solid #f0f0f0' }}
        />
      )
    }
    if (mode === 'image') {
      return (
        // 图片预览用原生 img：尺寸未知，交给浏览器按容器缩放
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={objectUrl}
          alt={doc.file_name}
          style={{ maxWidth: '100%', maxHeight: '65vh', display: 'block', margin: '0 auto' }}
        />
      )
    }
    return (
      <pre
        style={{
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          maxHeight: '65vh',
          overflow: 'auto',
          background: '#fafafa',
          padding: 12,
          margin: 0,
        }}
      >
        {textContent || '（空文件）'}
      </pre>
    )
  })()

  const chunksPane = (
    <div>
      {chunkError ? <Alert type="error" showIcon message="解析内容加载失败" description={chunkError} /> : null}
      <Spin spinning={chunkLoading}>
        {chunks.length ? (
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            {chunks.map((chunk, index) => (
              <div key={chunk.id || index} style={{ border: '1px solid #f0f0f0', borderRadius: 6, padding: 10 }}>
                <div style={{ marginBottom: 6 }}>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    片段 {(chunkPage - 1) * CHUNK_PAGE_SIZE + index + 1}
                    {chunk.document_keyword ? ` · ${chunk.document_keyword}` : ''}
                  </Typography.Text>
                  {chunkPages(chunk).map((page) => (
                    <Tag key={page} style={{ marginLeft: 6 }}>
                      第 {page} 页
                    </Tag>
                  ))}
                </div>
                <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                  {chunk.content}
                </Typography.Paragraph>
                {/* PDF 页图 / 图注配图：点开可在新窗口看大图 */}
                {chunk.image_id ? (
                  brokenImages.has(chunk.id) ? (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      配图加载失败
                    </Typography.Text>
                  ) : (
                    <a
                      href={kbImageUrl(kbId, chunk.image_id)}
                      target="_blank"
                      rel="noreferrer"
                      style={{ display: 'inline-block', marginTop: 8 }}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={kbImageUrl(kbId, chunk.image_id)}
                        alt="切片配图"
                        loading="lazy"
                        onError={() =>
                          setBrokenImages((prev) => new Set(prev).add(chunk.id))
                        }
                        style={{
                          maxWidth: '100%',
                          maxHeight: 320,
                          borderRadius: 4,
                          border: '1px solid #f0f0f0',
                          display: 'block',
                        }}
                      />
                    </a>
                  )
                ) : null}
              </div>
            ))}
          </Space>
        ) : (
          !chunkLoading && !chunkError && <Empty description="还没有解析内容，解析完成后可在此查看" />
        )}
      </Spin>
      {chunkTotal > CHUNK_PAGE_SIZE ? (
        <div style={{ marginTop: 12, textAlign: 'right' }}>
          <Pagination
            size="small"
            current={chunkPage}
            pageSize={CHUNK_PAGE_SIZE}
            total={chunkTotal}
            showSizeChanger={false}
            onChange={(page) => void loadChunks(page)}
          />
        </div>
      ) : null}
    </div>
  )

  return (
    <Tabs
      activeKey={tab}
      onChange={setTab}
      items={[
        { key: 'source', label: '原文预览', children: sourcePane },
        { key: 'chunks', label: '解析内容', children: chunksPane },
      ]}
    />
  )
}
