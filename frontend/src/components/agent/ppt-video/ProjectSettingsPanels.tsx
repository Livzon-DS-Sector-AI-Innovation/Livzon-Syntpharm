'use client'

import { Alert, Checkbox, ColorPicker, Input, Select, Slider, Typography } from 'antd'

import HighlightPreview from './HighlightPreview'
import {
  HIGHLIGHT_STYLE_OPTIONS,
  LANGUAGE_LABEL,
  highlightStyleLabel,
  type LanguageCode,
  type ProjectDetail,
  type ProjectUpdatePayload,
  type VoiceOption,
} from '@/types/agent/ppt-video'

/** 系统默认样式为空时（模块未配置）按文字变色预览，与后端 DEFAULTS 一致 */
const FALLBACK_STYLE = 'text_recolor'

/** 抽屉里「语言与配音」「文稿高亮」共用的草稿；两页签同进同出，避免各自提交覆盖对方 */
export interface ProjectSettingsDraft {
  name: string
  language: LanguageCode
  voiceId: string
  speed: number
  highlightEnabled: boolean
  highlightStyle: string | null
  highlightColor: string | null
}

export function draftFromDetail(detail: ProjectDetail): ProjectSettingsDraft {
  return {
    name: detail.name,
    language: detail.default_language,
    voiceId: detail.default_voice_id,
    speed: detail.speed,
    highlightEnabled: detail.highlight_override_enabled,
    highlightStyle: detail.highlight_style ?? null,
    highlightColor: detail.highlight_color ?? null,
  }
}

/** 空串 = 清除项目覆盖、回到跟随模块默认；后端按同一语义处理 */
export function buildProjectUpdatePayload(draft: ProjectSettingsDraft): ProjectUpdatePayload {
  return {
    name: draft.name.trim() || undefined,
    default_language: draft.language,
    default_voice_id: draft.voiceId || undefined,
    speed: draft.speed,
    highlight_override_enabled: draft.highlightEnabled,
    highlight_style: draft.highlightStyle ?? '',
    highlight_color: draft.highlightColor ?? '',
  }
}

export function isProjectDraftDirty(draft: ProjectSettingsDraft, detail: ProjectDetail): boolean {
  return (
    draft.name.trim() !== detail.name ||
    draft.language !== detail.default_language ||
    draft.voiceId !== detail.default_voice_id ||
    Math.abs(draft.speed - detail.speed) > 0.001 ||
    draft.highlightEnabled !== detail.highlight_override_enabled ||
    draft.highlightStyle !== (detail.highlight_style ?? null) ||
    draft.highlightColor !== (detail.highlight_color ?? null)
  )
}

const FIELD_LABEL = 'mb-1 block text-[12px] text-[#5D5B54]'
const FIELD_HINT = 'mt-1 block text-[11px] leading-4 text-[#A4A097]'

interface VoicePanelProps {
  value: ProjectSettingsDraft
  voices: VoiceOption[]
  onChange: (patch: Partial<ProjectSettingsDraft>) => void
  disabled?: boolean
}

/** 语言与配音：项目名 + 默认语言 + 默认音色 + 默认语速 */
export function ProjectVoicePanel({ value, voices, onChange, disabled }: VoicePanelProps) {
  const options = voices.filter((voice) => voice.language === value.language)
  const current = voices.find((voice) => voice.voice_id === value.voiceId)

  return (
    <div className="flex flex-col gap-4">
      <div>
        <label className={FIELD_LABEL} htmlFor="project-name">
          项目名
        </label>
        <Input
          id="project-name"
          value={value.name}
          maxLength={255}
          disabled={disabled}
          placeholder="给这个项目起个好认的名字"
          onChange={(event) => onChange({ name: event.target.value })}
        />
        <span className={FIELD_HINT}>只影响列表与页面标题的显示，不改变已生成的内容。</span>
      </div>

      <div>
        <span className={FIELD_LABEL}>默认语言</span>
        <Select<LanguageCode>
          className="w-full"
          value={value.language}
          disabled={disabled}
          options={[
            { value: 'zh', label: LANGUAGE_LABEL.zh },
            { value: 'en', label: LANGUAGE_LABEL.en },
          ]}
          onChange={(language) => {
            // 换语言必须同时换音色，否则会出现「中文音色读英文」的空音轨
            const fallback = voices.find((voice) => voice.language === language)
            onChange({ language, voiceId: fallback?.voice_id ?? '' })
          }}
        />
        <span className={FIELD_HINT}>新建页面默认用这个语言，单页可以单独指定。</span>
      </div>

      <div>
        <span className={FIELD_LABEL}>默认音色</span>
        <Select
          className="w-full"
          value={value.voiceId || undefined}
          disabled={disabled}
          placeholder="选择一个音色"
          options={options.map((voice) => ({
            value: voice.voice_id,
            label: voice.display_name,
            title: voice.description,
          }))}
          onChange={(voiceId: string) => onChange({ voiceId })}
        />
        <span className={FIELD_HINT}>{current?.description || '选择后这里会说明这个音色的听感。'}</span>
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between">
          <span className="text-[12px] text-[#5D5B54]">默认语速</span>
          <span className="text-[12px] tabular-nums text-[#37352F]">{value.speed.toFixed(2)} 倍</span>
        </div>
        <Slider
          min={0.5}
          max={2}
          step={0.05}
          value={value.speed}
          disabled={disabled}
          tooltip={{ formatter: (next) => `${Number(next).toFixed(2)} 倍` }}
          onChange={(speed) => onChange({ speed })}
        />
        <span className={FIELD_HINT}>1.00 倍是正常语速，0.9 倍更从容，1.1 倍更紧凑。</span>
      </div>
    </div>
  )
}

