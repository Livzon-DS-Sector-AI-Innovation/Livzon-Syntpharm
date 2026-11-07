'use server'

import { revalidatePath } from 'next/cache'
import type { components } from '@/types/generated/schema'
import {
  deleteDeliverableTemplateVersion as deleteDeliverableTemplateVersionApi,
  restoreDeliverableTemplateVersion as restoreDeliverableTemplateVersionApi,
} from '@/lib/api/server/research/deliverable-template'

type DocGenTemplateVersionRestoreData = components['schemas']['DocGenTemplateVersionRestoreData']

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