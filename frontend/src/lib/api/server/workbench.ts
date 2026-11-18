import { apiFetchData } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

export type WorkbenchOverview = components['schemas']['WorkbenchOverviewData']
export type WorkbenchItem = components['schemas']['WorkbenchItemModel']
export type WorkbenchTodoSection = components['schemas']['TodoSectionModel']
export type WorkbenchProcessSection = components['schemas']['ProcessSectionModel']

/** 单数据源条数上限的默认值（后端默认 5，允许 1-20） */
const DEFAULT_SOURCE_LIMIT = 5

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
    return await apiFetchData<WorkbenchOverview>(`/api/v1/workbench/overview?${query.toString()}`)
  } catch (error) {
    console.error('工作台数据获取失败:', error)
    return null
  }
}