'use client'

import { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { useSearchParams } from 'next/navigation'
import { Skeleton, Tabs } from 'antd'
import ModulePermissionPanel from './ModulePermissionPanel'
import ModuleSettingsClient from '@/components/settings/ModuleSettingsClient'
import type { ModuleSettingsCustomComponent, ModuleSettingsDefinition } from './settings-registry'

/**
 * 迁移进来的既有设置页（仪器 / 试剂提醒各约 400 行）按页签懒加载：
 * 12 个模块的配置页共用同一个容器，若静态 import 会把 4 个 legacy 页面
 * 全部塞进每个模块的首包，仓储/采购这类只有权限页签的模块也被迫下载。
 */
const TAB_FALLBACK = () => (
  <div className="py-8">
    <Skeleton active paragraph={{ rows: 6 }} />
  </div>
)

const CUSTOM_COMPONENTS: Record<ModuleSettingsCustomComponent, React.ComponentType<{ embedded?: boolean }>> = {
  'quality-instrument': dynamic(() => import('./legacy/QualityInstrumentSettings'), { loading: TAB_FALLBACK }),
  'quality-stability': dynamic(() => import('./legacy/QualityStabilitySettings'), { loading: TAB_FALLBACK }),
  'quality-reagent': dynamic(() => import('./legacy/QualityReagentReminder'), { loading: TAB_FALLBACK }),
  'hr-system': dynamic(() => import('./legacy/HrSystemSettings'), { loading: TAB_FALLBACK }),
}

/**
 * 切换页签时同步地址栏：刷新、分享、书签都能停在同一页签。
 *
 * 用原生 History API 而不是 `router.replace`：后者会让 `force-dynamic` 的
 * 模块配置页再跑一次服务端取数，切个页签就多一次 RSC 往返。
 */
function syncTabToUrl(key: string) {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  url.searchParams.set('tab', key)
  window.history.replaceState(null, '', url)
}

interface ModuleSettingsTabsProps {
  definition: ModuleSettingsDefinition
  canManage: boolean
  currentUserId: string
  isSystemAdmin: boolean
}

/** 模块配置页的页签容器：首屏固定「权限管理」，其余页签由注册表声明。 */
export default function ModuleSettingsTabs({
  definition,
  canManage,
  currentUserId,
  isSystemAdmin,
}: ModuleSettingsTabsProps) {
  const searchParams = useSearchParams()
  const requested = searchParams.get('tab')

  const items = useMemo(
    () =>
      definition.tabs.map((tab) => {
        let children: React.ReactNode
        if (tab.kind === 'permission') {
          children = (
            <ModulePermissionPanel
              moduleCode={definition.moduleCode}
              moduleLabel={definition.moduleLabel}
              canManage={canManage}
              currentUserId={currentUserId}
              isSystemAdmin={isSystemAdmin}
            />
          )
        } else if (tab.kind === 'runtime') {
          children = (
            <ModuleSettingsClient
              moduleCode={definition.moduleCode}
              moduleName={definition.moduleLabel}
              moduleDescription={`${definition.moduleLabel}的运行时配置（模型、开关、阈值等）。密钥类信息请在系统配置中管理。`}
              embedded
            />
          )
        } else {
          const Component = tab.component ? CUSTOM_COMPONENTS[tab.component] : null
          // embedded：迁移来的旧设置页自带页头，嵌入页签后隐藏，避免与「模块配置 · X」重复
          children = Component ? <Component embedded /> : null
        }
        return {
          key: tab.key,
          label: tab.label,
          children,
        }
      }),
    [definition, canManage, currentUserId, isSystemAdmin],
  )

  // 非法 / 缺失的 ?tab= 一律回落到第一个页签（权限管理），避免空白页签
  const initialKey = items.some((item) => item.key === requested) ? (requested as string) : items[0]?.key

  return <Tabs defaultActiveKey={initialKey} items={items} destroyOnHidden onChange={syncTabToUrl} />
}
