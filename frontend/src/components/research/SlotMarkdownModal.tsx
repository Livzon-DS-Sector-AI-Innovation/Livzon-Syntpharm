'use client'

/**
 * 「模板 Markdown」弹窗：展示 Word 母本解析出的**全内容 Markdown**。
 *
 * 数据源两级（后端 template_markdown）：母本规则解析（source=docx，现转换）＞
 * 填写项骨架回退（source=spec）。渲染统一走 react-markdown + remark-gfm +
 * rehype-raw——不造解析轮子；骨架视图里 <!--slot:key--> 标记转填写项卡片、
 * {{待填}} 转高亮 chip，全内容视图无标记时装饰自然空转。
 * 「填写项语义」视图直接展示后端语义清单（检索词/期望/必填/核对状态）——
 * AI 增强与人工维护的成果在此肉眼可验，增强前后对比一目了然。
 * 源码视图保留原始 Markdown——骨架标记是 P2「编辑→按 key 解析回填」的寻址锚。
 *
 * 安全说明：内容来自内部模板母本与 AI 标注（与 AIReportPanel 的 rehype-raw 用法同级
 * 信任），非公开用户输入。
 */
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Modal, Segmented, Spin, Tag, Empty, Table, Tooltip } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DownloadOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { fetchDeliverableTemplateMarkdown } from '@/lib/api/client/research/doc-gen'
import type { DocGenTemplateMarkdown } from '@/lib/api/client/research/doc-gen'
import { saveBlob } from '@/lib/utils/download'

/** 填写项语义行（后端 template_structure 的只读摘要） */
type SlotSemantics = NonNullable<DocGenTemplateMarkdown['slots']>[number]

interface SlotMarkdownModalProps {
  open: boolean
  templateId: string | null
  templateName: string
  onClose: () => void
}

type ViewMode = '渲染视图' | '填写项语义' | 'Markdown 源码'

/** 填写项语义枚举的中文口径（与后端 template_spec 的 Literal 对齐） */
const KIND_LABELS: Record<string, string> = { field: '字段', paragraph: '段落', table: '表格', image: '图片' }
const EXPECTS_LABELS: Record<string, string> = { text: '文本', number: '数值', date: '日期', percent: '百分比' }

/** 核对状态 → Tag 配色/文案 */
function reviewTag(state: string) {
  if (state === 'needs_review') return <Tag color="orange">需人工核对</Tag>
  if (state === 'confirmed') return <Tag color="green">已确认</Tag>
  return <Tag>自动</Tag>
}

/** slot 标记里的 key：与后端 _SLOT_BLOCK_RE 同口径 */
const SLOT_KEY = '[A-Za-z0-9_.\\-]+'

/**
 * 把标记化 Markdown 装饰为可渲染的 HTML 结构（仅用于渲染视图，源码视图不动）：
 * - `**标签**` + 紧随的 `<!--slot:key-->` → 卡片 + 卡片标题（标签不属于可编辑内容区）
 * - 落单的 `<!--slot:key-->` → 无标题卡片
 * - `<!--/slot-->` → 卡片收尾
 * - `{{待填}}` → 高亮 chip
 */
function decorateMarkdown(md: string): string {
  return md
    .replace(new RegExp(`\\*\\*([^*\\n]+)\\*\\*\\n\\n<!--slot:(${SLOT_KEY})-->`, 'g'), (_m, label: string, key: string) =>
      `<div class="tpl-slot" data-slot="${key}"><div class="tpl-slot-label">${label}</div>`,
    )
    .replace(new RegExp(`<!--slot:(${SLOT_KEY})-->`, 'g'), (_m, key: string) => `<div class="tpl-slot" data-slot="${key}">`)
    .replace(/<!--\/slot-->/g, '</div>')
    .replace(/\{\{待填\}\}/g, '<span class="tpl-slot-todo">待填</span>')
}

