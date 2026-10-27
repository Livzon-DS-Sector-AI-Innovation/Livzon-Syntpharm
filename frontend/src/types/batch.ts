/**
 * 批量操作结果（权限 / 用户 / 系统运维共用一份定义）。
 *
 * 后端 `BatchResultData` 给 succeeded/failed 设了默认值，OpenAPI 因此标成可选；
 * 实际响应总会返回这两个数组，这里恢复成必填，避免消费端冗余判空。
 */
import type { components } from '@/types/generated/schema'

export type BatchFailureItem = components['schemas']['BatchFailure']

export type BatchResult = {
  succeeded: NonNullable<components['schemas']['BatchResultData']['succeeded']>
  failed: NonNullable<components['schemas']['BatchResultData']['failed']>
}