interface HighlightPanelProps {
  value: ProjectSettingsDraft
  detail: ProjectDetail
  onChange: (patch: Partial<ProjectSettingsDraft>) => void
  disabled?: boolean
}

/** 文稿高亮：开关 + 样式 + 主色；开关关闭时两项置灰，但已选值保留在草稿里 */
export function ProjectHighlightPanel({ value, detail, onChange, disabled }: HighlightPanelProps) {
  const systemStyle = detail.module_highlight_style || FALLBACK_STYLE
  const systemColor = detail.module_highlight_color
  // 模块总闸（参数设置里的 AGENT_PPT_VIDEO_HIGHLIGHT_ENABLED）：关掉后任何层级都不出高亮
  const moduleEnabled = detail.script_runtime?.highlight_enabled !== false
  const enabled = value.highlightEnabled
  // 预览取「勾选后会用到的样式」：开关关闭时项目配置不参与，展示系统默认
  const effectiveStyle = enabled ? (value.highlightStyle ?? systemStyle) : systemStyle
  const effectiveColor = (enabled ? (value.highlightColor ?? systemColor) : systemColor) || systemColor
  const controlsDisabled = disabled || !enabled

  return (
    <div className="flex flex-col gap-4">
      {!moduleEnabled && (
        <Alert
          type="warning"
          showIcon
          message="模块总闸已关闭，所有页面都不会高亮"
          description="到「参数设置」里打开「PPT 视频 · 高亮效果」总开关后，这里的设置才会生效。"
        />
      )}

      <div className="rounded-lg border border-[#E5E3DF] bg-[#FAFAF9] px-3 py-2.5">
        <Checkbox
          checked={enabled}
          disabled={disabled}
          onChange={(event) => onChange({ highlightEnabled: event.target.checked })}
        >
          <span className="text-[13px] font-medium text-[#37352F]">高亮效果</span>
        </Checkbox>
        <span className="mt-1 block pl-6 text-[11px] leading-4 text-[#A4A097]">
          {enabled
            ? '本项目按下面的样式与颜色做高亮。'
            : '未勾选时整条成片没有高亮；已选的样式与颜色会保留，勾选后立即恢复。单页仍可单独开启。'}
        </span>
      </div>

      <div>
        <span className={FIELD_LABEL}>高亮样式</span>
        <Select
          className="w-full"
          allowClear
          value={value.highlightStyle ?? undefined}
          disabled={controlsDisabled}
          placeholder={`跟随默认（${highlightStyleLabel(systemStyle)}）`}
          options={HIGHLIGHT_STYLE_OPTIONS}
          onChange={(style?: string) => onChange({ highlightStyle: style ?? null })}
        />
        <span className={FIELD_HINT}>
          留空就用系统默认的「{highlightStyleLabel(systemStyle)}」，保存后重新生成视频即可看到。
        </span>
      </div>

      <div>
        <span className={FIELD_LABEL}>高亮颜色</span>
        <div className="flex items-center gap-2">
          <ColorPicker
            value={effectiveColor}
            disabled={controlsDisabled}
            showText
            disabledAlpha
            onChangeComplete={(color) => onChange({ highlightColor: color.toHexString().toUpperCase() })}
          />
          <span className="text-[11px] text-[#A4A097]">系统默认色 {systemColor}</span>
          {value.highlightColor && (
            <button
              type="button"
              className="ml-auto text-[12px] text-[#5645D4] hover:text-[#4534B3] disabled:cursor-not-allowed disabled:text-[#A4A097]"
              disabled={controlsDisabled}
              onClick={() => onChange({ highlightColor: null })}
            >
              恢复默认
            </button>
          )}
        </div>
        <span className={FIELD_HINT}>
          只给讲到的内容上色，未讲到的部分保持原样；颜色越醒目，观众视线越集中。
        </span>
      </div>

      <HighlightPreview
        style={effectiveStyle}
        color={effectiveColor}
        enabled={enabled}
        note={enabled ? '本项目设置' : '项目未启用 · 成片无高亮'}
      />

      <Typography.Text type="secondary" className="text-[11px] leading-4">
        保存后重新生成视频生效；单独勾选过高亮的页面仍按自己的设置。
      </Typography.Text>
    </div>
  )
}