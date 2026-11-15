'use client'

import { useState } from 'react'
import { Alert, App, Button, Flex, Input, Popconfirm, Tag, Tooltip } from 'antd'
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  PlusOutlined,
  SaveOutlined,
  UndoOutlined,
} from '@ant-design/icons'
import { saveReportGenEdits } from '@/actions/research/report-gen'
import {
  fieldStateMeta,
  type ReportGenEditOperation,
  type ReportGenEditRemoval,
  type ReportGenEditResult,
  type ReportGenFieldItem,
} from '@/types/research/report-gen'

interface Props {
  jobId: string
  item: ReportGenFieldItem
  /** 并发校验：提交时带上打开编辑时的当前版本，被别人改过则后端拒绝 */
  baseVersionId?: string | null
  onBack: () => void
  onSaved: (result: ReportGenEditResult) => void
}

type Mode = 'edit' | 'insert'

const KIND_LABEL: Record<string, string> = {
  paragraph: '正文段落',
  table_cell: '表格单元格',
  append_paragraph: 'AI 新增段落',
  append_table_rows: 'AI 新增表格行',
  references: '参考资料',
}

function RemovalList({ items, applied }: { items: ReportGenEditRemoval[]; applied: number }) {
  if (!items.length) return null
  return (
    <Alert
      type={applied > 0 ? 'warning' : 'error'}
      showIcon
      message={applied > 0 ? `有 ${items.length} 处没有保存成功，已恢复原文` : '这一批修改都没有保存成功'}
      description={
        <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
          {items.map((item, index) => (
            <li key={`${item.key ?? 'op'}-${index}`} style={{ fontSize: 12 }}>
              {item.reason}
              {item.restored ? '（这一处已恢复为模板原文）' : ''}
            </li>
          ))}
        </ul>
      }
    />
  )
}

/**
 * 选中位置的编辑卡。
 *
 * 母本里的每一处都可以人工修改（固定内容只是 AI 不写）。校验未通过时后端只丢弃
 * 那一处并还原母本原样，其余修改照常保存，所以界面按「部分成功」呈现。
 */
