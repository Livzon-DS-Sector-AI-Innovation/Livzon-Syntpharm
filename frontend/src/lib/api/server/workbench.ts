import { apiFetchData, getApiBaseUrl } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'
import type { TodoReadMark, TodoReadResult } from '@/types/workbench'

export type WorkbenchOverview = components['schemas']['WorkbenchOverviewData']
export type WorkbenchItem = components['schemas']['WorkbenchItemModel']
export type WorkbenchTodoSection = components['schemas']['TodoSectionModel']
export type WorkbenchProcessSection = components['schemas']['ProcessSectionModel']

/** 单数据源条数上限的默认值（后端默认 5，允许 1-20） */
const DEFAULT_SOURCE_LIMIT = 5

/** 后端 API 前缀：服务端调用必须拼 `API_BASE_URL`，不依赖 apiFetch 的相对路径兜底。 */
function workbenchUrl(path: string): string {
  return `${getApiBaseUrl()}/api/v1/workbench${path}`
}

/**
 * 首页工作台数据（审核待办 + 我参与的流程）。
 *
 * 首页是 force-dynamic 首屏，聚合接口失败不应让整页白屏：
 * 这里吞掉异常并返回 null，由页面降级为「数据暂时不可用」。
 */
export async function fetchWorkbenchOverview(
  todoLimit: number = DEFAULT_SOURCE_LIMIT,
  processLimit: number = DEFAULT_SOURCE_LIMIT,
): Promise<WorkbenchOverview | null> {
  const query = new URLSearchParams({
    todo_limit: String(todoLimit),
    process_limit: String(processLimit),
  })
  try {
    return await apiFetchData<WorkbenchOverview>(`${workbenchUrl('/overview')}?${query.toString()}`)
  } catch (error) {
    console.error('工作台数据获取失败:', error)
    return null
  }
}

/** 标记单条待办已读（幂等；只影响当前用户自己的未读计数）。 */
export async function markTodoRead(mark: TodoReadMark): Promise<TodoReadResult> {
  return apiFetchData<TodoReadResult>(workbenchUrl('/todos/read'), {
    method: 'POST',
    body: JSON.stringify(mark),
  })
}

/** 一键已读：批量写入客户端当前看到的未读项（空列表直接返回 0）。 */
export async function markAllTodosRead(
  body: components['schemas']['TodoReadBatchRequest'],
): Promise<TodoReadResult> {
  const items = body.items ?? []
  if (items.length === 0) return { marked: 0 }
  return apiFetchData<TodoReadResult>(workbenchUrl('/todos/read-all'), {
    method: 'POST',
    body: JSON.stringify({ items } satisfies components['schemas']['TodoReadBatchRequest']),
  })
}