'use client'

import { useEffect, useRef, useState } from 'react'
import { Alert, App, Button, Drawer, Space, Tabs, Typography } from 'antd'
import { RobotOutlined } from '@ant-design/icons'

import AiGuidePanel from './AiGuidePanel'
import AiKeyPanel from './AiKeyPanel'
import AiModelPicker, { encodeModelValue } from './AiModelPicker'
import {
  ProjectHighlightPanel,
  ProjectVoicePanel,
  buildProjectUpdatePayload,
  draftFromDetail,
  isProjectDraftDirty,
  type ProjectSettingsDraft,
} from './ProjectSettingsPanels'
import {
  loadAiConfigs,
  saveGlobalAiSettings,
  saveProjectAiSettings,
  updateProjectSettings,
} from '@/actions/agent/ppt-video'
import {
  MODEL_SOURCE_HINT,
  MODEL_SOURCE_LABEL,
  type AiConfigListResponse,
  type ModelSource,
  type ProjectDetail,
  type VoiceOption,
} from '@/types/agent/ppt-video'

interface Props {
  open: boolean
  onClose: () => void
  /** global：列表页的全局默认；project：工作台的项目设置 */
  mode: 'global' | 'project'
  /** 全局视图的首屏数据（RSC 传入），为空时抽屉内自取 */
  configs: AiConfigListResponse | null
  detail?: ProjectDetail | null
  /** 项目视图的音色目录，由工作台 RSC 一次取好传下来 */
  voices?: VoiceOption[]
  onConfigsChange?: (next: AiConfigListResponse) => void
  onDetailChange?: (next: ProjectDetail) => void
}

/**
 * AI 配置抽屉：把「用哪个模型」「自己的 Key」「怎么写讲稿」放在一处。
 *
 * 全局视图：模型/自定义模型/指南三页签，模型即选即存、指南单独保存。
 * 项目视图：四页签，模型与指南沿用上面的即存语义；语言/音色/语速/高亮合成一份
 * 草稿一次提交，避免四个页签各自 PATCH 同一行时互相覆盖旧值。
 */
