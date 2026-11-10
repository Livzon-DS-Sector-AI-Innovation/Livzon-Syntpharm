'use server'

import { revalidatePath } from 'next/cache'

import {
  cancelReportGenJob as cancelReportGenJobApi,
  createReportGenFeedback as createReportGenFeedbackApi,
  createReportGenJob as createReportGenJobApi,
  deleteTemplateExample as deleteTemplateExampleApi,
  promoteReportGenFeedback as promoteReportGenFeedbackApi,
  testReportGenModel as testReportGenModelApi,
  updateReportGenFeedback as updateReportGenFeedbackApi,
  updateReportGenSlot as updateReportGenSlotApi,
  updateTemplateExample as updateTemplateExampleApi,
} from '@/lib/api/server/research/report-gen'
import type {
  ReportGenExampleUpdate,
  ReportGenFeedbackCreate,
  ReportGenJobCreate,
  ReportGenModelSlot,
  ReportGenSlotUpdate,
} from '@/types/research/report-gen'

/** 提交生成任务：立即返回任务行，后台 worker 异步跑 Agent。 */
export async function submitReportGenJob(payload: ReportGenJobCreate) {
  const result = await createReportGenJobApi(payload)
  revalidatePath('/research')
  return result
}

/** 终止执行中/排队中的任务。 */
export async function cancelReportGenJob(jobId: string) {
  const result = await cancelReportGenJobApi(jobId)
  revalidatePath('/research')
  revalidatePath(`/research/reports/generation/${jobId}`)
  return result
}

/** 人工修正槽位：只改结果区与对照表口径，不重渲染成品。 */
export async function saveReportGenSlot(jobId: string, slotKey: string, payload: ReportGenSlotUpdate) {
  const result = await updateReportGenSlotApi(jobId, slotKey, payload)
  revalidatePath(`/research/reports/generation/${jobId}`)
  return result
}

/**
 * 提一条评审意见：只记录不立即执行。
 * 下一次生成（含详情页「重新生成」）会把该报告下未落实的意见自动拼进补充说明。
 */
export async function createReportGenFeedback(jobId: string, payload: ReportGenFeedbackCreate) {
  const result = await createReportGenFeedbackApi(jobId, payload)
  revalidatePath(`/research/reports/generation/${jobId}`)
  return result
}

/** 处置意见：标不采纳后不再带入下一次生成，重新打开则恢复带入。 */
export async function updateReportGenFeedback(feedbackId: string, status: 'open' | 'ignored') {
  return updateReportGenFeedbackApi(feedbackId, status)
}

/**
 * 把已落实的意见沉淀成槽位示例：值取自那次生成的实际写法，所以只传意见 id。
 * 落库后同模板的下一次生成会把它当 few-shot 参照，等于把「评审一次」变成「永久学会」。
 */
export async function promoteReportGenFeedback(feedbackId: string) {
  return promoteReportGenFeedbackApi(feedbackId)
}

/**
 * 单档位连通测试：后端按「已保存的配置」解析该档位后发一次极短对话。
 * 不写配置、不影响全局活跃模型，因此不做 revalidate。
 */
export async function testReportGenModel(slot: ReportGenModelSlot) {
  return testReportGenModelApi({ slot })
}

/** 人工维护一条槽位示例：改写法 / 补依据 / 停用。 */
export async function updateReportGenExample(exampleId: string, payload: ReportGenExampleUpdate) {
  return updateTemplateExampleApi(exampleId, payload)
}

/** 删除一条槽位示例（后端软删）：之后不再注入生成。 */
export async function deleteReportGenExample(exampleId: string) {
  return deleteTemplateExampleApi(exampleId)
}