/**
 * 注册模块的外部系统地址配置。
 *
 * 仅限服务端组件 / 服务端代码导入：这里读取的是服务端运行时环境变量，
 * 客户端组件导入拿不到值（Next 只会为 `NEXT_PUBLIC_` 前缀的变量做构建期内联）。
 *
 * 约定：
 * - 源码不提供任何默认地址（禁止硬编码固定地址），地址只来自部署环境的 `.env`；
 * - 未配置时返回空值，调用方据此回退系统内的旧页面，保证零配置环境行为不变。
 */

/** 侧边栏「申报资料撰写」的菜单 key，与 lib/menu-config.ts 保持一致 */
export const DOSSIER_WRITER_MENU_KEY = 'dossier-writer'

/** 外部撰写系统地址；未配置或配置为空串时返回 '' */
export function getDossierWriterUrl(): string {
  return (process.env.DOSSIER_WRITER_URL ?? '').trim()
}

/**
 * 菜单 key → 外部地址的映射，供 Sidebar 判断点击时是 `window.open` 还是 `router.push`。
 * 未配置时返回空对象，菜单保持原有本地路由行为。
 */
export function getExternalMenuLinks(): Record<string, string> {
  const url = getDossierWriterUrl()
  return url ? { [DOSSIER_WRITER_MENU_KEY]: url } : {}
}
