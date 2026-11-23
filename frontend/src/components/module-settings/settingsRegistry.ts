/**
 * 模块配置页的**声明式页签注册表**（唯一权威）。
 *
 * 每个业务模块统一一个 `/{module}/settings` 页面，该模块的所有配置都归到这里：
 * - 第一个页签固定「权限管理」（角色 + 授权，按模块过滤）；
 * - 其余页签按模块**实际有没有配置项**声明，没有就不声明（避免出现空页签）；
 * - 后续新增配置项只需在这里加一条记录，不需要新建页面。
 *
 * `kind` 的取值决定渲染什么：
 * - `permission` → `ModulePermissionPanel`（岗位角色与授权）
 * - `runtime`    → 现有的 `ModuleSettingsClient`（模块运行时配置）
 * - `custom`     → 迁移进来的既有设置页组件（见 `ModuleSettingsPage` 的映射表）
 */

export type ModuleSettingsTabKind = 'permission' | 'runtime' | 'custom'

/** `custom` 页签约定的组件键，与 `ModuleSettingsPage` 内的映射表一一对应 */
export type ModuleSettingsCustomComponent =
  | 'quality-instrument'
  | 'quality-stability'
  | 'quality-reagent'
  | 'quality-department-contacts'
  | 'equipment-personnel'
  | 'hr-system'

export interface ModuleSettingsTab {
  key: string
  label: string
  kind: ModuleSettingsTabKind
  /** 迁移自哪个旧页面（展示「迁移自 xxx」标注，并用它做旧地址重定向目标） */
  legacyPath?: string
  /** kind=custom 时必填 */
  component?: ModuleSettingsCustomComponent
}

export interface ModuleSettingsDefinition {
  moduleCode: string
  moduleLabel: string
  /** 模块配置页顶部说明 */
  description: string
  tabs: ModuleSettingsTab[]
}

export const PERMISSION_TAB: ModuleSettingsTab = { key: 'perm', label: '权限管理', kind: 'permission' }

const RUNTIME = (label = '运行配置'): ModuleSettingsTab => ({ key: 'runtime', label, kind: 'runtime' })

export const MODULE_SETTINGS: Record<string, ModuleSettingsDefinition> = {
  quality: {
    moduleCode: 'quality',
    moduleLabel: '质量管理',
    description: '本模块的岗位角色与授权，以及仪器提醒、稳定性提醒、试剂库存提醒等配置。',
    tabs: [
      PERMISSION_TAB,
      {
        key: 'department-contacts',
        label: '部门联系人配置',
        kind: 'custom',
        component: 'quality-department-contacts',
        legacyPath: '/quality/department-contacts',
      },
      {
        key: 'instrument',
        label: '仪器提醒',
        kind: 'custom',
        component: 'quality-instrument',
        legacyPath: '/quality/instrument/settings',
      },
      {
        key: 'stability',
        label: '稳定性提醒',
        kind: 'custom',
        component: 'quality-stability',
        legacyPath: '/quality/stability/settings',
      },
      {
        key: 'reagent',
        label: '试剂库存提醒',
        kind: 'custom',
        component: 'quality-reagent',
        legacyPath: '/quality/reagent/reminder',
      },
      RUNTIME(),
    ],
  },
  production: {
    moduleCode: 'production',
    moduleLabel: '生产管理',
    description: '本模块的岗位角色与授权，以及生产相关的运行时参数。',
    tabs: [PERMISSION_TAB, RUNTIME()],
  },
  safety: {
    moduleCode: 'safety',
    moduleLabel: '安全管理',
    description: '本模块的岗位角色与授权，以及 AI 模型、飞书集成等运行时参数。',
    tabs: [PERMISSION_TAB, { ...RUNTIME(), legacyPath: '/safety/settings' }],
  },
  equipment: {
    moduleCode: 'equipment',
    moduleLabel: '设备管理',
    description: '本模块的岗位角色与授权，以及飞书同步、维护计划生成等功能开关。',
    tabs: [
      PERMISSION_TAB,
      {
        key: 'personnel',
        label: '人员配置',
        kind: 'custom',
        component: 'equipment-personnel',
        legacyPath: '/equipment/personnel',
      },
      { ...RUNTIME(), legacyPath: '/equipment/settings' },
    ],
  },
  hr: {
    moduleCode: 'hr',
    moduleLabel: '人事管理',
    description: '本模块的岗位角色与授权，以及飞书 Bot、AI 模型与运行时配置。',
    tabs: [
      PERMISSION_TAB,
      {
        key: 'feishu',
        label: '飞书 Bot 配置',
        kind: 'custom',
        component: 'hr-system',
        legacyPath: '/hr/system/settings',
      },
      { ...RUNTIME(), legacyPath: '/hr/settings' },
    ],
  },
  energy: {
    moduleCode: 'energy',
    moduleLabel: '能源管理',
    description: '本模块的岗位角色与授权，以及能源自动采集等功能开关。',
    tabs: [PERMISSION_TAB, { ...RUNTIME(), legacyPath: '/energy/settings' }],
  },
  warehouse: {
    moduleCode: 'warehouse',
    moduleLabel: '仓储管理',
    description: '本模块的岗位角色与授权。',
    tabs: [PERMISSION_TAB],
  },
  procurement: {
    moduleCode: 'procurement',
    moduleLabel: '采购管理',
    description: '本模块的岗位角色与授权。',
    tabs: [PERMISSION_TAB],
  },
  registration: {
    moduleCode: 'registration',
    moduleLabel: '注册管理',
    description: '本模块的岗位角色与授权。',
    tabs: [PERMISSION_TAB],
  },
  research: {
    moduleCode: 'research',
    moduleLabel: '研发管理',
    description: '本模块的岗位角色与授权。',
    tabs: [PERMISSION_TAB],
  },
  administration: {
    moduleCode: 'administration',
    moduleLabel: '行政管理',
    description: '本模块的岗位角色与授权。',
    tabs: [PERMISSION_TAB],
  },
  environment: {
    moduleCode: 'environment',
    moduleLabel: '环保管理',
    description: '本模块的岗位角色与授权。',
    tabs: [PERMISSION_TAB],
  },
}

export function getModuleSettings(moduleCode: string): ModuleSettingsDefinition | undefined {
  return MODULE_SETTINGS[moduleCode]
}

/** 旧设置页 → 新页签的映射（旧地址重定向用） */
export const LEGACY_SETTINGS_REDIRECTS: Record<string, string> = Object.values(MODULE_SETTINGS).reduce(
  (acc, def) => {
    for (const tab of def.tabs) {
      if (tab.legacyPath) acc[tab.legacyPath] = `/${def.moduleCode}/settings?tab=${tab.key}`
    }
    return acc
  },
  {} as Record<string, string>,
)
