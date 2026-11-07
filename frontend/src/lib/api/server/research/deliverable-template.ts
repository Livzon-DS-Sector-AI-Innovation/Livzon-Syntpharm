/**
 * 交付物模板 —— 服务端 API（Server Component / Server Action 使用）
 *
 * 只含版本回滚与版本删除两个写操作；上传/下载必须走浏览器侧
 * （见 lib/api/client/research/deliverable-template.ts 的例外说明）。
 */
import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

const DOC_TEMPLATE_BASE = '/api/v1/research/doc-gen/deliverable-templates'

type DocGenTemplateVersionRestoreData = components['schemas']['DocGenTemplateVersionRestoreData']

/**
 * 回滚交付物模板到指定历史版本。
 *
 * 后端不在旧记录上原地生效，而是以该版本内容新建 v(N+1) 并设为当前生效版本
 * （类似 git revert），因此历史版本不可改写、可再次回滚回来。
 */
export async function restoreDeliverableTemplateVersion(
  templateId: string,
  versionId: string,
): Promise<DocGenTemplateVersionRestoreData> {
  const result = await apiFetch<components['schemas']['DocGenTemplateVersionRestoreResponse']>(
    `${getApiBaseUrl()}${DOC_TEMPLATE_BASE}/${templateId}/versions/${versionId}/restore`,
    { method: 'POST' },
  )
  return result.data
}

/** 删除模板的一个历史版本；当前生效版本与唯一版本后端会拒绝并返回业务提示 */
export async function deleteDeliverableTemplateVersion(templateId: string, versionId: string): Promise<void> {
  await apiFetch<components['schemas']['DocGenOperationResponse']>(
    `${getApiBaseUrl()}${DOC_TEMPLATE_BASE}/${templateId}/versions/${versionId}`,
    { method: 'DELETE' },
  )
}