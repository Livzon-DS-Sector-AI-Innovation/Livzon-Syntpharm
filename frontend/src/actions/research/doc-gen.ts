'use server'

import { revalidatePath } from 'next/cache'
import type { components } from '@/types/generated/schema'
import {
  cancelDocGenJob as cancelDocGenJobApi,
  completeDocGenConversation as completeDocGenConversationApi,
  confirmDocGenJob as confirmDocGenJobApi,
  deleteDeliverableTemplateVersion as deleteDeliverableTemplateVersionApi,
  extractDocGenJob as extractDocGenJobApi,
  restoreDeliverableTemplateVersion as restoreDeliverableTemplateVersionApi,
  sendDocGenMessage as sendDocGenMessageApi,
  skipDocGenConversation as skipDocGenConversationApi,
  updateDocGenJob as updateDocGenJobApi,
} from '@/lib/api/server/research/doc-gen'

type DocGenJobResponse = components['schemas']['DocGenJobResponse']
type DocGenConversationData = components['schemas']['DocGenConversationData']
type DocGenTemplateVersionRestoreData = components['schemas']['DocGenTemplateVersionRestoreData']

/** 交付物模板页路由，写操作后据此失效缓存 */
const DELIVERABLE_TEMPLATES_PATH = '/research/deliverable-templates'

/** 取消文档生成任务（排队中或进行中 / 待确认） */
export async function cancelDocGenJob(jobId: string): Promise<DocGenJobResponse> {
  const job = await cancelDocGenJobApi(jobId)
  revalidatePath('/research')
  return job
}

/** 触发 AI 提取信息：对话模式（DOC_GEN_CHAT_ENABLED=true）下任务停在草稿，由用户手动开始 */
export async function extractDocGenJob(jobId: string): Promise<DocGenJobResponse> {
  const job = await extractDocGenJobApi(jobId)
  revalidatePath('/research')
  return job
}

/** 确认提取结果并生成；slots 只含被改过的填充项（key → 修正后的文本） */
export async function confirmDocGenJob(jobId: string, slots: Record<string, string>): Promise<DocGenJobResponse> {
  const job = await confirmDocGenJobApi(jobId, slots)
  revalidatePath('/research')
  return job
}

/** 发送一条对话消息：模型抽值后写入槽位，返回更新后的会话与消息 */
export async function sendDocGenMessage(jobId: string, content: string): Promise<DocGenConversationData> {
  const data = await sendDocGenMessageApi(jobId, content)
  revalidatePath('/research')
  return data
}

/** 完成对话：保留已补值，转由确认页逐项检查 */
export async function completeDocGenConversation(jobId: string): Promise<DocGenConversationData> {
  const data = await completeDocGenConversationApi(jobId)
  revalidatePath('/research')
  return data
}

/** 跳过对话：与完成等效，仅不计入轮数 */
export async function skipDocGenConversation(jobId: string): Promise<DocGenConversationData> {
  const data = await skipDocGenConversationApi(jobId)
  revalidatePath('/research')
  return data
}

/** 修改报告基本信息与补充说明 */
export async function updateDocGenJob(
  jobId: string,
  payload: {
    doc_code?: string | null
    doc_version?: string | null
    drug_name?: string | null
    supplement_text?: string | null
    template_code?: string | null
  },
): Promise<DocGenJobResponse> {
  const job = await updateDocGenJobApi(jobId, payload)
  revalidatePath('/research')
  return job
}

/**
 * 回滚交付物模板到指定历史版本。
 *
 * 后端以该版本内容新建一个版本并设为当前生效，不就地改写历史，
 * 因此回滚本身也会在版本历史里留下新的一条记录。
 */
export async function restoreDeliverableTemplateVersion(
  templateId: string,
  versionId: string,
): Promise<DocGenTemplateVersionRestoreData> {
  const data = await restoreDeliverableTemplateVersionApi(templateId, versionId)
  revalidatePath(DELIVERABLE_TEMPLATES_PATH)
  return data
}

/** 删除交付物模板的一个历史版本（当前生效版本与唯一版本由后端拒绝） */
export async function deleteDeliverableTemplateVersion(templateId: string, versionId: string): Promise<void> {
  await deleteDeliverableTemplateVersionApi(templateId, versionId)
  revalidatePath(DELIVERABLE_TEMPLATES_PATH)
}
