'use client'

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Empty, Input, Select, Skeleton, Switch, Tag, Tooltip } from 'antd'
import {
  DownloadOutlined,
  ReloadOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { batchUpdateModuleSettings, getModuleSettings } from '@/actions/module-settings'
import type { ModuleSetting } from '@/types/module-settings'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'
import { BatchResultModal, SettingsListCard, SettingsPageHeader, type BatchResult } from '@/components/settings'
import BatchToggleModal from './BatchToggleModal'
import RuntimeSettingGroups from './RuntimeSettingGroups'
import {
  DEFAULT_QUERY,
  boolSettings,
  buildBatchPayload,
  buildExportPayload,
  buildGroupedSettings,
  collectGroups,
  isManuallyAdjusted,
  type SettingQuery,
} from './runtimeSettingsMeta'

interface ModuleSettingsClientProps {
  moduleCode: string
  moduleName: string
  moduleDescription: string
  /**
   * 作为「模块配置」页签内容嵌入时传 true：
   * 外层页面已有页头与容器留白，这里不再重复渲染。
   */
  embedded?: boolean
}

const TYPE_OPTIONS = [
  { value: 'all', label: '全部类型' },
  { value: 'bool', label: '开关' },
  { value: 'int', label: '数字' },
  { value: 'string', label: '文本' },
  { value: 'json', label: 'JSON' },
]

const SORT_OPTIONS = [
  { value: 'name', label: '按名称排序' },
  { value: 'updated', label: '按最近修改排序' },
]

/**
 * 模块运行时配置清单。
 *
 * 结构：工具行（检索 / 筛选 / 排序 / 导出 / 批量）→ 按功能域分组 → 行内就地编辑。
 * 12 个业务模块共用本组件，模块差异全部由后端 ``core.module_settings`` 的数据驱动。
 */
export default function ModuleSettingsClient({
  moduleCode,
  moduleName,
  moduleDescription,
  embedded = false,
}: ModuleSettingsClientProps) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()

  // hook 必须写在任何 early return 之前
  const { can, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.configManage)

  const [query, setQuery] = useState<SettingQuery>(DEFAULT_QUERY)
  const [batchOpen, setBatchOpen] = useState(false)
  const [batchLoading, setBatchLoading] = useState(false)
  const [result, setResult] = useState<BatchResult | null>(null)

  const { data: settings = [], isLoading } = useQuery({
    queryKey: ['module-settings', moduleCode],
    queryFn: async () => {
      const res = await getModuleSettings(moduleCode)
      return res || []
    },
  })

  const groups = useMemo(() => buildGroupedSettings(settings, query), [settings, query])
  const groupOptions = useMemo(
    () => [{ value: 'all', label: '全部分组' }, ...collectGroups(settings).map((name) => ({ value: name, label: name }))],
    [settings],
  )
  const visibleCount = groups.reduce((total, group) => total + group.items.length, 0)
  const adjustedCount = settings.filter(isManuallyAdjusted).length
  const switches = boolSettings(settings)
  const filtering =
    query.keyword.trim() !== '' ||
    query.valueType !== 'all' ||
    query.group !== 'all' ||
    query.onlyAdjusted

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['module-settings', moduleCode] })

  const runBatch = async (targets: ModuleSetting[], value: 'true' | 'false') => {
    if (targets.length === 0) return
    setBatchLoading(true)
    try {
      const data = await batchUpdateModuleSettings(buildBatchPayload(targets, value))
      setResult({
        succeeded: data.succeeded,
        failed: data.failed.map((item) => ({
          key: item.key,
          label: item.label ?? item.key,
          reason: item.reason,
        })),
      })
      await refresh()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '批量保存失败')
    } finally {
      setBatchLoading(false)
    }
  }

  const exportJson = () => {
    const blob = new Blob([buildExportPayload(settings)], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${moduleCode}-settings.json`
    link.click()
    URL.revokeObjectURL(url)
    message.success('已导出当前模块配置（密钥类不含明文）')
  }

  return (
    <div className={embedded ? '' : 'settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6'}>
      {embedded ? null : <SettingsPageHeader title={`${moduleName}配置`} description={moduleDescription} />}

      <SettingsListCard
        title="运行时配置"
        className="settings-region-card"
        extra={
          <span className="text-[12px] text-[var(--color-steel)]">
            共 {settings.length} 项
            {filtering ? ` · 筛选出 ${visibleCount} 项` : ''}
            {adjustedCount > 0 ? ` · ${adjustedCount} 项已调整` : ''}
          </span>
        }
        toolbar={
          <div className="flex w-full flex-wrap items-center gap-2">
            <Input
              allowClear
              prefix={<SearchOutlined className="text-[var(--color-stone)]" />}
              placeholder="搜索配置名称、键名或说明"
              value={query.keyword}
              onChange={(event) => setQuery((prev) => ({ ...prev, keyword: event.target.value }))}
              style={{ width: 260 }}
            />
            <Select
              value={query.valueType}
              options={TYPE_OPTIONS}
              onChange={(value) => setQuery((prev) => ({ ...prev, valueType: value }))}
              style={{ width: 130 }}
            />
            <Select
              value={query.group}
              options={groupOptions}
              onChange={(value) => setQuery((prev) => ({ ...prev, group: value }))}
              style={{ width: 150 }}
            />
            <Select
              value={query.sortBy}
              options={SORT_OPTIONS}
              onChange={(value) => setQuery((prev) => ({ ...prev, sortBy: value }))}
              style={{ width: 160 }}
            />
            <Tooltip title="只看被人工修改过的配置项">
              <span className="flex items-center gap-2 text-[12px] text-[var(--color-steel)]">
                <Switch
                  size="small"
                  checked={query.onlyAdjusted}
                  onChange={(checked) => setQuery((prev) => ({ ...prev, onlyAdjusted: checked }))}
                />
                只看已调整
              </span>
            </Tooltip>
            <div className="ml-auto flex items-center gap-2">
              <Tooltip title="重新拉取最新配置">
                <Button icon={<ReloadOutlined />} onClick={() => void refresh()} />
              </Tooltip>
              <Tooltip title="导出为 JSON（密钥类不含明文）">
                <Button icon={<DownloadOutlined />} onClick={exportJson} disabled={settings.length === 0}>
                  导出
                </Button>
              </Tooltip>
              {canManage && (
                <Button
                  icon={<ThunderboltOutlined />}
                  disabled={switches.length === 0}
                  onClick={() => setBatchOpen(true)}
                >
                  批量启停
                </Button>
              )}
            </div>
          </div>
        }
      >
        {isLoading ? (
          <Skeleton active paragraph={{ rows: 6 }} className="py-4" />
        ) : settings.length === 0 ? (
          <Empty
            className="py-10"
            description={
              <div className="text-[13px] text-[var(--color-steel)]">
                <div className="text-[var(--color-charcoal)]">本模块还没有可调参数</div>
                <div className="mt-1">
                  新增配置项请联系系统管理员在「系统配置」中登记；登记后会自动出现在这里。
                </div>
              </div>
            }
          />
        ) : visibleCount === 0 ? (
          <Empty
            className="py-10"
            description={
              <div className="text-[13px] text-[var(--color-steel)]">
                <div className="text-[var(--color-charcoal)]">没有符合条件的配置项</div>
                <div className="mt-1">试试换一个关键词，或清空筛选条件。</div>
              </div>
            }
          >
            <Button onClick={() => setQuery(DEFAULT_QUERY)}>清空筛选</Button>
          </Empty>
        ) : (
          <RuntimeSettingGroups
            groups={groups}
            canManage={canManage}
            batchLoading={batchLoading}
            onSaved={() => void refresh()}
            onGroupBatch={(targets, value) => void runBatch(targets, value)}
          />
        )}
      </SettingsListCard>

      <div className="mt-4 flex items-center gap-2 text-[12px] text-[var(--color-steel)]">
        <Tag className="!mr-0">提示</Tag>
        开关类配置保存后立即生效；密钥类配置只显示掩码，修改时填写新值即可整体替换。
      </div>

      {batchOpen && (
        <BatchToggleModal
          settings={switches}
          onClose={() => setBatchOpen(false)}
          onSaved={() => void refresh()}
        />
      )}

      <BatchResultModal result={result} onClose={() => setResult(null)} />
    </div>
  )
}