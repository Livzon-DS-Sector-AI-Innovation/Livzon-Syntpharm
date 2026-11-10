'use server'

import { revalidatePath } from 'next/cache'
import type { components } from '@/types/generated/schema'
import {
  deleteDeliverableTemplateVersion as deleteDeliverableTemplateVersionApi,
  generateDeliverableTemplateSample as generateDeliverableTemplateSampleApi,
  reparseDeliverableTemplateSlots as reparseDeliverableTemplateSlotsApi,
  restoreDeliverableTemplateVersion as restoreDeliverableTemplateVersionApi,
  saveDeliverableTemplateSlots as saveDeliverableTemplateSlotsApi,
} from '@/lib/api/server/research/deliverable-template'

type DocGenTemplateVersionRestoreData = components['schemas']['DocGenTemplateVersionRestoreData']
type DocGenTemplateSampleData = components['schemas']['DocGenTemplateSampleData']
type DocGenSlotsSaveData = components['schemas']['DocGenTemplateSlotsSaveData']
type DocGenSlotsReparseData = components['schemas']['DocGenTemplateSlotsReparseData']
type DocGenSlot = components['schemas']['DocGenSlotItem']

/** 交付物模板页路由，写操作后据此失效缓存 */
const DELIVERABLE_TEMPLATES_PATH = '/research/deliverable-templates'

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

/** 全量保存槽位结构；保存后下次生成生效，历史任务不受影响 */
export async function saveDeliverableTemplateSlots(
  templateId: string,
  slots: DocGenSlot[],
  token: string | null,
): Promise<DocGenSlotsSaveData> {
  const data = await saveDeliverableTemplateSlotsApi(templateId, slots, token)
  revalidatePath(DELIVERABLE_TEMPLATES_PATH)
  return data
}

/**
 * 按已保存的填充项生成填充示例稿，返回新增的示例稿版本信息。
 *
 * 不做乐观更新：结果是一条新版本记录，由页面重新拉取版本历史即可看到。
 */
export async function generateDeliverableTemplateSample(templateId: string): Promise<DocGenTemplateSampleData> {
  const data = await generateDeliverableTemplateSampleApi(templateId)
  revalidatePath(DELIVERABLE_TEMPLATES_PATH)
  return data
}

/** 强制重新识别槽位结构并按锚点合并人工修改 */
export async function reparseDeliverableTemplateSlots(
  templateId: string,
  token: string | null,
): Promise<DocGenSlotsReparseData> {
  const data = await reparseDeliverableTemplateSlotsApi(templateId, token)
  revalidatePath(DELIVERABLE_TEMPLATES_PATH)
  return data
}

/**
 * 流式重解析结束后只刷缓存。
 *
 * 分析本身已经由流式接口写库，这里不能再调同步接口（会白跑一次模型），
 * 但仍要让模板列表看到新的分析时间。
 */
export async function revalidateDeliverableTemplates(): Promise<void> {
  revalidatePath(DELIVERABLE_TEMPLATES_PATH)
}