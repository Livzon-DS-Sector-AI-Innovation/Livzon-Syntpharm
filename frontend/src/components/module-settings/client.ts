/**
 * 模块配置页的 Client 入口。
 *
 * 与 `./index.ts` 分开的原因：`index.ts` 导出 async Server Component（依赖 `next/headers`），
 * Client Component 引用它会构建失败。这里只导出自身带 `'use client'` 的组件，
 * 供抽屉/弹窗这类客户端场景嵌入式复用。
 */
export { default as ModuleSettingsClient } from './ModuleSettingsClient'