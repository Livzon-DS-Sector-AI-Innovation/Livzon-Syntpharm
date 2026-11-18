/** 工作台卡片用到的模块落点（待办与流程共用，避免两处各写一份）。 */

/** 模块首页：待办来自模块内多个列表，没有统一待办页，只给模块入口 */
export const MODULE_HOME_PATH: Record<string, string> = {
  quality: '/quality',
  safety: '/safety',
}

/** 流程列表页：目前流程只来自偏差台账与隐患台账 */
export const MODULE_PROCESS_PATH: Record<string, { label: string; path: string }> = {
  quality: { label: '偏差台账', path: '/quality/deviation/ledger' },
  safety: { label: '隐患台账', path: '/safety/hazard' },
}