/**
 * 模块配置页公共入口（Server 侧）。
 *
 * ⚠️ 本文件**只能**导出 Server Component：`ModuleSettingsPage` 经 `lib/permissions/server`
 * 读取 `next/headers`。一旦被 Client Component 引用，整个 barrel 会进入客户端模块图，
 * 构建直接失败（"You're importing a module that depends on next/headers"）。
 *
 * Client 侧（如 `AgentSettingsDrawer` 的嵌入式复用）请从 `@/components/module-settings/client`
 * 导入，那里只导出带 `'use client'` 的组件。
 */
export { default as ModuleSettingsPage } from './ModuleSettingsPage'
export { default as ModuleSettingsTabs } from './ModuleSettingsTabs'