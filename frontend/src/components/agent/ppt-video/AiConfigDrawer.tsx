'use client'

import { useEffect, useState } from 'react'
import { Alert, App, Button, Drawer, Space, Tabs, Typography } from 'antd'
import { RobotOutlined } from '@ant-design/icons'

import AiGuidePanel from './AiGuidePanel'
import AiKeyPanel from './AiKeyPanel'
import AiModelPicker from './AiModelPicker'
import { loadAiConfigs, saveGlobalAiSettings, saveProjectAiSettings } from '@/actions/agent/ppt-video'
import {
  MODEL_SOURCE_HINT,
  MODEL_SOURCE_LABEL,
  type AiConfigListResponse,
  type ModelSource,
  type ProjectDetail,
} from '@/types/agent/ppt-video'

interface Props {
  open: boolean
  onClose: () => void
  /** global：列表页的全局默认；project：工作台的项目覆盖 */
  mode: 'global' | 'project'
  /** 全局视图的首屏数据（RSC 传入），为空时抽屉内自取 */
  configs: AiConfigListResponse | null
  detail?: ProjectDetail | null
  onConfigsChange?: (next: AiConfigListResponse) => void
  onDetailChange?: (next: ProjectDetail) => void
}

/**
 * AI 配置抽屉：把「用哪个模型」「自己的 Key」「怎么写讲稿」放在一处。
 *
 * 模型选择即保存，风格指南单独点保存——两者写的是不同字段，避免改指南时把
 * 用户刚选的模型一起提交成旧值。
 */
export default function AiConfigDrawer({
  open,
  onClose,
  mode,
  configs,
  detail,
  onConfigsChange,
  onDetailChange,
}: Props) {
  const { message } = App.useApp()
  // 首屏数据来自 RSC/props，本地只在刷新与保存后覆盖，避免用 effect 同步 props
  const [localData, setLocalData] = useState<AiConfigListResponse | null>(null)
  const data = localData ?? configs
  // 用户改过才用草稿值；没改过就跟随当前作用域的数据源，关抽屉即丢弃草稿
  const [guideDraft, setGuideDraft] = useState<string | null>(null)
  const guide = guideDraft ?? (mode === 'project' ? (detail?.script_guide ?? '') : (data?.global_guide ?? ''))
  const [saving, setSaving] = useState(false)

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

  const handleClose = () => {
    setGuideDraft(null)
    onClose()
  }

  const refresh = async () => {
    const result = await loadAiConfigs()
    if (!result.success || !result.data) {
      message.error(result.message || '读取 AI 配置失败')
      return
    }
    setData(result.data)
    onConfigsChange?.(result.data)
  }

  const canManageGlobal = data?.can_manage_global ?? false
  const globalItem = (data?.items ?? []).find((item) => item.id === data?.global_default_id) ?? null
  const runtime = detail?.script_runtime ?? null

  const effective: { model: string; source: ModelSource } =
    mode === 'project' && runtime
      ? { model: runtime.model_name, source: runtime.source }
      : globalItem
        ? { model: globalItem.model_name, source: 'global' }
        : { model: '平台默认模型', source: 'active' }

  const handleSelectGlobal = async (configId: string | null) => {
    setSaving(true)
    const result = await saveGlobalAiSettings({ global_config_id: configId })
    setSaving(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    setData(result.data)
    onConfigsChange?.(result.data)
    message.success(configId ? '全局默认模型已更新' : '已改为沿用平台默认模型')
  }

  const handleSelectProject = async (configId: string | null) => {
    if (!detail) return
    setSaving(true)
    const result = await saveProjectAiSettings(
      detail.id,
      configId ? { llm_config_id: configId } : { clear_config: true },
    )
    setSaving(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    onDetailChange?.(result.data)
    message.success(configId ? '本项目模型已更新' : '已改为沿用全局默认模型')
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
      message.success(trimmed ? '项目风格指南已保存' : '已清空项目指南，跟随全局')
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
    message.success(trimmed ? '全局风格指南已保存' : '已清空全局指南')
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
    message.success('已清除项目覆盖，全部跟随全局')
  }

  const maxChars = data?.script_guide_max_chars ?? 2000
  const items = data?.items ?? []

  const modelTab =
    mode === 'project' ? (
      <div className="flex flex-col gap-3">
        {!canManageGlobal && (
          <Alert
            type="info"
            showIcon
            message="全局模型由平台管理员设定"
            description="你可以为当前项目单独指定模型；个人 Key 请到「AI 配置」里添加。"
          />
        )}
        <AiModelPicker
          items={items}
          value={detail?.llm_config_id ?? null}
          onChange={handleSelectProject}
          disabled={saving}
          inheritLabel="沿用全局默认模型"
          inheritHint={globalItem ? `当前全局：${globalItem.model_name}` : '全局尚未指定，使用平台启用的模型'}
          inheritedId={data?.global_default_id ?? null}
        />
      </div>
    ) : (
      <div className="flex flex-col gap-3">
        {!canManageGlobal && (
          <Alert
            type="warning"
            showIcon
            message="没有全局配置权限"
            description="全局默认模型只能由平台管理员修改，你可以添加自己的 Key 供个人使用。"
          />
        )}
        <AiModelPicker
          items={items}
          value={data?.global_default_id ?? null}
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

  const tabs =
    mode === 'project'
      ? [
          { key: 'model', label: '模型', children: modelTab },
          { key: 'guide', label: '风格指南', children: guideTab },
        ]
      : [
          { key: 'model', label: '模型', children: modelTab },
          { key: 'keys', label: '我的 Key', children: <AiKeyPanel items={items} onChanged={refresh} /> },
          { key: 'guide', label: '风格指南', children: guideTab },
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
          {mode === 'project' ? '项目 AI 设置' : 'AI 配置'}
        </span>
      }
      styles={{
        header: { borderBottom: '1px solid #e5e3df', padding: '16px 24px' },
        body: { padding: '16px 24px', background: '#FCFCFB' },
        footer: { borderTop: '1px solid #e5e3df', padding: '12px 24px' },
      }}
      footer={
        <Space className="w-full justify-end">
          {mode === 'project' && (detail?.llm_config_id || detail?.script_guide) && (
            <Button onClick={handleClearProject} loading={saving}>
              清除项目覆盖
            </Button>
          )}
          <Button onClick={handleClose}>关闭</Button>
          <Button
            type="primary"
            loading={saving}
            onClick={handleSaveGuide}
            disabled={mode === 'global' && !canManageGlobal}
          >
            保存风格指南
          </Button>
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