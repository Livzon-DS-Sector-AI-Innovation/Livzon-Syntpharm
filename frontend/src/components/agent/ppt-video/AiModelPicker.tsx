'use client'

import { useMemo } from 'react'
import { Radio, Tag, Typography } from 'antd'

import type { AiConfigItem } from '@/types/agent/ppt-video'

/** 选择项是「配置 + 模型」二元组，用这个分隔符编码成单值给 Radio.Group */
export const MODEL_VALUE_SEPARATOR = '::'

export function encodeModelValue(configId: string, modelName: string): string {
  return `${configId}${MODEL_VALUE_SEPARATOR}${modelName}`
}

export function decodeModelValue(value: string): { configId: string; modelName: string } {
  const index = value.lastIndexOf(MODEL_VALUE_SEPARATOR)
  if (index < 0) return { configId: value, modelName: '' }
  return { configId: value.slice(0, index), modelName: value.slice(index + MODEL_VALUE_SEPARATOR.length) }
}

interface Props {
  items: AiConfigItem[]
  /** 当前选中 "configId::modelName"；null 表示「继承上一层」 */
  value: string | null
  onChange: (selection: { configId: string; modelName: string } | null) => void
  disabled?: boolean
  /** null 选项的文案：全局视图=沿用平台默认，项目视图=沿用全局默认 */
  inheritLabel: string
  inheritHint?: string
  /** 上一层正在用的配置 id，用于打「当前继承」标记 */
  inheritedId?: string | null
}

const INHERIT = '__inherit__'

/**
 * 模型单选列表：按配置（系统预置 / 自定义模型）分组，组内一行一个模型。
 *
 * 一个 Key 勾选多个模型后，模型名才是真正的选择单位，所以 value 是
 * `configId::modelName`。选中的变化直接落库（全局默认 / 项目覆盖），不做本地态。
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
  const groups = useMemo(
    () =>
      items.map((item) => ({
        item,
        models: item.available_models?.length ? item.available_models : [item.model_name],
      })),
    [items],
  )

  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-[#E5E3DF] bg-[#FAFAF9] px-4 py-6 text-center text-[13px] text-[#A4A097]">
        还没有可用的模型，先在「自定义模型」里添加一个并勾选模型。
      </div>
    )
  }

  return (
    <Radio.Group
      value={value ?? INHERIT}
      disabled={disabled}
      onChange={(event) => {
        const next = event.target.value as string
        onChange(next === INHERIT ? null : decodeModelValue(next))
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

      {groups.map(({ item, models }) => (
        <div
          key={item.id}
          className="rounded-xl border border-[#E5E3DF] bg-white px-3.5 py-3 transition-colors hover:border-[#5645D4]/40"
        >
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[13px] font-semibold text-[#37352F]">{item.config_name}</span>
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
          </div>

          <div className="mt-2 flex flex-col gap-1.5">
            {models.map((model) => (
              <Radio key={`${item.id}-${model}`} value={encodeModelValue(item.id, model)}>
                <span className="text-[13px] text-[#37352F]">{model}</span>
              </Radio>
            ))}
          </div>

          <Typography.Text type="secondary" className="mt-1 block truncate text-[11px]">
            {item.visibility === 'personal' ? '你添加的配置，只有你能选' : '平台预置配置，开箱即用'}
          </Typography.Text>
        </div>
      ))}
    </Radio.Group>
  )
}