/** 视图美化样式：作用域限定在 .tpl-md 容器内 */
const SLOT_MD_CSS = `
.tpl-md { font-size: 14px; line-height: 1.75; color: #1f2937; }
.tpl-md h1 { font-size: 18px; font-weight: 600; text-align: center; margin: 4px 0 18px; color: #111827; }
.tpl-md h2 { font-size: 15px; font-weight: 600; margin: 20px 0 10px; padding-bottom: 6px; border-bottom: 1px solid #eef2f7; color: #111827; }
.tpl-md p { margin: 6px 0; }
.tpl-slot { border: 1px solid #e6ecf5; border-left: 3px solid #1677ff; border-radius: 8px; padding: 10px 14px; margin: 10px 0 16px; background: #fafcff; transition: border-color .2s; }
.tpl-slot:hover { border-color: #91caff; border-left-color: #1677ff; }
.tpl-slot-label { font-weight: 600; color: #1f2937; margin-bottom: 6px; }
.tpl-slot blockquote { margin: 0; padding: 8px 12px; background: #fff; border: 1px dashed #dbe4f0; border-radius: 6px; color: #98a2b3; }
.tpl-slot blockquote p { margin: 0; }
.tpl-slot table { width: 100%; border-collapse: collapse; background: #fff; font-size: 13px; margin: 4px 0; }
.tpl-slot th, .tpl-slot td, .tpl-md table th, .tpl-md table td { border: 1px solid #e6ecf5; padding: 6px 10px; text-align: left; }
.tpl-slot th, .tpl-md table th { background: #f0f5ff; font-weight: 600; }
.tpl-slot-todo { display: inline-block; padding: 0 10px; border-radius: 999px; background: #fff7e6; border: 1px dashed #ffd591; color: #d46b08; font-size: 12px; line-height: 20px; }
`

/** 「填写项语义」表格列：AI 增强/人工维护的检索词、期望取值与核对状态在此肉眼可验 */
const SEMANTICS_COLUMNS: ColumnsType<SlotSemantics> = [
  {
    title: '填写项',
    dataIndex: 'label',
    key: 'label',
    width: 150,
    render: (label: string, row) => (
      <div>
        <div style={{ fontWeight: 600 }}>{label}</div>
        <div style={{ fontSize: 12, color: '#98a2b3' }}>{row.key}</div>
      </div>
    ),
  },
  {
    title: '类型',
    dataIndex: 'kind',
    key: 'kind',
    width: 56,
    render: (kind: string) => KIND_LABELS[kind] ?? kind,
  },
  {
    title: '必填',
    dataIndex: 'required',
    key: 'required',
    width: 60,
    render: (required: boolean) => (required ? <Tag color="red">必填</Tag> : '否'),
  },
  {
    title: '期望取值',
    key: 'expects',
    width: 130,
    render: (_: unknown, row) => (
      <span>
        {EXPECTS_LABELS[row.expects] ?? row.expects}
        {row.unit && <span style={{ color: '#667085' }}> · {row.unit}</span>}
        {row.cardinality === 'one_or_more' && <span style={{ color: '#667085' }}> · 可多值</span>}
        {row.source_scope === 'project_kb' && <span style={{ color: '#667085' }}> · 仅知识库</span>}
        {(row.enum_values?.length ?? 0) > 0 && (
          <Tooltip title={`允许取值：${(row.enum_values ?? []).join('、')}`}>
            <span style={{ color: '#667085' }}> · 枚举</span>
          </Tooltip>
        )}
      </span>
    ),
  },
  {
    title: '检索词',
    key: 'search_terms',
    width: 230,
    render: (_: unknown, row) => {
      const terms = row.search_terms ?? []
      return terms.length > 0 ? (
        <span style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {terms.slice(0, 6).map((term) => (
            <Tag key={term} style={{ marginInlineEnd: 0 }}>
              {term}
            </Tag>
          ))}
          {terms.length > 6 && (
            <Tooltip title={terms.join('、')}>
              <Tag style={{ marginInlineEnd: 0 }}>+{terms.length - 6}</Tag>
            </Tooltip>
          )}
        </span>
      ) : (
        <span style={{ color: '#98a2b3' }}>—</span>
      )
    },
  },
  {
    title: '取值说明',
    dataIndex: 'query_hint',
    key: 'query_hint',
    ellipsis: { showTitle: false },
    render: (hint: string) =>
      hint ? (
        <Tooltip title={hint} placement="topLeft">
          <span>{hint}</span>
        </Tooltip>
      ) : (
        <span style={{ color: '#98a2b3' }}>—</span>
      ),
  },
  {
    title: '状态',
    dataIndex: 'review_state',
    key: 'review_state',
    width: 100,
    render: (state: string) => reviewTag(state),
  },
]

