'use server'

import { revalidatePath } from 'next/cache'
import {
  createDeliverable as createDeliverableApi,
  updateDeliverable as updateDeliverableApi,
  deleteDeliverable as deleteDeliverableApi,
  uploadDeliverableFile as uploadDeliverableFileApi,
  generateDeliverableReport as generateDeliverableReportApi,
} from '@/lib/api/server/research'
import type { components } from '@/types/generated/schema'

type DeliverableCreate = components['schemas']['RdStageDeliverableCreate']
type DeliverableUpdate = components['schemas']['RdStageDeliverableUpdate']
type DeliverableGenerate = components['schemas']['RdStageDeliverableGenerateRequest']

export async function createDeliverable(data: DeliverableCreate) {
  const result = await createDeliverableApi(data)
  revalidatePath('/research/projects')
  return result
}

export async function updateDeliverable(id: string, data: DeliverableUpdate) {
  const result = await updateDeliverableApi(id, data)
  revalidatePath('/research/projects')
  return result
}

export async function deleteDeliverable(id: string) {
  await deleteDeliverableApi(id)
  revalidatePath('/research/projects')
}

export async function uploadDeliverableFile(deliverableId: string, formData: FormData) {
  const result = await uploadDeliverableFileApi(deliverableId, formData)
  revalidatePath('/research/projects')
  return result
}

/**
 * 阶段交付文档 → AI 生成研发报告。
 *
 * 后端一次性完成「补建/复用交付文档 → 找/建报告 → 提交后台任务」，
 * 返回 {deliverable_id, report_id, job_id, job_status, reused}，前端据此进入进度页。
 */
export async function generateDeliverable(data: DeliverableGenerate) {
  const result = await generateDeliverableReportApi(data)
  revalidatePath('/research/projects')
  revalidatePath('/research/reports')
  return result
}