'use server'

import { revalidatePath } from 'next/cache'
import type {
  SingleCheckRequest,
  BatchCheckRequest,
  ProblemHandleRequest,
  CheckRecordFilter,
  PaginatedResponse,
  CheckMain,
  CheckMainDetail,
  SopAiConfig,
  ScheduledJob,
  CheckTaskResponse,
  BatchCheckResult,
} from '@/types/sop-ai'
import {
  getConfigs as getConfigsServer,
  getConfig as getConfigServer,
  updateConfig as updateConfigServer,
  singleCheck as singleCheckServer,
  batchCheck as batchCheckServer,
  getCheckRecords as getCheckRecordsServer,
  getCheckRecordDetail as getCheckRecordDetailServer,
  exportCheckReport as exportCheckReportServer,
  handleProblem as handleProblemServer,
  getScheduledJobs as getScheduledJobsServer,
  createScheduledJob as createScheduledJobServer,
  deleteScheduledJob as deleteScheduledJobServer,
} from '@/lib/api/server/sop-ai'

export async function getConfigs(): Promise<SopAiConfig[]> {
  const response = await getConfigsServer()
  return response.data || []
}

export async function getConfig(configKey: string): Promise<string> {
  const response = await getConfigServer(configKey)
  return response.data?.config_value || ''
}

export async function updateConfig(
  configKey: string,
  configValue: string,
  description?: string,
  operator?: string
): Promise<SopAiConfig> {
  const response = await updateConfigServer(configKey, {
    config_value: configValue,
    description,
    operator,
  })
  revalidatePath('/quality/sop-ai')
  return response.data
}

export async function singleCheck(
  request: SingleCheckRequest
): Promise<CheckTaskResponse> {
  const response = await singleCheckServer(request)
  revalidatePath('/quality/sop-ai')
  return response.data
}

export async function batchCheck(
  request: BatchCheckRequest
): Promise<BatchCheckResult> {
  const response = await batchCheckServer(request)
  revalidatePath('/quality/sop-ai')
  return response.data
}

export async function getCheckRecords(
  filter?: CheckRecordFilter
): Promise<PaginatedResponse<CheckMain>> {
  const response = await getCheckRecordsServer(filter as Record<string, unknown> || {})
  return response.data
}

export async function getCheckRecordDetail(id: string): Promise<CheckMainDetail> {
  const response = await getCheckRecordDetailServer(id)
  return response.data
}

export async function exportCheckReport(
  id: string,
  format: 'excel' | 'pdf' = 'excel',
  includeProblems: boolean = true
): Promise<{ download_url: string }> {
  const response = await exportCheckReportServer(id, format, includeProblems)
  return response.data
}

export async function handleProblem(
  problemId: string,
  request: ProblemHandleRequest
): Promise<{ id: string; handle_status: string; ignore_reason?: string }> {
  const response = await handleProblemServer(problemId, request)
  revalidatePath('/quality/sop-ai')
  return response.data
}

export async function getScheduledJobs(): Promise<ScheduledJob[]> {
  const response = await getScheduledJobsServer()
  return response.data || []
}

export async function createScheduledJob(
  job: Omit<ScheduledJob, 'next_run_time' | 'last_run_time' | 'run_count'>
): Promise<ScheduledJob> {
  const response = await createScheduledJobServer(job)
  revalidatePath('/quality/sop-ai')
  return response.data
}

export async function deleteScheduledJob(jobId: string): Promise<boolean> {
  const response = await deleteScheduledJobServer(jobId)
  revalidatePath('/quality/sop-ai')
  return response.data.deleted
}