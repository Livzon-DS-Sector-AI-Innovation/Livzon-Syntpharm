// 文件上传必须走浏览器直传（FormData），Server Action 无法把 File 以 multipart 形式
// 交给后端，故按 AGENTS.md 的上传例外条款放在 lib/api/client/。
// 其余 JSON 写操作见 actions/quality.ts。

import type { ApiResponse } from '@/types/common'

const API_BASE = '/api/v1/quality'

async function parseEnvelope<T>(res: Response, fallback: string): Promise<ApiResponse<T>> {
  const body = (await res.json()) as ApiResponse<T>
  if (!res.ok) {
    throw new Error(body?.message || fallback)
  }
  return body
}

/** 上传文件并登记元数据（文档预审用） */
export async function uploadDocCheckFile<T>(formData: FormData): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData })
  return parseEnvelope<T>(res, '文件上传失败')
}

/** 给偏差单上传附件 */
export async function uploadDeviationFlowAttachment<T = unknown>(
  deviationId: string,
  formData: FormData,
): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}/deviation-flow/${deviationId}/attachments`, {
    method: 'POST',
    body: formData,
  })
  return parseEnvelope<T>(res, '附件上传失败')
}