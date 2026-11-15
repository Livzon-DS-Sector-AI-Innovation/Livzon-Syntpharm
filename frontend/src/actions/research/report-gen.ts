'use server'

import { revalidatePath } from 'next/cache'

import {
  cancelReportGenJob as cancelReportGenJobApi,
  createReportGenFeedback as createReportGenFeedbackApi,
  createReportGenJob as createReportGenJobApi,
  restoreReportGenVersion as restoreReportGenVersionApi,
  saveReportGenEdits as saveReportGenEditsApi,
  testReportGenModel as testReportGenModelApi,
  updateReportGenFeedback as updateReportGenFeedbackApi,
  updateReportGenOpinion as updateReportGenOpinionApi,
} from '@/lib/api/server/research/report-gen'
import type {
  ReportGenEditRequest,
  ReportGenFeedbackCreate,
  ReportGenJobCreate,
  ReportGenModelSlot,
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

/** 停用 / 恢复一条历史意见：停用后不再进入生成前的写作要求汇总。 */
export async function updateReportGenOpinion(opinionId: string, status: 'active' | 'disabled') {
  const result = await updateReportGenOpinionApi(opinionId, status)
  revalidatePath('/research')
  return result
}

/**
 * 在线编辑保存：一批操作提交后逐条生效。
 *
 * 校验未通过的操作后端会丢弃并把该处还原成母本原样，其余照常保存；前端不做乐观更新，
 * 免得出现「界面已改、文档没改」的错位。
 */
export async function saveReportGenEdits(jobId: string, payload: ReportGenEditRequest) {
  const result = await saveReportGenEditsApi(jobId, payload)
  if (result.applied > 0) {
    revalidatePath(`/research/reports/generation/${jobId}`)
    revalidatePath('/research')
  }
  return result
}

/** 回滚到某一版：产生新版本，不覆盖历史。 */
export async function restoreReportGenVersion(jobId: string, versionId: string, baseVersionId?: string | null) {
  const result = await restoreReportGenVersionApi(jobId, versionId, baseVersionId)
  revalidatePath(`/research/reports/generation/${jobId}`)
  return result
}

/**
 * 单档位连通测试：后端按「已保存的配置」解析该档位后发一次极短对话。
 * 不写配置、不影响全局活跃模型，因此不做 revalidate。
 */
export async function testReportGenModel(slot: ReportGenModelSlot) {
  return testReportGenModelApi({ slot })
}
