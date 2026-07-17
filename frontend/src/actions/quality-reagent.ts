'use server'

/**
 * 质量检验试剂/标准品管理 Server Actions
 */

import { revalidatePath } from 'next/cache'
import type {
  Reagent,
  ReagentListResponse,
  CreateReagentRequest,
  UpdateReagentRequest,
  AiRecognizeResponse,
} from '@/types/reagent-quality'
import {
  recognizeReagentLabel as recognizeReagentLabelApi,
  getNextIncomingLotNo as getNextIncomingLotNoApi,
  getReagentList as getReagentListApi,
  getReagentDetail as getReagentDetailApi,
  createReagent as createReagentApi,
  updateReagent as updateReagentApi,
  deleteReagent as deleteReagentApi,
  exportReagentsExcel as exportReagentsExcelApi,
  saveReagentReminderConfig as saveReagentReminderConfigApi,
  triggerReagentReminderCheck as triggerReagentReminderCheckApi,
  setReagentItemReminder as setReagentItemReminderApi,
} from '@/lib/api/server/quality-reagent'

export async function recognizeReagentLabel(
  fileList: File[]
): Promise<{ code: number; message: string; data: AiRecognizeResponse | null }> {
  const formData = new FormData()
  fileList.forEach((file) => {
    formData.append('files', file)
  })
  return recognizeReagentLabelApi(formData)
}

export async function getNextIncomingLotNo(
  dateStr?: string
): Promise<{ code: number; message: string; data: { incoming_lot_no: string } | null }> {
  return getNextIncomingLotNoApi(dateStr)
}

export async function getReagentList(params: {
  keyword?: string
  category?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<{ code: number; message: string; data: ReagentListResponse }> {
  return getReagentListApi(params)
}

export async function getReagentDetail(
  reagentId: string
): Promise<{ code: number; message: string; data: Reagent | null }> {
  return getReagentDetailApi(reagentId)
}

export async function createReagent(
  data: CreateReagentRequest
): Promise<{ code: number; message: string; data: Reagent | null }> {
  return createReagentApi(data)
}

export async function updateReagent(
  reagentId: string,
  data: UpdateReagentRequest
): Promise<{ code: number; message: string; data: Reagent | null }> {
  return updateReagentApi(reagentId, data)
}

export async function deleteReagent(
  reagentId: string
): Promise<{ code: number; message: string; data: null }> {
  return deleteReagentApi(reagentId)
}

export async function exportReagentsExcel(params?: {
  keyword?: string
  category?: string
  status?: string
}): Promise<void> {
  const response = await exportReagentsExcelApi(params)
  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = `试剂台账_${new Date().toISOString().split('T')[0]}.xlsx`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename\*?=['"]?(?:UTF-8'')?([^;\n"']+)/i)
    if (match) {
      filename = decodeURIComponent(match[1])
    }
  }
  const blob = await response.blob()
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

export async function saveReagentReminderConfig(data: Record<string, unknown>) {
  return saveReagentReminderConfigApi(data)
}

export async function triggerReagentReminderCheck() {
  return triggerReagentReminderCheckApi()
}

export async function setReagentItemReminder(reagentName: string, isEnabled: boolean) {
  return setReagentItemReminderApi(reagentName, isEnabled)
}