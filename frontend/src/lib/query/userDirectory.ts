import type { QueryClient } from '@tanstack/react-query'

/**
 * 「用户名单」类查询的 key 首段。
 *
 * 选人下拉散落在设备、安全、授权等多个模块，各自用了不同的 key：
 * - `['users', ...]`              用户管理表格
 * - `['all-users']`               设备工单/维修负责人
 * - `['identity-users-search', ...]` 设备/安全人员选择
 * - `['permission-user-options']` 授权管理选人
 *
 * 全局 `staleTime` 是 5 分钟且 `refetchOnWindowFocus: false`（见 Providers.tsx），
 * 所以新建 / 删除账号后必须显式失效这些查询，否则其他页面在不刷新浏览器的情况下
 * 会一直看到旧的名单（「刷新后才正常」的根因）。
 *
 * 注意：`['employees']`、`['hr-employees*']`、`['inspection-personnel']`、
 * `['equipment-personnel']` 不在此列 —— 它们读的是 hr.employees / equipment.personnel，
 * 与 identity.users 是两套数据，失效缓存也不会出现新账号。
 */
const USER_DIRECTORY_KEY_HEADS = new Set([
  'users',
  'all-users',
  'identity-users-search',
  'permission-user-options',
])

/** 失效所有「用户名单」查询：账号增删改后调用，让选人下拉立即看到最新名单。 */
export function invalidateUserDirectoryQueries(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({
    predicate: (query) => typeof query.queryKey[0] === 'string' && USER_DIRECTORY_KEY_HEADS.has(query.queryKey[0]),
  })
}
