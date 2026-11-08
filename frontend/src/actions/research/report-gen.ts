'use server'

import { revalidatePath } from 'next/cache'

import {
  cancelReportGenJob as cancelReportGenJobApi,
  createReportGenJob as createReportGenJobApi,
  testReportGenModel as testReportGenModelApi,
  updateReportGenSlot as updateReportGenSlotApi,
} from '@/lib/api/server/research/report-gen'
import type {
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
 * 单档位连通测试：后端按「已保存的配置」解析该档位后发一次极短对话。
 * 不写配置、不影响全局活跃模型，因此不做 revalidate。
 */
export async function testReportGenModel(slot: ReportGenModelSlot) {
  return testReportGenModelApi({ slot })
}