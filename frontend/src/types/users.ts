import type { components } from '@/types/generated/schema'

/** 用户管理列表项（与后端 identity 模块 schema 一致）。 */
export type UserManagementItem = components['schemas']['UserManagementItem']

/** 用户管理列表数据：前端只消费 items/total，offset/limit 不落地到 UI。 */
export type UserManagementListResponse = Pick<
  components['schemas']['UserManagementListResponse'],
  'items' | 'total'
>

export type UserBatchStatusRequest = components['schemas']['UserBatchStatusRequest']

/** 批量结果：后端 schema 给 succeeded/failed 设了默认值，OpenAPI 标成可选；
 *  实际响应总会返回这两个数组，这里恢复成必填，避免消费端冗余判空。 */
export type UserBatchStatusResult = {
  succeeded: NonNullable<components['schemas']['UserBatchStatusData']['succeeded']>
  failed: NonNullable<components['schemas']['UserBatchStatusData']['failed']>
}

export type FeishuBindRequest = components['schemas']['FeishuBindRequest']
export type LocalUserCreate = components['schemas']['LocalUserCreate']
export type UserCreateResult = components['schemas']['UserCreateData']
export type UserManagementUpdate = components['schemas']['UserManagementUpdate']
export type PasswordResetRequest = components['schemas']['PasswordResetRequest']
export type PasswordResetResult = components['schemas']['PasswordResetData']
export type UserDeleteResult = components['schemas']['UserDeleteData']
export type ChangePasswordRequest = components['schemas']['ChangePasswordRequest']

/** 解绑飞书响应（比列表项多一个 account_deleted 标记）。 */
export type UserUnbindResult = components['schemas']['UserUnbindFeishuData']

/** 在线会话（来自 GET /identity/sessions，Redis 会话索引）。 */
export type UserSession = components['schemas']['SessionItem']
