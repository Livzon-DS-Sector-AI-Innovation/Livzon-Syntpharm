import { apiFetch } from './base'

const API_BASE = '/api/v1/quality'

/** 启动 AI 预审，返回 task_id */
export async function startDocCheck(fileId: string, checkConfig: unknown) {
  return apiFetch<{ code: number; message?: string; data: { task_id: string } }>(`${API_BASE}/check`, {
    method: 'POST',
    body: JSON.stringify({ file_id: fileId, check_config: checkConfig }),
  })
}

/** 确认预审通过 */
export async function confirmDocCheckRecord(recordId: string) {
  return apiFetch<{ code: number; message?: string; data: unknown }>(`${API_BASE}/records/${recordId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

/** 更新问题处理结果 */
export async function updateDocCheckProblem(
  problemId: string,
  payload: { handle_status: string; ignore_reason?: string },
) {
  return apiFetch<{ code: number; message?: string; data: unknown }>(`${API_BASE}/problems/${problemId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

/** 删除偏差单 */
export async function deleteDeviationFlow(deviationId: string) {
  return apiFetch<{ code: number; message?: string; data: unknown }>(`${API_BASE}/deviation-flow/${deviationId}`, {
    method: 'DELETE',
  })
}
