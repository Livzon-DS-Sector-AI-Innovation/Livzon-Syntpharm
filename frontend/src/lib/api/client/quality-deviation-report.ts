// 偏差报告的「保存并下载」与「下载原文档」返回二进制流，Server Action 无法把
// Blob 交给浏览器，故按 AGENTS.md 的流式例外条款放在 lib/api/client/ 直接用 fetch。
// 上传与 AI 优化见 actions/quality.ts。

const API_BASE = '/api/v1/quality/deviation-report'

async function readErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body = (await res.json()) as { message?: string; detail?: string }
    if (typeof body.message === 'string' && body.message) return body.message
    if (typeof body.detail === 'string' && body.detail) return body.detail
  } catch {
    // 非 JSON 响应，保留兜底文案
  }
  return fallback
}

export function triggerBlobDownload(blob: Blob, fileName: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/** 保存编辑后的 HTML 为 Word，并触发浏览器下载 */
export async function saveDeviationReport(fileId: string, htmlContent: string): Promise<void> {
  const res = await fetch(`${API_BASE}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId, html_content: htmlContent }),
  })
  if (!res.ok) throw new Error(await readErrorMessage(res, '保存失败'))
  triggerBlobDownload(await res.blob(), `偏差报告_${Date.now()}.docx`)
}

/** 下载原始上传的 Word 文档 */
export async function downloadDeviationReport(fileId: string, fileName: string): Promise<void> {
  const res = await fetch(`${API_BASE}/download?file_id=${encodeURIComponent(fileId)}`)
  if (!res.ok) throw new Error(await readErrorMessage(res, '下载失败'))
  triggerBlobDownload(await res.blob(), fileName)
}