export function ReportGenSlotEditor({ jobId, item, baseVersionId, onBack, onSaved }: Props) {
  const { message } = App.useApp()
  const [text, setText] = useState(item.value ?? '')
  const [mode, setMode] = useState<Mode>('edit')
  const [rowText, setRowText] = useState('')
  const [saving, setSaving] = useState(false)
  const [removals, setRemovals] = useState<ReportGenEditRemoval[]>([])
  const [applied, setApplied] = useState(0)

  const meta = fieldStateMeta(item.state, item.edit_source)
  // 固定内容只代表 AI 不写；人工编辑一律放开，editable 才是人能不能改
  const locked = item.editable === false
  const isCell = item.kind === 'table_cell'
  const isAppendedParagraph = item.kind === 'append_paragraph'
  const canInsert = !locked && (item.kind === 'paragraph' || isAppendedParagraph)
  const canAppendRow = !locked && isCell
  const canDeleteRow = !locked && isCell && (item.row ?? 0) > 0
  // 已填写的母本位置可以还原成原样（空段/下划线占位），段落与单元格节点都保留
  const canRestore = !locked && item.state !== 'blank' && (item.kind === 'paragraph' || isCell)

  const submit = async (operations: ReportGenEditOperation[]) => {
    setSaving(true)
    setRemovals([])
    try {
      const result = await saveReportGenEdits(jobId, {
        base_version_id: baseVersionId ?? null,
        operations,
      })
      setApplied(result.applied)
      if (!result.applied) {
        setRemovals(result.removed ?? [])
        message.warning('这一批修改都没有保存成功，相关位置已恢复原文')
        return
      }
      if ((result.removed ?? []).length > 0) {
        // 部分成功：其余修改已经落版本，这里只提示哪些位置被还原
        message.warning(`已保存 ${result.applied} 处，另有 ${result.removed?.length ?? 0} 处还原原文`)
      } else {
        message.success(`已保存 ${result.applied} 处修改`)
      }
      onSaved(result)
      setMode('edit')
      setRowText('')
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  const submitText = () => {
    const value = text.trim()
    if (!value) {
      message.warning('内容不能为空；需要整段删除时，只有 AI 新增的段落支持删除')
      return
    }
    if (mode === 'insert') {
      void submit([{ op: 'insert_paragraph', key: item.key, text: value }])
      return
    }
    void submit([{ op: isCell ? 'update_cell' : 'update_text', key: item.key, text: value }])
  }

  const submitRow = () => {
    const cells = rowText
      .split(/[\t|｜]/)
      .map((cell) => cell.trim())
      .filter(Boolean)
    if (!cells.length) {
      message.warning('请填写新增行每一列的内容，用竖线或制表符分隔')
      return
    }
    void submit([{ op: 'append_table_row', key: item.key, cells }])
  }

  return (
    <Flex vertical style={{ height: '100%', minHeight: 0 }}>
      <div style={{ padding: '10px 16px', borderBottom: '1px solid #EDEFF2' }}>
        <Button size="small" type="link" icon={<ArrowLeftOutlined />} onClick={onBack} style={{ paddingLeft: 0 }}>
          返回清单
        </Button>
        <Flex gap={8} align="center" wrap style={{ marginTop: 2 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: '#1F2329' }}>{item.label}</span>
          <Tag color={meta.color} style={{ margin: 0 }}>
            {meta.label}
          </Tag>
          <Tag style={{ margin: 0 }}>{KIND_LABEL[item.kind] ?? item.kind}</Tag>
        </Flex>
        <div style={{ marginTop: 4, fontSize: 12, color: '#8C8C8C' }}>
          {item.section ? `${item.section} · ` : ''}
          {item.source_name ? `来源：${item.source_name}` : '人工补写不需要来源'}
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 16 }}>
        <Flex vertical gap={14}>
          <RemovalList items={removals} applied={applied} />

          {item.writable === false && (
            <Alert
              type="info"
              showIcon
              message="模板固定内容"
              description={
                item.reason ||
                '这是模板里固定的文字（标题、说明或签字审批区），需要时可以直接修改。'
              }
            />
          )}

          {item.human_locked && (
            <Alert
              type="success"
              showIcon
              message="人工确认的内容会保留"
              description="下次重新生成会沿用这一处的人工写法，AI 不会覆盖。"
            />
          )}

          {!locked && item.state === 'blank' && (
            <Alert
              type="warning"
              showIcon
              message="这一处这次没有填写"
              description={item.reason || '资料里没有可用依据，可以直接补写；补写后会保存在新版本里。'}
            />
          )}

          {item.state === 'anchor_unresolved' && (
            <Alert
              type="error"
              showIcon
              message="这一处内容没有写进文档"
              description={item.reason || '生成好的文档里找不到这一处，模板可能换过版本，建议重新生成。'}
            />
          )}

          {item.text && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#5A6472', marginBottom: 6 }}>模板原文</div>
              <div style={{ background: '#FAFBFC', border: '1px solid #EDEFF2', borderRadius: 8, padding: '10px 12px', fontSize: 13, color: '#5A6472', whiteSpace: 'pre-wrap' }}>
                {item.text}
              </div>
            </div>
          )}

          {!locked && (
            <div>
              <Flex align="center" justify="space-between" style={{ marginBottom: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#5A6472' }}>
                  {mode === 'insert' ? '在当前位置之后新增段落' : '修改内容'}
                </span>
                {canInsert && (
                  <Button
                    size="small"
                    type={mode === 'insert' ? 'primary' : 'text'}
                    ghost={mode === 'insert'}
                    onClick={() => {
                      setMode(mode === 'insert' ? 'edit' : 'insert')
                      setText(mode === 'insert' ? item.value ?? '' : '')
                    }}
                  >
                    {mode === 'insert' ? '取消新增' : '新增一段'}
                  </Button>
                )}
              </Flex>
              <Input.TextArea
                value={text}
                onChange={(event) => setText(event.target.value)}
                autoSize={{ minRows: mode === 'insert' ? 3 : 6, maxRows: 16 }}
                placeholder={mode === 'insert' ? '新段落内容，空行会拆成多段' : '填写这一处的内容'}
                style={{ fontSize: 13, lineHeight: 1.7 }}
              />
              <Flex gap={8} style={{ marginTop: 10 }}>
                <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={submitText}>
                  {mode === 'insert' ? '新增并保存' : '保存'}
                </Button>
                {isAppendedParagraph && (
                  <Popconfirm
                    title="删除这一段？"
                    description="只删除生成或编辑时新增的段落，模板原文不受影响。"
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => void submit([{ op: 'delete_paragraph', key: item.key }])}
                  >
                    <Button danger icon={<DeleteOutlined />} disabled={saving}>
                      删除这段
                    </Button>
                  </Popconfirm>
                )}
                {canRestore && mode !== 'insert' && (
                  <Popconfirm
                    title="还原为模板原文？"
                    description="内容会被清掉，段落/单元格本身保留，版面不变；保存后生成新版本，可回滚。"
                    okText="还原"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => void submit([{ op: 'restore_position', key: item.key }])}
                  >
                    <Button icon={<UndoOutlined />} disabled={saving}>
                      还原为模板原文
                    </Button>
                  </Popconfirm>
                )}
              </Flex>
            </div>
          )}

          {(canAppendRow || canDeleteRow) && (
            <div style={{ borderTop: '1px dashed #EDEFF2', paddingTop: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#5A6472', marginBottom: 6 }}>表格行</div>
              {canAppendRow && (
                <Flex vertical gap={8}>
                  <Input
                    value={rowText}
                    onChange={(event) => setRowText(event.target.value)}
                    placeholder="新增行内容，列之间用竖线分隔，如：收率 | 92.1%"
                  />
                  <Button size="small" icon={<PlusOutlined />} loading={saving} onClick={submitRow}>
                    在表格末尾新增一行
                  </Button>
                </Flex>
              )}
              {canDeleteRow && (
                <Popconfirm
                  title="删除这一行？"
                  description="只能删除空行或这次新增的行；模板里有内容的行不能删除。"
                  okText="删除"
                  cancelText="取消"
                  okButtonProps={{ danger: true }}
                  onConfirm={() => void submit([{ op: 'delete_table_row', key: item.key }])}
                >
                  <Button size="small" danger icon={<DeleteOutlined />} style={{ marginTop: 8 }} disabled={saving}>
                    删除这一行
                  </Button>
                </Popconfirm>
              )}
            </div>
          )}
        </Flex>
      </div>

      <div style={{ padding: '8px 16px', borderTop: '1px solid #EDEFF2', fontSize: 11, color: '#8C8C8C' }}>
        <Tooltip title="每次保存都会生成一个新版本，可在「版本」里回滚；人工修改过的位置会保留到下次生成">
          <span>保存后生成新版本；人工修改的位置下次重新生成会保留</span>
        </Tooltip>
      </div>
    </Flex>
  )
}