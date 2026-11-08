'use client'

import { useState, type CSSProperties } from 'react'
import { Alert, Button, Drawer, Flex, Spin, Typography } from 'antd'
import { SlotCandidatePanel } from './SlotCandidatePanel'
import { SlotStructureTable } from './SlotStructureTable'
import { SlotsDrawerToolbar } from './SlotsDrawerToolbar'
import { TemplateStructureRunsDrawer } from './TemplateStructureRunsDrawer'
import { useTemplateSlotsEditor, useTemplateSlotsQuery } from './useTemplateSlotsEditor'
import type { DocGenTemplateSlots } from '@/types/research/deliverable-template-slot'

interface Props {
  open: boolean
  templateId: string | null
  templateName: string
  onClose: () => void
  onChanged: () => void
}

const drawerStyles: { wrapper: CSSProperties; body: CSSProperties } = {
  wrapper: { width: '62vw' },
  body: { display: 'flex', flexDirection: 'column', gap: 12 },
}

/**
 * 交付物模板的槽位结构编辑器（右侧抽屉）。
 *
 * AI 识别母本难免漏选/错选，这里让人工在结构层面直接改：改字段、换绑位置、
 * 增删停用槽位，并可强制重识别（按锚点合并，人工改过的字段不被覆盖）。
 * 编辑结果写回模板的 template_structure 缓存，下一次生成生效。
 */
export function DeliverableTemplateSlotsDrawer({ open, templateId, templateName, onClose, onChanged }: Props) {
  const { data, isLoading, error, refetch } = useTemplateSlotsQuery(open, templateId)

  if (isLoading || (!data && !error)) {
    return (
      <Drawer title={`槽位结构：${templateName}`} open={open} onClose={onClose} destroyOnHidden styles={drawerStyles}>
        <Flex justify="center" style={{ padding: 48 }}>
          <Spin />
        </Flex>
      </Drawer>
    )
  }

  if (!data || !templateId) {
    return (
      <Drawer title={`槽位结构：${templateName}`} open={open} onClose={onClose} destroyOnHidden styles={drawerStyles}>
        <Alert
          type="error"
          showIcon
          title="槽位结构加载失败"
          description={error instanceof Error ? error.message : '请稍后重试'}
          action={
            <Button size="small" onClick={() => void refetch()}>
              重试
            </Button>
          }
        />
      </Drawer>
    )
  }

  return (
    <SlotsDrawerBody
      key={`${templateId}:${data.token ?? ''}`}
      payload={data}
      templateId={templateId}
      templateName={templateName}
      open={open}
      onClose={onClose}
      onChanged={onChanged}
    />
  )
}

interface BodyProps extends Omit<Props, 'templateId'> {
  payload: DocGenTemplateSlots
  templateId: string
}

/** 已拿到结构后的正文：草稿以 ``payload`` 为初始值，靠 key 保证每次打开都是新挂载 */
function SlotsDrawerBody({ payload, templateId, templateName, open, onClose, onChanged }: BodyProps) {
  const editor = useTemplateSlotsEditor({ payload, templateId, onClose, onChanged })
  const [historyOpen, setHistoryOpen] = useState(false)

  return (
    <Drawer
      title={`槽位结构：${templateName}`}
      open={open}
      onClose={editor.requestClose}
      destroyOnHidden
      styles={drawerStyles}
      extra={
        <Button size="small" onClick={() => setHistoryOpen(true)}>
          解析历史
        </Button>
      }
    >
      <SlotsDrawerToolbar
        isStale={editor.isStale}
        total={editor.total}
        enabled={editor.enabledCount}
        analyzedAt={payload.analyzed_at}
        stats={editor.stats}
        removedLabels={editor.removedLabels}
        diffOnly={editor.diffOnly}
        keyword={editor.keyword}
        panelOpen={editor.panelOpen}
        busy={editor.busy}
        saving={editor.saving}
        reparsing={editor.reparsing}
        dirty={editor.dirty}
        canSave={editor.canSave}
        onKeywordChange={editor.setKeyword}
        onToggleDiff={editor.toggleDiff}
        onBatchToggle={editor.batchToggle}
        onFillUnused={editor.fillUnused}
        onTogglePanel={editor.togglePanel}
        onReparse={editor.reparse}
        onSave={() => void editor.save()}
      />
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <SlotStructureTable
            slots={editor.slots}
            busy={editor.busy}
            loading={editor.reparsing}
            duplicateKeys={editor.duplicateKeys}
            diffStatus={editor.diffStatus}
            selectedKeys={editor.selectedKeys}
            onSelect={editor.setSelectedKeys}
            onPatch={editor.patch}
            onRemove={editor.remove}
            onRebind={(uid) => {
              editor.openPanel()
              editor.setSelectedKeys([uid])
            }}
          />
        </div>
        {editor.panelOpen && (
          <div style={{ width: 300, flexShrink: 0, height: 'calc(100vh - 430px)' }}>
            <SlotCandidatePanel
              candidates={payload.candidates ?? []}
              usedIds={editor.usedIds}
              disabled={editor.busy}
              onPick={editor.pick}
            />
          </div>
        )}
      </div>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        候选位置最多展示母本里的前 {payload.candidate_total ?? 0} 个（段落 320 / 单元格 480 上限），未被列出的位置无法绑定。
      </Typography.Text>
      <TemplateStructureRunsDrawer
        open={historyOpen}
        templateId={templateId}
        templateName={templateName}
        onClose={() => setHistoryOpen(false)}
      />
    </Drawer>
  )
}