export function SlotMarkdownModal({ open, templateId, templateName, onClose }: SlotMarkdownModalProps) {
  const [mode, setMode] = useState<ViewMode>('渲染视图')

  const { data, isLoading, error } = useQuery({
    queryKey: ['deliverable-template-markdown', templateId],
    queryFn: () => fetchDeliverableTemplateMarkdown(templateId as string),
    enabled: open && templateId !== null,
  })

  const decorated = useMemo(() => (data?.markdown ? decorateMarkdown(data.markdown) : ''), [data])

  const handleDownload = () => {
    if (!data) return
    const blob = new Blob([data.markdown], { type: 'text/markdown;charset=utf-8' })
    saveBlob(blob, `${data.name || templateName}-模板markdown.md`)
  }

  const errorMessage = error instanceof Error ? error.message : '加载模板 Markdown 失败'

  return (
    <Modal
      title={`模板 Markdown：${templateName}`}
      open={open}
      onCancel={onClose}
      width={880}
      destroyOnClose
      footer={
        data ? (
          <Button icon={<DownloadOutlined />} onClick={handleDownload}>
            下载 Markdown
          </Button>
        ) : null
      }
    >
      <style>{SLOT_MD_CSS}</style>
      {isLoading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="正在生成模板 Markdown…" />
        </div>
      )}
      {!isLoading && error && <Alert type="error" showIcon title={errorMessage} />}
      {!isLoading && !error && data && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span>
              {data.source === 'spec' ? (
                <Tag color="geekblue">填写项骨架</Tag>
              ) : (
                <Tag color="green">母本全文解析</Tag>
              )}
              {data.slot_count > 0 && <Tag color="blue">{data.slot_count} 个填写项</Tag>}
              {data.needs_review > 0 && <Tag color="orange">{data.needs_review} 个需人工核对</Tag>}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Segmented
                options={['渲染视图', '填写项语义', 'Markdown 源码']}
                value={mode}
                onChange={(v) => setMode(v as ViewMode)}
              />
            </span>
          </div>
          {data.markdown || mode === '填写项语义' ? (
            mode === '填写项语义' ? (
              data.slots && data.slots.length > 0 ? (
                <Table<SlotSemantics>
                  size="small"
                  rowKey="key"
                  columns={SEMANTICS_COLUMNS}
                  dataSource={data.slots}
                  pagination={false}
                  scroll={{ y: 520 }}
                />
              ) : (
                <Empty description="该模板暂无填写项定义（请先上传母本自动识别或人工新增填写项）" />
              )
            ) : mode === '渲染视图' ? (
              <div className="tpl-md agent-markdown" style={{ maxHeight: 560, overflow: 'auto', padding: '4px 12px' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                  {decorated}
                </ReactMarkdown>
              </div>
            ) : (
              <pre
                style={{
                  maxHeight: 560,
                  overflow: 'auto',
                  background: '#fafafa',
                  border: '1px solid #f0f0f0',
                  borderRadius: 6,
                  padding: 12,
                  fontSize: 12,
                  lineHeight: 1.7,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {data.markdown}
              </pre>
            )
          ) : (
            <Empty description="该模板暂无可解析内容（母本为空且无填写项定义）" />
          )}
        </>
      )}
    </Modal>
  )
}
