'use client'

import { App, Collapse, Space, Tag, Tooltip } from 'antd'
import type { ModuleSetting } from '@/types/module-settings'
import SettingValueEditor from './SettingValueEditor'
import {
  boolSettings,
  isManuallyAdjusted,
  settingTitle,
  valueTypeColor,
  valueTypeLabel,
  type SettingGroupView,
} from './runtimeSettingsMeta'

interface RuntimeSettingGroupsProps {
  groups: SettingGroupView[]
  canManage: boolean
  batchLoading: boolean
  onSaved: () => void
  onGroupBatch: (items: ModuleSetting[], value: 'true' | 'false') => void
}

/**
 * 按功能域折叠展示配置项。
 *
 * 组头承担三件事：组名 + 条数、该组布尔项的一键启停、折叠状态。
 * 分组本身由后端 ``group_name`` 驱动，未回填的存量项归入「其他」。
 */
export default function RuntimeSettingGroups({
  groups,
  canManage,
  batchLoading,
  onSaved,
  onGroupBatch,
}: RuntimeSettingGroupsProps) {
  const { message } = App.useApp()

  const items = groups.map((group) => {
    const switches = boolSettings(group.items)
    const adjusted = group.items.filter(isManuallyAdjusted).length
    return {
      key: group.name,
      label: (
        <Space size={8} wrap>
          <span className="text-[14px] font-semibold text-[var(--color-primary-deep)]">{group.name}</span>
          <Tag className="!mr-0">{group.items.length} 项</Tag>
          {adjusted > 0 && (
            <Tooltip title="本组有配置项被人工修改过">
              <Tag color="gold" className="!mr-0">
                {adjusted} 项已调整
              </Tag>
            </Tooltip>
          )}
        </Space>
      ),
      children: (
        <div className="flex flex-col">
          {/* 组操作放在区域标题栏下方，不进标题栏 */}
          {canManage && switches.length > 0 && (
            <div className="mb-2 flex items-center justify-end gap-2">
              <button
                type="button"
                className="cursor-pointer border-0 bg-transparent px-1 text-[12px] text-[var(--color-primary)] hover:underline disabled:cursor-not-allowed disabled:text-[var(--color-muted)]"
                disabled={batchLoading}
                onClick={() => onGroupBatch(switches, 'true')}
              >
                全部启用
              </button>
              <span className="text-[var(--color-hairline-strong)]">|</span>
              <button
                type="button"
                className="cursor-pointer border-0 bg-transparent px-1 text-[12px] text-[var(--color-primary)] hover:underline disabled:cursor-not-allowed disabled:text-[var(--color-muted)]"
                disabled={batchLoading}
                onClick={() => onGroupBatch(switches, 'false')}
              >
                全部停用
              </button>
            </div>
          )}
          {group.items.map((setting) => (
            <div
              key={setting.id}
              className="flex flex-col gap-2 border-b border-[var(--color-hairline-soft)] px-1 py-3 last:border-b-0 md:flex-row md:items-center md:justify-between md:gap-6"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-[var(--color-charcoal)]">{settingTitle(setting)}</span>
                  <Tag color={valueTypeColor(setting.value_type)} className="!mr-0">
                    {valueTypeLabel(setting.value_type)}
                  </Tag>
                  {isManuallyAdjusted(setting) && (
                    <Tag color="gold" className="!mr-0">
                      已调整
                    </Tag>
                  )}
                  {setting.is_secret && <Tag className="!mr-0">密钥</Tag>}
                </div>
                <Tooltip title="点击可复制键名">
                  <button
                    type="button"
                    className="mt-0.5 block max-w-full cursor-copy truncate border-0 bg-transparent p-0 text-left font-mono text-[12px] text-[var(--color-steel)] hover:text-[var(--color-primary)]"
                    onClick={() => {
                      void navigator.clipboard
                        ?.writeText(setting.key)
                        .then(() => message.success('键名已复制'))
                        .catch(() => message.warning('复制失败，请手动选择'))
                    }}
                  >
                    {setting.key}
                  </button>
                </Tooltip>
                {setting.description && (
                  <div className="mt-0.5 line-clamp-2 text-[12px] text-[var(--color-steel)]">
                    {setting.description}
                  </div>
                )}
              </div>
              <div className="shrink-0 md:max-w-[46%]">
                <SettingValueEditor setting={setting} canManage={canManage} onSaved={onSaved} />
              </div>
            </div>
          ))}
        </div>
      ),
    }
  })

  // 分组多时只默认展开第一组，避免一次铺满整屏；少分组（≤4）全展开。
  // 用分组集合做 key：筛选导致分组变化时重新挂载，保证新出现的分组是展开的
  // （Collapse 非受控，defaultActiveKey 只在挂载时生效）。
  const defaultActiveKey =
    groups.length <= 4 ? groups.map((group) => group.name) : groups.slice(0, 1).map((g) => g.name)

  return (
    <Collapse
      key={groups.map((group) => group.name).join('|')}
      size="small"
      items={items}
      defaultActiveKey={defaultActiveKey}
      className="settings-region-collapse"
    />
  )
}