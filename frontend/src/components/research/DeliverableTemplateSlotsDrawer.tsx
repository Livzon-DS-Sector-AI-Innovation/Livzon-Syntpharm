'use client'

import { useState, type CSSProperties } from 'react'
import { Alert, App, Button, Drawer, Flex, Space, Spin, Tooltip, Typography } from 'antd'
import { FileWordOutlined } from '@ant-design/icons'
import { generateDeliverableTemplateSample } from '@/actions/research/deliverable-template'
import { DeliverableSamplePreviewModal, type SamplePreviewTarget } from './DeliverableSamplePreviewModal'
import { ReportGenExampleDrawer } from './ReportGenExampleDrawer'
import { ReparseProgressPanel } from './ReparseProgressPanel'
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
      <Drawer title={`填充项设置：${templateName}`} open={open} onClose={onClose} destroyOnHidden styles={drawerStyles}>
        <Flex justify="center" style={{ padding: 48 }}>
          <Spin />
        </Flex>
      </Drawer>
    )
  }

  if (!data || !templateId) {
    return (
      <Drawer title={`填充项设置：${templateName}`} open={open} onClose={onClose} destroyOnHidden styles={drawerStyles}>
        <Alert
          type="error"
          showIcon
          title="填充项设置没能加载出来"
          description={error instanceof Error ? error.message : '请稍后重试，或关掉重开一次'}
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
  const { message: msgApi } = App.useApp()
  const editor = useTemplateSlotsEditor({ payload, templateId, onClose, onChanged })
  const [historyOpen, setHistoryOpen] = useState(false)
  const [examplesOpen, setExamplesOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [sampleTarget, setSampleTarget] = useState<SamplePreviewTarget | null>(null)

  /**
   * 生成示例稿。
   *
   * 只能基于已保存的结构：草稿态下生成的稿子会和表格里看到的对不上，所以有改动时直接拦住。
   */
  const generateSample = async () => {
    if (editor.dirty) {
      msgApi.warning('填充项还有未保存的修改，先保存再生成示例稿')
      return
    }
    setGenerating(true)
    try {
      const data = await generateDeliverableTemplateSample(templateId)
      setSampleTarget({
        templateId,
        fileName: `${templateName}-填充示例-v${data.version_no}.docx`,
        data,
      })
      msgApi.success(`已生成填充示例稿 v${data.version_no}`)
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '生成示例稿失败')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <Drawer
      title={`填充项设置：${templateName}`}
      open={open}
      onClose={editor.requestClose}
      destroyOnHidden
      styles={drawerStyles}
      extra={
        <Space size={8}>
          <Tooltip
            title={
              editor.dirty
                ? '填充项还有未保存的修改，先保存再生成'
                : '按已保存的填充项生成一份带标记的 Word：标出每处在哪、该填什么，可直接对照补充'
            }
          >
            {/* 禁用态的 Tooltip 需要包一层原生元素才收得到 hover 事件 */}
            <span style={{ display: 'inline-block' }}>
              <Button
                size="small"
                icon={<FileWordOutlined />}
                loading={generating}
                disabled={editor.dirty}
                onClick={() => void generateSample()}
              >
                生成示例稿
              </Button>
            </span>
          </Tooltip>
          <Tooltip title="给某些填充项准备「照抄的写法」，下次生成更贴近你们的口径">
            <Button size="small" onClick={() => setExamplesOpen(true)}>
              示例写法
            </Button>
          </Tooltip>
          <Tooltip title="看每次系统挑了哪些位置、人工又改了什么">
            <Button size="small" onClick={() => setHistoryOpen(true)}>
              分析记录
            </Button>
          </Tooltip>
        </Space>
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
      <ReparseProgressPanel progress={editor.reparseProgress} />
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
        可填位置最多只展示模板文件里的前 {payload.candidate_total ?? 0} 个（段落 320 / 单元格 480 上限），没列出来的位置暂时无法绑定。
      </Typography.Text>
      <ReportGenExampleDrawer
        open={examplesOpen}
        templateId={templateId}
        templateName={templateName}
        onClose={() => setExamplesOpen(false)}
      />
      <TemplateStructureRunsDrawer
        open={historyOpen}
        templateId={templateId}
        templateName={templateName}
        onClose={() => setHistoryOpen(false)}
      />
      <DeliverableSamplePreviewModal target={sampleTarget} onClose={() => setSampleTarget(null)} />
    </Drawer>
  )
}