export default function AiConfigDrawer({
  open,
  onClose,
  mode,
  configs,
  detail,
  voices,
  onConfigsChange,
  onDetailChange,
}: Props) {
  const { message, modal } = App.useApp()
  // 首屏数据来自 RSC/props，本地只在刷新与保存后覆盖，避免用 effect 同步 props
  const [localData, setLocalData] = useState<AiConfigListResponse | null>(null)
  const data = localData ?? configs
  // 用户改过才用草稿值；没改过就跟随当前作用域的数据源，关抽屉即丢弃草稿
  const [guideDraft, setGuideDraft] = useState<string | null>(null)
  const guide = guideDraft ?? (mode === 'project' ? (detail?.script_guide ?? '') : (data?.global_guide ?? ''))
  const [saving, setSaving] = useState(false)
  // 项目设置草稿：只在抽屉「关 → 开」时按当前详情重置；开着时不回填，避免轮询覆盖用户输入
  const [draft, setDraft] = useState<ProjectSettingsDraft | null>(null)
  const prevOpen = useRef(false)
  useEffect(() => {
    if (open && !prevOpen.current && mode === 'project' && detail) {
      setDraft(draftFromDetail(detail))
    }
    prevOpen.current = open
  }, [open, mode, detail])

  const setData = (next: AiConfigListResponse) => {
    setLocalData(next)
    onConfigsChange?.(next)
  }

  // 项目视图没有 RSC 首屏数据，抽屉打开时自取一次（含 can_manage_global 与全局默认）
  useEffect(() => {
    if (!open || data) return
    let cancelled = false
    void loadAiConfigs().then((result) => {
      if (cancelled || !result.success || !result.data) return
      setLocalData(result.data)
      onConfigsChange?.(result.data)
    })
    return () => {
      cancelled = true
    }
  }, [open, data, onConfigsChange])

  const draftDirty = Boolean(mode === 'project' && detail && draft && isProjectDraftDirty(draft, detail))
  const guideDirty =
    guideDraft !== null &&
    guideDraft.trim() !==
      (mode === 'project' ? (detail?.script_guide ?? '') : (data?.global_guide ?? '')).trim()

  const handleClose = () => {
    if (!draftDirty && !guideDirty) {
      setGuideDraft(null)
      onClose()
      return
    }
    modal.confirm({
      title: '放弃未保存的改动？',
      content: '还有没保存的内容，关闭后会丢失。',
      okText: '放弃改动',
      cancelText: '继续编辑',
      okButtonProps: { danger: true },
      onOk: () => {
        setGuideDraft(null)
        setDraft(detail ? draftFromDetail(detail) : null)
        onClose()
      },
    })
  }

  const refresh = async () => {
    const result = await loadAiConfigs()
    if (!result.success || !result.data) {
      message.error(result.message || '读取模型配置失败')
      return
    }
    setData(result.data)
    onConfigsChange?.(result.data)
  }

  const canManageGlobal = data?.can_manage_global ?? false
  const items = data?.items ?? []
  const globalItem = items.find((item) => item.id === data?.global_default_id) ?? null
  // 全局默认模型名可能为空（旧数据），此时按该配置的默认模型展示
  const globalModel = data?.global_default_model || globalItem?.model_name || ''
  const runtime = detail?.script_runtime ?? null

  /** 把「配置 id + 模型名」编码成 Radio 的单值；模型名缺失时回落到配置默认模型 */
  const toSelection = (configId?: string | null, modelName?: string | null): string | null => {
    if (!configId) return null
    const item = items.find((entry) => entry.id === configId)
    const model = modelName || item?.model_name
    return model ? encodeModelValue(configId, model) : null
  }

  const effective: { model: string; source: ModelSource } =
    mode === 'project' && runtime
      ? { model: runtime.model_name, source: runtime.source }
      : globalItem
        ? { model: globalModel, source: 'global' }
        : { model: '平台默认模型', source: 'active' }

  const handleSelectGlobal = async (selection: { configId: string; modelName: string } | null) => {
    setSaving(true)
    const result = await saveGlobalAiSettings(
      selection
        ? { global_config_id: selection.configId, global_model_name: selection.modelName }
        : { clear_global_config: true },
    )
    setSaving(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    setData(result.data)
    onConfigsChange?.(result.data)
    message.success(selection ? '全局默认模型已更新' : '已改为沿用平台默认模型')
  }

  const handleSelectProject = async (selection: { configId: string; modelName: string } | null) => {
    if (!detail) return
    setSaving(true)
    const result = await saveProjectAiSettings(
      detail.id,
      selection
        ? { llm_config_id: selection.configId, llm_model_name: selection.modelName }
        : { clear_config: true },
    )
    setSaving(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    onDetailChange?.(result.data)
    message.success(selection ? '本项目模型已更新' : '已改为沿用全局默认模型')
  }

  const handleSaveGuide = async () => {
    setSaving(true)
    const trimmed = guide.trim()
    if (mode === 'project') {
      if (!detail) {
        setSaving(false)
        return
      }
      const result = await saveProjectAiSettings(detail.id, {
        script_guide: trimmed || null,
        clear_guide: !trimmed,
      })
      setSaving(false)
      if (!result.success || !result.data) {
        message.error(result.message)
        return
      }
      onDetailChange?.(result.data)
      setGuideDraft(null)
      message.success(trimmed ? '项目文稿提示词指南已保存' : '已清空项目指南，跟随全局')
      return
    }
    const result = await saveGlobalAiSettings({ global_guide: trimmed || null, clear_global_guide: !trimmed })
    setSaving(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    setData(result.data)
    setGuideDraft(null)
    message.success(trimmed ? '全局文稿提示词指南已保存' : '已清空全局指南')
  }

  const handleClearProject = async () => {
    if (!detail) return
    setSaving(true)
    const result = await saveProjectAiSettings(detail.id, { clear_config: true, clear_guide: true })
    setSaving(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    setGuideDraft(null)
    onDetailChange?.(result.data)
    message.success('已恢复为全局默认')
  }

  /** 语言/音色/语速/高亮合并提交：一次 PATCH 写完，避免多页签并发提交互相覆盖 */
  const handleSaveProjectSettings = async () => {
    if (!detail || !draft) return
    if (!draft.name.trim()) {
      message.warning('项目名不能为空')
      return
    }
    if (!draft.voiceId) {
      message.warning('请先选择一个默认音色')
      return
    }
    setSaving(true)
    const result = await updateProjectSettings(detail.id, buildProjectUpdatePayload(draft))
    setSaving(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    onDetailChange?.(result.data)
    setDraft(draftFromDetail(result.data))
    message.success('项目设置已保存')
  }

  const patchDraft = (patch: Partial<ProjectSettingsDraft>) => {
    setDraft((current) => (current ? { ...current, ...patch } : current))
  }

  const maxChars = data?.script_guide_max_chars ?? 2000

  const modelTab =
    mode === 'project' ? (
      <div className="flex flex-col gap-3">
        {!canManageGlobal && (
          <Alert
            type="info"
            showIcon
            message="全局模型由平台管理员设定"
            description="你可以为这个项目单独指定模型；想添加自己的模型，请到列表页的「模型配置」里操作。"
          />
        )}
        <AiModelPicker
          items={items}
          value={toSelection(detail?.llm_config_id, detail?.llm_model_name)}
          onChange={handleSelectProject}
          disabled={saving}
          inheritLabel="沿用全局默认模型"
          inheritHint={globalItem ? `当前全局：${globalModel}` : '全局尚未指定，使用平台启用的模型'}
          inheritedId={data?.global_default_id ?? null}
        />
      </div>
    ) : (
      <div className="flex flex-col gap-3">
        {!canManageGlobal && (
          <Alert
            type="warning"
            showIcon
            message="当前账号不能修改全局模型"
            description="全局默认模型只能由平台管理员修改；你可以添加自己的模型，只给你自己用。"
          />
        )}
        <AiModelPicker
          items={items}
          value={toSelection(data?.global_default_id, data?.global_default_model)}
          onChange={handleSelectGlobal}
          disabled={!canManageGlobal || saving}
          inheritLabel="沿用平台默认模型"
          inheritHint="不指定时按平台管理后台启用的文本模型"
        />
      </div>
    )

  const guideTab = (
    <AiGuidePanel
      value={guide}
      onChange={setGuideDraft}
      maxChars={maxChars}
      readOnly={mode === 'global' && !canManageGlobal}
      scope={mode}
      inherited={data?.global_guide ?? ''}
    />
  )

  const settingsPlaceholder = (
    <Typography.Text type="secondary" className="text-[12px]">
      正在读取项目设置…
    </Typography.Text>
  )

  const voiceTab =
    draft && detail ? (
      <ProjectVoicePanel value={draft} voices={voices ?? []} onChange={patchDraft} disabled={saving} />
    ) : (
      settingsPlaceholder
    )

  const highlightTab =
    draft && detail ? (
      <ProjectHighlightPanel value={draft} detail={detail} onChange={patchDraft} disabled={saving} />
    ) : (
      settingsPlaceholder
    )

  const tabs =
    mode === 'project'
      ? [
          { key: 'model', label: '模型', children: modelTab },
          { key: 'guide', label: '文稿提示词指南', children: guideTab },
          { key: 'voice', label: '语言与配音', children: voiceTab },
          { key: 'highlight', label: '文稿高亮', children: highlightTab },
        ]
      : [
          { key: 'model', label: '模型', children: modelTab },
          { key: 'keys', label: '自定义模型', children: <AiKeyPanel items={items} onChanged={refresh} /> },
          { key: 'guide', label: '文稿提示词指南', children: guideTab },
        ]

  return (
    <Drawer
      forceRender
      size={480}
      open={open}
      onClose={handleClose}
      destroyOnHidden
      title={
        <span className="flex items-center gap-2">
          <RobotOutlined className="text-[#5645D4]" />
          {mode === 'project' ? '项目全局设置' : 'AI 配置'}
        </span>
      }
      styles={{
        header: { borderBottom: '1px solid #e5e3df', padding: '16px 24px' },
        body: { padding: '16px 24px', background: '#FCFCFB' },
        footer: { borderTop: '1px solid #e5e3df', padding: '12px 24px' },
      }}
      footer={
        <Space className="w-full justify-end">
          {mode === 'project' &&
            (detail?.llm_config_id || detail?.llm_model_name || detail?.script_guide) && (
              <Button onClick={handleClearProject} loading={saving}>
                清除模型与指南覆盖
              </Button>
            )}
          <Button onClick={handleClose}>关闭</Button>
          {mode === 'project' ? (
            <Button type="primary" loading={saving} disabled={!draftDirty} onClick={handleSaveProjectSettings}>
              保存设置
            </Button>
          ) : (
            <Button type="primary" loading={saving} onClick={handleSaveGuide} disabled={!canManageGlobal}>
              保存文稿提示词指南
            </Button>
          )}
        </Space>
      }
    >
      <div className="mb-3 flex flex-col gap-1">
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-[#F4F1FE] px-2.5 py-1 text-[12px] text-[#5645D4]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#5645D4]" />
          当前生效：{effective.model} · {MODEL_SOURCE_LABEL[effective.source]}
        </span>
        <Typography.Text type="secondary" className="text-[11px]">
          {MODEL_SOURCE_HINT[effective.source]}
        </Typography.Text>
      </div>

      <Tabs size="small" items={tabs} />
    </Drawer>
  )
}