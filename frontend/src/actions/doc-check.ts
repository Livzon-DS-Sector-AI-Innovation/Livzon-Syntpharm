'use server'

import { revalidatePath } from 'next/cache'
import {
  CheckConfig,
  CheckMain,
  CheckProblem,
  HandleStatus,
  UploadFileRequest,
  StartCheckRequest,
  HandleProblemRequest,
  QueryCheckRecordsRequest,
  UploadFileResponse,
  StartCheckResponse,
  CheckProgressResponse,
  CheckRecordResponse,
  CheckRecordDetailResponse,
  ExportReportResponse,
  HandleProblemResponse,
  ApiResponse,
} from '@/types/doc-check'
import {
  startCheckApi,
  getCheckProgressApi,
  batchCheckApi,
  getCheckRecordsApi,
  getCheckRecordDetailApi,
  handleProblemApi,
  exportCheckReportApi,
  getCheckConfigApi,
  updateCheckConfigApi,
} from '@/lib/api/server/doc-check'

export async function uploadFile(
  request: UploadFileRequest
): Promise<UploadFileResponse> {
  const file_id = `file_${Date.now()}_${Math.random().toString(36).slice(2)}`

  return {
    file_id,
    file_name: request.file_name,
    file_path: `/uploads/${file_id}`,
    file_size: 0,
    file_ext: request.file_name.split('.').pop() || '',
  }
}

export async function getUploadProgress(
  uploadId: string
): Promise<{ progress: number; file_id?: string }> {
  return {
    progress: 100,
    file_id: uploadId,
  }
}

export async function startCheck(
  request: StartCheckRequest
): Promise<StartCheckResponse> {
  const response = await startCheckApi(request) as ApiResponse<{ task_id: string; status: string }>

  revalidatePath('/quality/doc-check')

  const data = response.data || { task_id: request.file_id, status: 'pending' }

  return {
    task_id: data.task_id || request.file_id,
    status: (data.status as any) || 'pending',
    message: response.message,
  }
}

export async function getCheckProgress(
  taskId: string
): Promise<CheckProgressResponse> {
  try {
    const response = await getCheckProgressApi(taskId) as ApiResponse<any>

    const data = response.data || {}

    return {
      task_id: taskId,
      status: data.status || 'pending',
      progress: data.status === 'completed' ? 100 : 50,
      current_step: data.status === 'completed' ? '完成' : '校验中',
      message: data.result_summary,
    }
  } catch {
    return {
      task_id: taskId,
      status: 'pending',
      progress: 0,
      current_step: '等待处理',
    }
  }
}

export async function batchCheck(
  fileIds: string[],
  checkConfig: CheckConfig,
  operator?: string
): Promise<{ task_id: string; status: string }> {
  const response = await batchCheckApi(fileIds, checkConfig, operator) as ApiResponse<{ task_id: string; status: string }>
  revalidatePath('/quality/doc-check')
  return response.data || { task_id: fileIds[0], status: 'pending' }
}

export async function getCheckRecords(
  filter?: QueryCheckRecordsRequest
): Promise<CheckRecordResponse> {
  const response = await getCheckRecordsApi(filter) as ApiResponse<{
    items: any[]
    total: number
    page: number
    page_size: number
  }>

  const data = response.data || { items: [], total: 0, page: 1, page_size: 20 }

  const items: CheckMain[] = data.items.map((item) => ({
    id: item.id,
    file_name: item.file_name || '',
    file_no: item.file_code || item.file_name,
    file_version: item.file_version,
    file_type: item.file_type,
    preparer: item.operator,
    prepare_date: item.created_at,
    status: item.status,
    total_problems: item.total_problems || 0,
    risk_high: item.risk_high || 0,
    risk_medium: item.risk_medium || 0,
    risk_low: item.risk_low || 0,
    operator: item.operator,
    created_at: item.created_at,
    updated_at: item.updated_at,
  }))

  return {
    items,
    total: data.total,
    page: data.page,
    page_size: data.page_size,
  }
}

