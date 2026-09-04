'use server'

import { revalidatePath } from 'next/cache'
import {
  ReportCreate,
  ReportUpdate,
  ReportItemsBatchSave,
  TemplateUpdate,
} from '@/types/material-report'
import {
  getReports as fetchReports,
  getReportById as fetchReportById,
  createReport as apiCreateReport,
  updateReport as apiUpdateReport,
  deleteReport as apiDeleteReport,
  saveReportItems as apiSaveReportItems,
  generateReport as apiGenerateReport,
  submitReport as apiSubmitReport,
  getReportStatistics as apiGetReportStatistics,
  getTemplates as apiGetTemplates,
  getTemplateById as apiGetTemplateById,
  uploadTemplate as apiUploadTemplate,
  updateTemplate as apiUpdateTemplate,
  deleteTemplate as apiDeleteTemplate,
  previewTemplate as apiPreviewTemplate,
  uploadReportImage as apiUploadReportImage,
  getReportImages as apiGetReportImages,
} from '@/lib/api/server/material-report'

export async function getReports(params?: {
  template_id?: string
  status?: string
  start_date?: string
  end_date?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<Record<string, unknown>> {
  return fetchReports(params) as Promise<Record<string, unknown>>
}

export async function getReportById(id: string): Promise<Record<string, unknown>> {
  return fetchReportById(id) as Promise<Record<string, unknown>>
}

export async function createReport(data: ReportCreate): Promise<Record<string, unknown>> {
  const processedData = {
    ...data,
    report_date: typeof data.report_date === 'object' && 'format' in data.report_date
      ? (data.report_date as { format: (fmt: string) => string }).format('YYYY-MM-DD')
      : data.report_date,
  }
  const result = await apiCreateReport(processedData)
  revalidatePath('/quality/material-report')
  return result as Record<string, unknown>
}

export async function updateReport(id: string, data: ReportUpdate): Promise<Record<string, unknown>> {
  const processedData = {
    ...data,
    report_date: data.report_date && typeof data.report_date === 'object' && 'format' in data.report_date
      ? (data.report_date as { format: (fmt: string) => string }).format('YYYY-MM-DD')
      : data.report_date,
  }
  const result = await apiUpdateReport(id, processedData)
  revalidatePath('/quality/material-report')
  return result as Record<string, unknown>
}

export async function deleteReport(id: string): Promise<Record<string, unknown>> {
  const result = await apiDeleteReport(id)
  revalidatePath('/quality/material-report')
  return result as Record<string, unknown>
}

export async function saveReportItems(id: string, data: ReportItemsBatchSave): Promise<Record<string, unknown>> {
  const result = await apiSaveReportItems(id, data)
  revalidatePath('/quality/material-report')
  return result as Record<string, unknown>
}

export async function generateReport(id: string) {
  return apiGenerateReport(id)
}

export async function submitReport(id: string): Promise<Record<string, unknown>> {
  const result = await apiSubmitReport(id)
  revalidatePath('/quality/material-report')
  return result as Record<string, unknown>
}

export async function getReportStatistics() {
  return apiGetReportStatistics()
}

export async function getTemplates(params?: {
  is_active?: boolean
  page?: number
  page_size?: number
}) {
  return apiGetTemplates(params)
}

export async function getTemplateById(id: string) {
  return apiGetTemplateById(id)
}

export async function uploadTemplate(
  file: File,
  templateName: string,
  templateDescription?: string,
  fieldMapping?: Record<string, unknown>,
  tableFields?: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const result = await apiUploadTemplate(file, templateName, templateDescription, fieldMapping, tableFields)
  revalidatePath('/quality/material-report')
  return result as Record<string, unknown>
}

export async function updateTemplate(id: string, data: TemplateUpdate): Promise<Record<string, unknown>> {
  const result = await apiUpdateTemplate(id, data)
  revalidatePath('/quality/material-report')
  return result as Record<string, unknown>
}

export async function deleteTemplate(id: string): Promise<Record<string, unknown>> {
  const result = await apiDeleteTemplate(id)
  revalidatePath('/quality/material-report')
  return result as Record<string, unknown>
}

export async function previewTemplate(id: string) {
  return apiPreviewTemplate(id)
}

export async function uploadReportImage(
  reportId: string,
  file: File,
  fieldKey?: string,
  rowIndex?: number
): Promise<Record<string, unknown>> {
  return apiUploadReportImage(reportId, file, fieldKey, rowIndex) as Promise<Record<string, unknown>>
}

export async function getReportImages(reportId: string): Promise<Record<string, unknown>> {
  return apiGetReportImages(reportId) as Promise<Record<string, unknown>>
}
