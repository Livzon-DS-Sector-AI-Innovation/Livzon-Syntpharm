import type { components } from '@/types/generated/schema'

// 运行时配置的契约类型一律从 OpenAPI 生成类型派生（AGENTS.md：禁止手写 API 类型）。
// UI 侧的派生视图（分组、筛选状态）另见 components/module-settings/runtimeSettingsMeta.ts。
export type ModuleSetting = components['schemas']['ModuleSettingResponse']
export type ModuleSettingCreate = components['schemas']['ModuleSettingCreate']
export type ModuleSettingUpdate = components['schemas']['ModuleSettingUpdate']
export type ModuleSettingBatchItem = components['schemas']['ModuleSettingBatchItem']
export type ModuleSettingBatchUpdate = components['schemas']['ModuleSettingBatchUpdate']
export type ModuleSettingBatchResult = components['schemas']['ModuleSettingBatchResult']