import { PERMISSION_DENIED_TITLE } from '@/lib/permissions/codes'

/**
 * 后端返回 403（权限不足）时抛出的语义化错误。
 *
 * 目的：不要把「请求失败: 403 Forbidden」这类技术文案直接抛给用户，
 * 统一转成「当前用户权限不足」，由调用方 catch 后用 message.warning 提示。
 */
export class PermissionDeniedError extends Error {
  readonly status = 403

  constructor(message: string = PERMISSION_DENIED_TITLE) {
    super(message)
    this.name = 'PermissionDeniedError'
  }
}

export function isPermissionDeniedError(error: unknown): error is PermissionDeniedError {
  return error instanceof PermissionDeniedError || (error as { status?: number })?.status === 403
}
