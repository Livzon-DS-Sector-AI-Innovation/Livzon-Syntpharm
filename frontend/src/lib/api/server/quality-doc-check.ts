import type { components } from '@/types/generated/schema'
import type { MessageResponse } from '@/types/common'

import { apiFetch } from './base'

const API_BASE = '/api/v1/quality'

/** 启动 AI 预审，返回 task_id */
export async function startDocCheck(fileId: string, checkConfig: unknown) {
  return apiFetch<components['schemas']['DocCheckTaskApiResponse']>(`${API_BASE}/check`, {
    method: 'POST',
    body: JSON.stringify({ file_id: fileId, check_config: checkConfig }),
  })
}

/** 确认预审通过 */
export async function confirmDocCheckRecord(recordId: string) {
  return apiFetch<components['schemas']['DocCheckConfirmApiResponse']>(`${API_BASE}/records/${recordId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

/** 更新问题处理结果 */
export async function updateDocCheckProblem(
  problemId: string,
  payload: { handle_status: string; ignore_reason?: string },
) {
  return apiFetch<components['schemas']['ProblemApiResponse']>(`${API_BASE}/problems/${problemId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

/** 删除偏差单（deviation_flow 路由未注册进 OpenAPI，使用 code/message 信封类型） */
export async function deleteDeviationFlow(deviationId: string) {
  return apiFetch<MessageResponse>(`${API_BASE}/deviation-flow/${deviationId}`, {
    method: 'DELETE',
  })
}