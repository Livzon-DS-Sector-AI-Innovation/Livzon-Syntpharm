/**
 * 批量操作结果的边界归一。
 *
 * 后端 `BatchResultData` / `UserBatchStatusData` 的 succeeded/failed 有默认值，
 * OpenAPI 因此标成可选；实际响应总会带上这两个数组。在 API 边界统一补齐，
 * 上层就能按必填数组直接消费，不必到处 `?.` 判空。
 */
import type { components } from '@/types/generated/schema'
import type { BatchResult } from '@/types/batch'
import type { UserBatchStatusResult } from '@/types/users'

export function normalizeBatchResult(
  data: components['schemas']['BatchResultData'] | null | undefined,
): BatchResult {
  return { succeeded: data?.succeeded ?? [], failed: data?.failed ?? [] }
}

export function normalizeUserBatchStatus(
  data: components['schemas']['UserBatchStatusData'] | null | undefined,
): UserBatchStatusResult {
  return { succeeded: data?.succeeded ?? [], failed: data?.failed ?? [] }
}
