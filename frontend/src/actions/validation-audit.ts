'use server'

import { revalidatePath } from 'next/cache'
import type { ValidationAuditTaskCreate } from '@/types/validation-audit'
import {
  fetchTasks as fetchTasksApi,
  fetchTaskById as fetchTaskByIdApi,
  fetchFiles as fetchFilesApi,
  fetchIssues as fetchIssuesApi,
  fetchReport as fetchReportApi,
  createTask as createTaskServer,
  deleteTask as deleteTaskServer,
  uploadFiles as uploadFilesServer,
  parseFiles as parseFilesServer,
  runAudit as runAuditServer,
} from '@/lib/api/server/validation-audit'

export async function fetchTasksServer(params?: {
  product_name?: string
  source_company?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<Record<string, unknown> | null> {
  try {
    return await fetchTasksApi(params)
  } catch {
    return null
  }
}

export async function fetchTaskByIdServer(id: string): Promise<Record<string, unknown> | null> {
  try {
    return await fetchTaskByIdApi(id)
  } catch {
    return null
  }
}

export async function fetchFilesServer(taskId: string): Promise<Record<string, unknown> | null> {
  try {
    return await fetchFilesApi(taskId)
  } catch {
    return null
  }
}

export async function fetchIssuesServer(taskId: string, issueType?: string): Promise<Record<string, unknown> | null> {
  try {
    return await fetchIssuesApi(taskId, issueType)
  } catch {
    return null
  }
}

export async function fetchReportServer(taskId: string): Promise<Record<string, unknown> | null> {
  try {
    return await fetchReportApi(taskId)
  } catch {
    return null
  }
}

export async function createValidationAuditTask(
  data: ValidationAuditTaskCreate
): Promise<{ success: boolean; message: string; data?: Record<string, unknown> }> {
  try {
    const result = await createTaskServer(data)
    revalidatePath('/registration/validation-audit')
    return result as { success: boolean; message: string; data?: Record<string, unknown> }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : '创建任务失败',
    }
  }
}

export async function deleteValidationAuditTask(
  taskId: string
): Promise<{ success: boolean; message: string }> {
  try {
    const result = await deleteTaskServer(taskId)
    revalidatePath('/registration/validation-audit')
    return result as { success: boolean; message: string }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : '删除任务失败',
    }
  }
}

export async function uploadValidationAuditFiles(
  taskId: string,
  formData: FormData
): Promise<{ success: boolean; message: string; data?: Record<string, unknown> }> {
  try {
    const result = await uploadFilesServer(taskId, formData)
    revalidatePath(`/registration/validation-audit/${taskId}`)
    return result as { success: boolean; message: string; data?: Record<string, unknown> }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : '上传文件失败',
    }
  }
}

export async function parseValidationAuditFiles(
  taskId: string
): Promise<{ success: boolean; message: string; data?: Record<string, unknown> }> {
  try {
    const result = await parseFilesServer(taskId)
    revalidatePath(`/registration/validation-audit/${taskId}`)
    return result as { success: boolean; message: string; data?: Record<string, unknown> }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : '文件解析失败',
    }
  }
}

export async function runValidationAudit(
  taskId: string
): Promise<{ success: boolean; message: string; data?: Record<string, unknown> }> {
  try {
    const result = await runAuditServer(taskId)
    revalidatePath(`/registration/validation-audit/${taskId}`)
    revalidatePath('/registration/validation-audit')
    return result as { success: boolean; message: string; data?: Record<string, unknown> }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : '审核执行失败',
    }
  }
}