/**
 * 交付物模板文件下载（浏览器侧）
 *
 * 文档生成任务已迁移到 `report-gen`（异步 Agent 生成），本文件只保留
 * 模板母本的下载读取能力——文件流必须由浏览器直接接收，属 AGENTS.md
 * 允许的 client fetch 例外。
 */

/** 下载模板母本文件（Word），返回 Blob 供预览或另存。 */
export async function downloadDeliverableTemplate(id: string): Promise<Blob> {
  const response = await fetch(`/api/v1/research/doc-gen/deliverable-templates/${id}/download`, {
    cache: 'no-store',
    credentials: 'include',
  })
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { message?: string; detail?: string } | null
    throw new Error(error?.message || error?.detail || `下载失败: ${response.status}`)
  }
  return response.blob()
}