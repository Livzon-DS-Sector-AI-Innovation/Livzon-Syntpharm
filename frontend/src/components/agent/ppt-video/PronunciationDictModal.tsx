'use client'

import { useState } from 'react'
import { App, Button, Input, Modal, Space, Typography } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'

import { updateProjectSettings } from '@/actions/agent/ppt-video'
import type { ProjectDetail } from '@/types/agent/ppt-video'

interface DictRow {
  key: string
  value: string
}

interface Props {
  open: boolean
  detail: ProjectDetail
  onClose: () => void
  onSaved: (detail: ProjectDetail) => void
}

function rowsFromDetail(detail: ProjectDetail): DictRow[] {
  const entries = Object.entries(detail.pronunciation_dict ?? {})
  return entries.length ? entries.map(([key, value]) => ({ key, value })) : [{ key: '', value: '' }]
}

/**
 * 项目级发音词典：原文 → 合成替代文本。
 *
 * 只影响「送 TTS 的文本」，讲稿与高亮匹配保持原样；
 * 保存后词条指纹变化，受影响页面的旧音频会自动失效，试听即重新合成。
 */
export default function PronunciationDictModal({ open, detail, onClose, onSaved }: Props) {
  const { message } = App.useApp()
  // 每次打开由父组件用 key 重新挂载，草稿直接从最新 detail 初始化（不在 effect 里 setState）
  const [rows, setRows] = useState<DictRow[]>(() => rowsFromDetail(detail))
  const [saving, setSaving] = useState(false)

  const updateRow = (index: number, patch: Partial<DictRow>) => {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  const handleSave = async () => {
    const payload: Record<string, string> = {}
    for (const row of rows) {
      const source = row.key.trim()
      const target = row.value.trim()
      if (source && target && source !== target) payload[source] = target
    }
    setSaving(true)
    const result = await updateProjectSettings(detail.id, { pronunciation_dict: payload })
    setSaving(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    onSaved(result.data)
    message.success('发音词典已保存；受影响页面试听时会重新合成')
    onClose()
  }

  return (
    <Modal
      title="发音词典"
      open={open}
      onCancel={onClose}
      width={640}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
            保存
          </Button>
        </Space>
      }
    >
      <Typography.Paragraph type="secondary" className="!text-[12px]">
        只替换「送语音合成的文本」，讲稿与页面高亮不受影响。用于多音字与专业词，例如把
        「重楼」写成「崇楼」、「大黄」写成「代黄」、「μg」写成「微克」。右侧必须是同音字，不能写拼音。
        保存后改用词条会影响音频缓存，相关页面试听时会重新合成。
      </Typography.Paragraph>
      <div className="flex flex-col gap-2">
        <div className="grid grid-cols-[1fr_1fr_32px] gap-2 text-[12px] text-[#5D5B54]">
          <span>原文（讲稿里出现的词）</span>
          <span>合成时替换成</span>
          <span />
        </div>
        {rows.map((row, index) => (
          <div key={index} className="grid grid-cols-[1fr_1fr_32px] items-center gap-2">
            <Input
              value={row.key}
              maxLength={32}
              placeholder="如：重楼"
              onChange={(event) => updateRow(index, { key: event.target.value })}
            />
            <Input
              value={row.value}
              maxLength={64}
              placeholder="如：崇楼"
              onChange={(event) => updateRow(index, { value: event.target.value })}
            />
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={rows.length <= 1}
              onClick={() => setRows((current) => current.filter((_, i) => i !== index))}
            />
          </div>
        ))}
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={() => setRows((current) => [...current, { key: '', value: '' }])}
        >
          新增词条
        </Button>
      </div>
      <Typography.Paragraph type="secondary" className="!mb-0 !mt-3 !text-[11px]">
        单项目最多 500 条；保存后在单页编辑区点「试听」确认读音，再提交渲染。
      </Typography.Paragraph>
    </Modal>
  )
}