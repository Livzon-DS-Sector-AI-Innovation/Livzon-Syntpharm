import { apiGet } from '@/lib/api/client'
import type { components } from '@/types/generated/schema'

/**
 * 客户端工作台待办查询（顶栏铃铛用）。
 *
 * 与 `lib/api/server/workbench.ts` 的区别：那份是 Server Component 首屏用，
 * 走 `API_BASE_URL` 服务端直连；这里走浏览器 `/api/v1` 代理，供顶栏按需刷新。
 */

export type WorkbenchTodoSection = components['schemas']['TodoSectionModel']
export type WorkbenchTodoItem = components['schemas']['WorkbenchItemModel']

export interface WorkbenchTodoSnapshot {
  todos: WorkbenchTodoSection
  /** 取数失败被后端降级的数据源标识（如 deviation / iqc） */
  degradedSources: string[]
}

const DEFAULT_TODO_LIMIT = 5

/** 后端默认每数据源 5 条、允许 1-20；弹层与首页卡片保持同一口径 */
function emptySection(): WorkbenchTodoSection {
  return { total: 0, unread_total: 0, has_more: false, person_total: 0, role_total: 0, groups: [] }
}

/**
 * 拉取待办摘要。
 *
 * `process_limit` 传最小值 1：铃铛只用 `todos`，避免把「我参与的流程」也全量取回。
 * 注意 `todos.total` / `unread_total` 都是按各数据源 limit 取回后的条数，不是全库总数；
 * 调用方需结合 `todos.has_more` 用「N+」呈现。
 */
export async function fetchWorkbenchTodos(todoLimit = DEFAULT_TODO_LIMIT): Promise<WorkbenchTodoSnapshot> {
  const query = new URLSearchParams({
    todo_limit: String(todoLimit),
    process_limit: '1',
  })
  const data = await apiGet<components['schemas']['WorkbenchOverviewData']>(
    `/api/v1/workbench/overview?${query.toString()}`,
  )
  return {
    todos: data?.todos ?? emptySection(),
    degradedSources: data?.degraded_sources ?? [],
  }
}

/** 扁平化后的待办条目（保留所属模块，便于分组展示） */
export interface FlatTodoItem extends WorkbenchTodoItem {
  groupModuleKey: string
  groupModuleLabel: string
}

export function flattenTodoItems(todos: WorkbenchTodoSection): FlatTodoItem[] {
  return (todos.groups ?? []).flatMap((group) =>
    (group.items ?? []).map((item) => ({
      ...item,
      groupModuleKey: group.module_key,
      groupModuleLabel: group.module_label,
    })),
  )
}