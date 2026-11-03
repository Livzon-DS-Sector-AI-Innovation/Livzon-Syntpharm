'use client'

import { Radio, Tag, Typography } from 'antd'

import type { AiConfigItem } from '@/types/agent/ppt-video'

interface Props {
  items: AiConfigItem[]
  /** 当前选中的配置 id；null 表示「继承上一层」 */
  value: string | null
  onChange: (configId: string | null) => void
  disabled?: boolean
  /** null 选项的文案：全局视图=沿用平台默认，项目视图=沿用全局默认 */
  inheritLabel: string
  inheritHint?: string
  /** 上一层正在用的配置 id，用于打「当前继承」标记 */
  inheritedId?: string | null
}

const INHERIT = '__inherit__'

/**
 * 模型单选列表：系统预置与个人 Key 混排，一行一个，便于对比模型名。
 *
 * 选中的变化直接落库（全局默认 / 项目覆盖），所以这里不做本地态。
 */
export default function AiModelPicker({
  items,
  value,
  onChange,
  disabled,
  inheritLabel,
  inheritHint,
  inheritedId,
}: Props) {
  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-[#E5E3DF] bg-[#FAFAF9] px-4 py-6 text-center text-[13px] text-[#A4A097]">
        还没有可用的模型配置，先在「我的 Key」里添加一个。
      </div>
    )
  }

  return (
    <Radio.Group
      value={value ?? INHERIT}
      disabled={disabled}
      onChange={(event) => {
        const next = event.target.value as string
        onChange(next === INHERIT ? null : next)
      }}
      className="flex w-full flex-col gap-2"
    >
      <Radio
        value={INHERIT}
        className="!m-0 w-full rounded-xl border border-[#E5E3DF] bg-white px-3.5 py-3 hover:border-[#5645D4]/40"
      >
        <span className="flex flex-col gap-0.5">
          <span className="text-[13px] font-medium text-[#37352F]">{inheritLabel}</span>
          {inheritHint && <span className="text-[11px] text-[#A4A097]">{inheritHint}</span>}
        </span>
      </Radio>

      {items.map((item) => (
        <Radio
          key={item.id}
          value={item.id}
          className="!m-0 w-full rounded-xl border border-[#E5E3DF] bg-white px-3.5 py-3 hover:border-[#5645D4]/40"
        >
          <span className="flex flex-col gap-0.5">
            <span className="flex flex-wrap items-center gap-1.5">
              <span className="text-[13px] font-semibold text-[#37352F]">{item.model_name}</span>
              {item.visibility === 'personal' ? (
                <Tag color="purple" className="!m-0 !text-[11px]">
                  个人私有
                </Tag>
              ) : (
                <Tag className="!m-0 !text-[11px]">系统预置</Tag>
              )}
              {item.is_active && (
                <Tag color="green" className="!m-0 !text-[11px]">
                  平台启用
                </Tag>
              )}
              {inheritedId === item.id && (
                <Tag color="blue" className="!m-0 !text-[11px]">
                  当前继承
                </Tag>
              )}
            </span>
            <Typography.Text type="secondary" className="text-[11px]">
              {item.config_name} · {item.masked_api_key || '系统预置'}
            </Typography.Text>
            <Typography.Text type="secondary" className="truncate text-[11px]">
              {item.api_base_url}
            </Typography.Text>
          </span>
        </Radio>
      ))}
    </Radio.Group>
  )
}