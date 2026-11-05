'use client'

import type { ReactNode } from 'react'
import { Button, Tag, Typography } from 'antd'
import { RobotOutlined, SwapOutlined } from '@ant-design/icons'

import { PermissionGate } from '@/components/auth/PermissionGate'
import { PERM } from '@/lib/permissions/codes'
import {
  PROJECT_STATUS_LABEL,
  highlightStyleLabel,
  LANGUAGE_LABEL,
  voiceLabel,
  type ProjectDetail,
  type VoiceOption,
} from '@/types/agent/ppt-video'

interface Props {
  detail: ProjectDetail
  voices: VoiceOption[]
  onOpenSettings: () => void
  onOpenSource: () => void
}

const STATUS_COLOR: Record<string, string> = {
  ready: 'green',
  failed: 'red',
  rendering: 'processing',
}

function SummaryRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 text-[12px] leading-5">
      <span className="shrink-0 text-[#A4A097]">{label}</span>
      <span className="min-w-0 text-right text-[#37352F]">{children}</span>
    </div>
  )
}

/**
 * 右栏「项目设置」：只读摘要 + 两个操作入口。
 *
 * 可编辑项全部收进「项目全局设置」抽屉，卡片本身不再承载表单，
 * 避免同一份配置在右栏和抽屉里各有一份草稿、保存后互相覆盖。
 */
export default function ProjectSettingsCard({ detail, voices, onOpenSettings, onOpenSource }: Props) {
  const currentVoice = voices.find((voice) => voice.voice_id === detail.default_voice_id)
  const highlightEnabled = detail.highlight_override_enabled
  // 未启用时摘要展示真实生效的那一档（系统默认），避免用户以为自己配的颜色丢了
  const color = highlightEnabled
    ? detail.highlight_color ?? detail.module_highlight_color
    : detail.module_highlight_color
  const styleText = highlightEnabled
    ? detail.highlight_style
      ? highlightStyleLabel(detail.highlight_style)
      : `跟随默认 · ${highlightStyleLabel(detail.module_highlight_style)}`
    : `跟随系统默认 · ${highlightStyleLabel(detail.module_highlight_style)}`

  return (
    <div className="rounded-xl border border-[#E5E3DF] bg-white p-4">
      <div className="mb-1 flex items-center justify-between">
        <Typography.Text strong>项目设置</Typography.Text>
        <Tag color={STATUS_COLOR[detail.status] ?? 'default'} className="!m-0">
          {PROJECT_STATUS_LABEL[detail.status] ?? '草稿'}
        </Tag>
      </div>
      <Typography.Text type="secondary" className="mb-3 block text-[11px] leading-4">
        这些设置作用于整个项目，单页可以单独覆盖。
      </Typography.Text>

      <div className="flex flex-col gap-1.5 border-t border-[#F0EEEB] pt-3">
        <SummaryRow label="默认语言">{LANGUAGE_LABEL[detail.default_language]}</SummaryRow>
        <SummaryRow label="默认音色">{voiceLabel(currentVoice?.display_name)}</SummaryRow>
        <SummaryRow label="默认语速">{detail.speed.toFixed(2)} 倍</SummaryRow>
        <SummaryRow label="高亮效果">
          <span className={highlightEnabled ? 'text-[#37352F]' : 'text-[#A4A097]'}>
            {highlightEnabled ? '已启用' : '未启用 · 跟随系统默认'}
          </span>
        </SummaryRow>
        <SummaryRow label="文稿高亮">{styleText}</SummaryRow>
        <SummaryRow label="高亮颜色">
          <span className="inline-flex items-center gap-2">
            <span
              aria-hidden
              className="inline-block h-3 w-3 rounded-[3px] border border-[#E5E3DF]"
              style={{ backgroundColor: color }}
            />
            <span className="tabular-nums">{color}</span>
            {!highlightEnabled && <span className="text-[11px] text-[#A4A097]">系统默认</span>}
            {highlightEnabled && !detail.highlight_color && (
              <span className="text-[11px] text-[#A4A097]">跟随默认</span>
            )}
          </span>
        </SummaryRow>
      </div>

      <PermissionGate code={PERM.pptVideoManage}>
        <div className="mt-3 flex flex-col gap-2">
          <Button type="primary" block icon={<RobotOutlined />} onClick={onOpenSettings}>
            项目全局设置
          </Button>
          <Button block icon={<SwapOutlined />} onClick={onOpenSource}>
            更换 PPT
          </Button>
        </div>
      </PermissionGate>
    </div>
  )
}