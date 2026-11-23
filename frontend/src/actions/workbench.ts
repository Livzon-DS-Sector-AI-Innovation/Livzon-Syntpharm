'use server'

import { markAllTodosRead as markAllTodosReadServer, markTodoRead as markTodoReadServer } from '@/lib/api/server/workbench'
import type { TodoReadMark, TodoReadResult } from '@/types/workbench'

/**
 * 标记单条待办已读（幂等）。
 *
 * 只影响当前用户自己的铃铛计数，不改业务单据状态；指纹回传后若单据已推进，
 * 服务端会认为「新状态仍未读」，下次刷新自动重新提醒。
 */
export async function markTodoRead(mark: TodoReadMark): Promise<TodoReadResult> {
  return markTodoReadServer(mark)
}

/** 一键已读：批量写入客户端当前看到的未读项（空列表直接返回 0）。 */
export async function markAllTodosRead(items: TodoReadMark[]): Promise<TodoReadResult> {
  return markAllTodosReadServer({ items })
}