import type { ApiResponse } from '@/types/common'

/** 列表接口统一后的结果：页面只关心「有哪些行、总数多少」。 */
export interface PageResult<T> {
  items: T[]
  total: number
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function toTotal(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

/**
 * 把列表接口响应统一成 {@link PageResult}。
 *
 * 后端历史原因存在两种形态：
 *   1. 标准信封 `{ code, message, data: { items, total } }`
 *   2. 裸分页对象 `{ items, total }`
 *
 * 差异集中在这里消化，页面不再各自手写 `as { code?: number; ... }` 这类契约断言。
 * 无法识别的形态直接抛错，交给 React Query 的 isError 走降级态，而不是静默显示空表。
 */
export function toPageResult<T>(payload: unknown): PageResult<T> {
  if (isRecord(payload)) {
    if (Array.isArray(payload.items)) {
      return { items: payload.items as T[], total: toTotal(payload.total) }
    }
    const data = payload.data
    if (isRecord(data) && Array.isArray(data.items)) {
      return { items: data.items as T[], total: toTotal(data.total) }
    }
    if (Array.isArray(data)) {
      return { items: data as T[], total: toTotal(payload.total ?? payload.count) }
    }
  }
  throw new Error('列表响应格式不符合预期')
}

/**
 * 客户端 fetch 路径使用：响应已经是 `{ data, meta }` 信封，分页数字在 meta 里。
 */
export function fromApiResponsePage<T>(response: ApiResponse<T[]> | undefined): PageResult<T> {
  return { items: response?.data ?? [], total: toTotal(response?.meta?.total) }
}