export async function getCheckRecordDetail(
  id: string
): Promise<CheckRecordDetailResponse> {
  const response = await getCheckRecordDetailApi(id) as ApiResponse<any>

  const data = response.data || {}

  const problems: CheckProblem[] = (data.problems || []).map((p: any) => ({
    id: p.id,
    main_id: p.main_id || id,
    problem_type: p.problem_type || 'duplicate',
    risk_level: p.risk_level || 'medium',
    location: p.location,
    description: p.description || '',
    suggestion: p.suggestion,
    handle_status: p.handle_status || 'pending',
    created_at: p.created_at,
    updated_at: p.updated_at,
  }))

  return {
    id: data.id,
    file_name: data.file_name || '',
    file_no: data.file_code || data.file_name,
    file_version: data.file_version,
    file_type: data.file_type,
    preparer: data.operator,
    prepare_date: data.created_at,
    status: data.status,
    total_problems: data.total_problems || 0,
    risk_high: data.risk_high || 0,
    risk_medium: data.risk_medium || 0,
    risk_low: data.risk_low || 0,
    operator: data.operator,
    created_at: data.created_at,
    updated_at: data.updated_at,
    problems,
  }
}

export async function handleProblem(
  problemId: string,
  request: HandleProblemRequest
): Promise<HandleProblemResponse> {
  const response = await handleProblemApi(problemId, request) as ApiResponse<{
    id: string
    handle_status: string
    ignore_reason?: string
  }>

  revalidatePath('/quality/doc-check')

  const data = response.data || {}

  return {
    id: data.id || problemId,
    handle_status: (data.handle_status as HandleStatus) || request.handle_status,
    ignore_reason: data.ignore_reason,
  }
}

export async function batchHandleProblems(
  problemIds: string[],
  request: HandleProblemRequest
): Promise<{ success_count: number }> {
  let success_count = 0

  for (const problemId of problemIds) {
    try {
      await handleProblem(problemId, request)
      success_count++
    } catch {
      // 跳过失败的问题
    }
  }

  revalidatePath('/quality/doc-check')
  return { success_count }
}

export async function exportCheckReport(
  id: string,
  format: 'pdf' | 'excel' = 'pdf'
): Promise<ExportReportResponse> {
  const response = await exportCheckReportApi(id, format) as ApiResponse<{
    download_url: string
  }>

  const data = response.data || {}

  return {
    download_url: data.download_url || '',
    file_name: `校验报告_${id}.${format}`,
  }
}

export async function confirmCheck(
  _id: string,
  _operator?: string
): Promise<{ success: boolean }> {
  revalidatePath('/quality/doc-check')
  return { success: true }
}

export async function cancelCheck(
  _taskId: string,
  _operator?: string
): Promise<{ success: boolean }> {
  revalidatePath('/quality/doc-check')
  return { success: true }
}

export async function getCheckConfig(): Promise<CheckConfig> {
  try {
    const response = await getCheckConfigApi() as ApiResponse<any[]>

    const configs = response.data || []

    const configMap: Record<string, any> = {}
    for (const c of configs) {
      configMap[c.config_key] = c.config_value
    }

    return {
      enable_duplicate_check: configMap.enable_duplicate_check !== false,
      enable_conflict_check: configMap.enable_conflict_check !== false,
      enable_regulation_check: configMap.enable_regulation_check !== false,
      enable_internal_control_check: configMap.enable_internal_control_check !== false,
      severe_duplicate_threshold: configMap.severe_duplicate_threshold || 85,
      suspected_duplicate_threshold: configMap.suspected_duplicate_threshold || 70,
    }
  } catch {
    return {
      enable_duplicate_check: true,
      enable_conflict_check: true,
      enable_regulation_check: true,
      enable_internal_control_check: false,
      severe_duplicate_threshold: 85,
      suspected_duplicate_threshold: 70,
    }
  }
}

export async function updateCheckConfig(
  config: CheckConfig,
  operator?: string
): Promise<CheckConfig> {
  const configKeys = [
    'enable_duplicate_check',
    'enable_conflict_check',
    'enable_regulation_check',
    'enable_internal_control_check',
    'severe_duplicate_threshold',
    'suspected_duplicate_threshold',
  ]

  for (const key of configKeys) {
    const value = (config as any)[key]
    if (value !== undefined) {
      try {
        await updateCheckConfigApi(key, String(value), operator)
      } catch {
        // 跳过失败
      }
    }
  }

  revalidatePath('/quality/doc-check')
  return config
}