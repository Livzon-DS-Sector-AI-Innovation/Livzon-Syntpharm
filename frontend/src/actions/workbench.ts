'use server'

import { apiFetch } from '@/lib/api/server/base'
import { getAuthHeaders } from '@/lib/auth'
import type { components } from '@/types/generated/schema'

/** 已读标记：source + item_id + 内容指纹（指纹来自 /workbench/overview） */
export type TodoReadMark = components['schemas']['TodoReadMark']

export interface TodoReadResult {
  /** 本次写入（含更新）的已读记录数 */
  marked: number
}

interface TodoReadResultEnvelope {
  code: number
  message: string
  data: TodoReadResult
}

/**
 * 标记单条待办已读（幂等）。
 *
 * 只影响当前用户自己的铃铛计数，不改业务单据状态；指纹回传后若单据已推进，
 * 服务端会认为「新状态仍未读」，下次刷新自动重新提醒。
 */
export async function markTodoRead(mark: TodoReadMark): Promise<TodoReadResult> {
  const headers = await getAuthHeaders()
  const response = await apiFetch<TodoReadResultEnvelope>('/api/v1/workbench/todos/read', {
    method: 'POST',
    headers,
    body: JSON.stringify(mark),
  })
  return response.data
}

/** 一键已读：批量写入客户端当前看到的未读项（空列表直接返回 0）。 */
export async function markAllTodosRead(items: TodoReadMark[]): Promise<TodoReadResult> {
  if (items.length === 0) return { marked: 0 }

  const headers = await getAuthHeaders()
  const response = await apiFetch<TodoReadResultEnvelope>('/api/v1/workbench/todos/read-all', {
    method: 'POST',
    headers,
    body: JSON.stringify({ items }),
  })
  return response.data
}