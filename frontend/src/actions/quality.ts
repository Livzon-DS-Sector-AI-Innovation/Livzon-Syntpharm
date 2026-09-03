'use server'

import { revalidatePath } from 'next/cache'
import type {
  InspectionStandard,
  InspectionStandardItem,
  InspectionStandardFormData,
  StandardCopyData,
  ObsoleteData,
  ApprovalRecord,
  StandardQueryParams,
  ApiResponse,
  CreateDeviationRequest,
  UpdateDeviationRequest,
  CreateCapaRequest,
  UpdateCapaRequest,
  CreateDepartmentContactRequest,
  UpdateDepartmentContactRequest,
  AiLogItem,
  AiLogListResponse,
  AiLogFilter,
  UploadLcResponse,
} from '@/types/quality'
import type {
  SamplingOrder,
  SamplingOrderCreate,
  SamplingOrderUpdate,
  SamplingOrderListResponse,
  SamplingOrderFilter,
  SamplingApprovalRecord,
  SamplingApprovalCreate,
  SampleRetentionLedger,
  RetentionLedgerListResponse,
  RetentionLedgerFilter,
} from '@/types/sampling'
import type {
  IQCInspection,
  IQCInspectionCreate,
  IQCInspectionUpdate,
  IQCInspectionListResponse,
  IQCInspectionFilter,
  IQCApprovalRecord,
  IQCApprovalCreate,
} from '@/types/iqc'
import type {
  IPQCInspection,
  IPQCInspectionCreate,
  IPQCInspectionUpdate,
  IPQCInspectionListResponse,
  IPQCInspectionFilter,
  IPQCApprovalRecord,
  IPQCApprovalCreate,
} from '@/types/ipqc'
import type {
  FQCInspection,
  FQCInspectionCreate,
  FQCInspectionUpdate,
  FQCInspectionListResponse,
  FQCInspectionFilter,
  FQCApprovalRecord,
  FQCApprovalCreate,
} from '@/types/fqc'
import type {
  StabilityStudy,
  StabilityStudyCreate,
  StabilityStudyUpdate,
  StabilityStudyListResponse,
  StabilityStudyFilter,
  StabilitySampleNode,
  StabilitySampleNodeUpdate,
  StabilityInspection,
  StabilityInspectionCreate,
  StabilityInspectionUpdate,
  StabilityInspectionListResponse,
  StabilityInspectionFilter,
  StabilityApprovalCreate,
  TrendData,
} from '@/types/stability'
import {
  CapaApprovalSchema,
  CapaExecutionTrackSchema,
  CapaExecutionConfirmSchema,
  CapaEvaluationSchema,
  CapaPartCompleteSchema,
  CapaDeptHeadConfirmSchema,
  DeviationInvestigationSchema,
  DeviationReviewSchema,
  DeviationFinalCodeSchema,
  DeviationTaskCreateSchema,
  DeviationReportGenerateSchema,
  DeviationApprovalSchema,
  DeviationTaskUpdateSchema,
  DeviationTaskFieldsUpdateSchema,
  DeviationTemplateCreateSchema,
  AIConfigSaveSchema,
  AIConfigTestSchema,
  SopTemplateCreateSchema,
  SopFromTemplateCreateSchema,
  SopGenerateSchema,
  SopRuleCreateSchema,
  parse
} from '@/lib/validation/schemas'
import * as QualityServer from '@/lib/api/server/quality'

async function wrap<T>(promise: Promise<unknown>): Promise<ApiResponse<T>> {
  const data = await promise
  return { data: data as T, code: 200, message: 'ok' }
}

// ============ InspectionStandard Actions ============

export async function getStandards(params: StandardQueryParams = {}) {
  return wrap<InspectionStandard[]>(QualityServer.getStandards(params))
}

export async function getEffectiveStandards(params: { material_code?: string; material_category?: string } = {}) {
  return wrap<InspectionStandard[]>(QualityServer.getEffectiveStandards(params))
}

export async function getStandard(id: string) {
  return wrap<InspectionStandard>(QualityServer.getStandard(id))
}

export async function createStandard(data: InspectionStandardFormData) {
  const response = await wrap<InspectionStandard>(QualityServer.createStandard(data))
  revalidatePath('/quality/inspection')
  return response
}

export async function updateStandard(id: string, data: Partial<InspectionStandardFormData>) {
  const response = await wrap<InspectionStandard>(QualityServer.updateStandard(id, data))
  revalidatePath('/quality/inspection')
  return response
}

export async function deleteStandard(id: string) {
  const response = await wrap<null>(QualityServer.deleteStandard(id))
  revalidatePath('/quality/inspection')
  return response
}

export async function submitStandardForApproval(id: string) {
  const response = await wrap<InspectionStandard>(QualityServer.submitStandardForApproval(id))
  revalidatePath('/quality/inspection')
  return response
}

export async function approveStandard(id: string) {
  const response = await wrap<InspectionStandard>(QualityServer.approveStandard(id))
  revalidatePath('/quality/inspection')
  return response
}

export async function rejectStandard(id: string, comments: string) {
  const response = await wrap<InspectionStandard>(QualityServer.rejectStandard(id, comments))
  revalidatePath('/quality/inspection')
  return response
}

export async function obsoleteStandard(id: string, data: ObsoleteData) {
  const response = await wrap<InspectionStandard>(QualityServer.obsoleteStandard(id, data))
  revalidatePath('/quality/inspection')
  return response
}

export async function copyStandard(data: StandardCopyData) {
  const response = await wrap<InspectionStandard>(QualityServer.copyStandard(data))
  revalidatePath('/quality/inspection')
  return response
}

// ============ InspectionStandardItem Actions ============

export async function getStandardItems(standardId: string) {
  return wrap<InspectionStandardItem[]>(QualityServer.getStandardItems(standardId))
}

// ============ ApprovalRecord Actions ============

export async function getApprovalRecords(standardId: string) {
  return wrap<ApprovalRecord[]>(QualityServer.getApprovalRecords(standardId))
}

// ============ Sampling Order Actions (取样管理) ============

export async function getSamplingOrders(params: SamplingOrderFilter & { page?: number; page_size?: number } = {}) {
  return wrap<SamplingOrderListResponse>(QualityServer.getSamplingOrders(params))
}

export async function getSamplingOrder(id: string) {
  return wrap<SamplingOrder>(QualityServer.getSamplingOrder(id))
}

export async function createSamplingOrder(data: SamplingOrderCreate) {
  const response = await wrap<SamplingOrder>(QualityServer.createSamplingOrder(data))
  revalidatePath('/quality/sampling')
  return response
}

export async function updateSamplingOrder(id: string, data: SamplingOrderUpdate) {
  const response = await wrap<SamplingOrder>(QualityServer.updateSamplingOrder(id, data))
  revalidatePath('/quality/sampling')
  return response
}

export async function deleteSamplingOrder(id: string) {
  const response = await wrap<null>(QualityServer.deleteSamplingOrder(id))
  revalidatePath('/quality/sampling')
  return response
}

export async function submitSamplingOrderForApproval(id: string) {
  const response = await wrap<SamplingOrder>(QualityServer.submitSamplingOrderForApproval(id))
  revalidatePath('/quality/sampling')
  return response
}

export async function approveSamplingOrder(id: string, data: SamplingApprovalCreate) {
  const response = await wrap<SamplingOrder>(QualityServer.approveSamplingOrder(id, data))
  revalidatePath('/quality/sampling')
  return response
}

export async function getSamplingApprovals(orderId: string) {
  return wrap<SamplingApprovalRecord[]>(QualityServer.getSamplingApprovals(orderId))
}

// ============ Retention Ledger Actions (留样台账) ============

export async function getRetentionLedger(params: RetentionLedgerFilter & { page?: number; page_size?: number } = {}) {
  return wrap<RetentionLedgerListResponse>(QualityServer.getRetentionLedger(params))
}

export async function getRetentionByOrder(orderId: string) {
  return wrap<SampleRetentionLedger[]>(QualityServer.getRetentionByOrder(orderId))
}

// ============ IQC Inspection Actions (IQC检验) ============

export async function getIQCInspections(params: IQCInspectionFilter & { page?: number; page_size?: number } = {}) {
  return wrap<IQCInspectionListResponse>(QualityServer.getIQCInspections(params))
}

export async function getIQCInspection(id: string) {
  return wrap<IQCInspection>(QualityServer.getIQCInspection(id))
}

export async function createIQCInspection(data: IQCInspectionCreate) {
  const response = await wrap<IQCInspection>(QualityServer.createIQCInspection(data))
  revalidatePath('/quality/iqc')
  return response
}

export async function updateIQCInspection(id: string, data: IQCInspectionUpdate) {
  const response = await wrap<IQCInspection>(QualityServer.updateIQCInspection(id, data))
  revalidatePath('/quality/iqc')
  return response
}

export async function deleteIQCInspection(id: string) {
  const response = await wrap<null>(QualityServer.deleteIQCInspection(id))
  revalidatePath('/quality/iqc')
  return response
}

export async function submitIQCInspectionForApproval(id: string) {
  const response = await wrap<IQCInspection>(QualityServer.submitIQCInspectionForApproval(id))
  revalidatePath('/quality/iqc')
  return response
}

export async function approveIQCInspection(id: string, data: IQCApprovalCreate) {
  const response = await wrap<IQCInspection>(QualityServer.approveIQCInspection(id, data))
  revalidatePath('/quality/iqc')
  return response
}

export async function getIQCApprovals(inspectionId: string) {
  return wrap<IQCApprovalRecord[]>(QualityServer.getIQCApprovals(inspectionId))
}

// ============ IPQC Inspection Actions (IPQC过程检验) ============

export async function getIPQCInspections(params: IPQCInspectionFilter & { page?: number; page_size?: number } = {}) {
  return wrap<IPQCInspectionListResponse>(QualityServer.getIPQCInspections(params))
}

export async function getIPQCInspection(id: string) {
  return wrap<IPQCInspection>(QualityServer.getIPQCInspection(id))
}

export async function createIPQCInspection(data: IPQCInspectionCreate) {
  const response = await wrap<IPQCInspection>(QualityServer.createIPQCInspection(data))
  revalidatePath('/quality/ipqc')
  return response
}

export async function updateIPQCInspection(id: string, data: IPQCInspectionUpdate) {
  const response = await wrap<IPQCInspection>(QualityServer.updateIPQCInspection(id, data))
  revalidatePath('/quality/ipqc')
  return response
}

export async function deleteIPQCInspection(id: string) {
  const response = await wrap<null>(QualityServer.deleteIPQCInspection(id))
  revalidatePath('/quality/ipqc')
  return response
}

export async function submitIPQCInspectionForApproval(id: string) {
  const response = await wrap<IPQCInspection>(QualityServer.submitIPQCInspectionForApproval(id))
  revalidatePath('/quality/ipqc')
  return response
}

export async function approveIPQCInspection(id: string, data: IPQCApprovalCreate) {
  const response = await wrap<IPQCInspection>(QualityServer.approveIPQCInspection(id, data))
  revalidatePath('/quality/ipqc')
  return response
}

export async function getIPQCApprovals(inspectionId: string) {
  return wrap<IPQCApprovalRecord[]>(QualityServer.getIPQCApprovals(inspectionId))
}

export async function lockIPQCBatch(id: string, reason: string) {
  const response = await wrap<IPQCInspection>(QualityServer.lockIPQCBatch(id, reason))
  revalidatePath('/quality/ipqc')
  return response
}

export async function unlockIPQCBatch(id: string) {
  const response = await wrap<IPQCInspection>(QualityServer.unlockIPQCBatch(id))
  revalidatePath('/quality/ipqc')
  return response
}

// ============ FQC Inspection Actions (FQC成品检验) ============

export async function getFQCInspections(params: FQCInspectionFilter & { page?: number; page_size?: number } = {}) {
  return wrap<FQCInspectionListResponse>(QualityServer.getFQCInspections(params))
}

export async function getFQCInspection(id: string) {
  return wrap<FQCInspection>(QualityServer.getFQCInspection(id))
}

export async function createFQCInspection(data: FQCInspectionCreate) {
  const response = await wrap<FQCInspection>(QualityServer.createFQCInspection(data))
  revalidatePath('/quality/fqc')
  return response
}

export async function updateFQCInspection(id: string, data: FQCInspectionUpdate) {
  const response = await wrap<FQCInspection>(QualityServer.updateFQCInspection(id, data))
  revalidatePath('/quality/fqc')
  return response
}

export async function deleteFQCInspection(id: string) {
  const response = await wrap<null>(QualityServer.deleteFQCInspection(id))
  revalidatePath('/quality/fqc')
  return response
}

export async function submitFQCInspectionForApproval(id: string) {
  const response = await wrap<FQCInspection>(QualityServer.submitFQCInspectionForApproval(id))
  revalidatePath('/quality/fqc')
  return response
}

export async function approveFQCInspection(id: string, data: FQCApprovalCreate) {
  const response = await wrap<FQCInspection>(QualityServer.approveFQCInspection(id, data))
  revalidatePath('/quality/fqc')
  return response
}

export async function getFQCApprovals(inspectionId: string) {
  return wrap<FQCApprovalRecord[]>(QualityServer.getFQCApprovals(inspectionId))
}

export async function applyFQCReinspection(id: string, reason: string) {
  const response = await wrap<FQCInspection>(QualityServer.applyFQCReinspection(id, reason))
  revalidatePath('/quality/fqc')
  return response
}

export async function releaseFQCInspection(id: string, releaseReason?: string) {
  const response = await wrap<FQCInspection>(QualityServer.releaseFQCInspection(id, releaseReason))
  revalidatePath('/quality/fqc')
  return response
}

export async function lockFQCBatch(id: string, reason: string) {
  const response = await wrap<FQCInspection>(QualityServer.lockFQCBatch(id, reason))
  revalidatePath('/quality/fqc')
  return response
}

export async function unlockFQCBatch(id: string) {
  const response = await wrap<FQCInspection>(QualityServer.unlockFQCBatch(id))
  revalidatePath('/quality/fqc')
  return response
}

// ============ Stability Study Actions (稳定性试验管理) ============

export async function getStabilityStudies(params: StabilityStudyFilter & { page?: number; page_size?: number } = {}) {
  return wrap<StabilityStudyListResponse>(QualityServer.getStabilityStudies(params))
}

export async function getStabilityStudy(id: string) {
  return wrap<StabilityStudy>(QualityServer.getStabilityStudy(id))
}

export async function createStabilityStudy(data: StabilityStudyCreate) {
  const response = await wrap<StabilityStudy>(QualityServer.createStabilityStudy(data))
  revalidatePath('/quality/stability')
  return response
}

export async function updateStabilityStudy(id: string, data: StabilityStudyUpdate) {
  const response = await wrap<StabilityStudy>(QualityServer.updateStabilityStudy(id, data))
  revalidatePath('/quality/stability')
  return response
}

export async function deleteStabilityStudy(id: string) {
  const response = await wrap<null>(QualityServer.deleteStabilityStudy(id))
  revalidatePath('/quality/stability')
  return response
}

export async function submitStabilityStudy(id: string) {
  const response = await wrap<StabilityStudy>(QualityServer.submitStabilityStudy(id))
  revalidatePath('/quality/stability')
  return response
}

export async function approveStabilityStudy(id: string, data: StabilityApprovalCreate) {
  const response = await wrap<StabilityStudy>(QualityServer.approveStabilityStudy(id, data))
  revalidatePath('/quality/stability')
  return response
}

export async function getStabilityStudySampleNodes(studyId: string) {
  return wrap<StabilitySampleNode[]>(QualityServer.getStabilityStudySampleNodes(studyId))
}

export async function updateStabilitySampleNode(id: string, data: StabilitySampleNodeUpdate) {
  return wrap<StabilitySampleNode>(QualityServer.updateStabilitySampleNode(id, data))
}

export async function getStabilityInspections(params: StabilityInspectionFilter & { page?: number; page_size?: number } = {}) {
  return wrap<StabilityInspectionListResponse>(QualityServer.getStabilityInspections(params))
}

export async function getStabilityInspection(id: string) {
  return wrap<StabilityInspection>(QualityServer.getStabilityInspection(id))
}

export async function createStabilityInspection(data: StabilityInspectionCreate) {
  const response = await wrap<StabilityInspection>(QualityServer.createStabilityInspection(data))
  revalidatePath('/quality/stability')
  return response
}

export async function updateStabilityInspection(id: string, data: StabilityInspectionUpdate) {
  const response = await wrap<StabilityInspection>(QualityServer.updateStabilityInspection(id, data))
  revalidatePath('/quality/stability')
  return response
}

export async function submitStabilityInspection(id: string) {
  const response = await wrap<StabilityInspection>(QualityServer.submitStabilityInspection(id))
  revalidatePath('/quality/stability')
  return response
}

export async function getStabilityTrendData(studyId: string) {
  return wrap<TrendData>(QualityServer.getStabilityTrendData(studyId))
}

// ============ AI交互日志 Actions ============

export async function getAiLogs(params: AiLogFilter & { page?: number; page_size?: number } = {}) {
  return wrap<AiLogListResponse>(QualityServer.getAiLogs(params))
}

export async function getAiLogById(id: string) {
  return wrap<AiLogItem>(QualityServer.getAiLogById(id))
}

// ============ Deviation Actions ============

export async function createDeviation(data: CreateDeviationRequest) {
  const result = await QualityServer.createDeviation(data)
  revalidatePath('/quality')
  revalidatePath('/quality/deviations')
  return result
}

export async function updateDeviation(deviationId: string, data: UpdateDeviationRequest) {
  const result = await QualityServer.updateDeviation(deviationId, data)
  revalidatePath('/quality')
  revalidatePath('/quality/deviations')
  revalidatePath(`/quality/deviations/${deviationId}`)
  return result
}

export async function deleteDeviation(deviationId: string) {
  await QualityServer.deleteDeviation(deviationId)
  revalidatePath('/quality')
  revalidatePath('/quality/deviations')
}

// ============ CAPA Actions ============

export async function createCapa(data: CreateCapaRequest) {
  const result = await QualityServer.createCapa(data)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  return result
}

export async function updateCapa(capaId: string, data: UpdateCapaRequest) {
  const result = await QualityServer.updateCapa(capaId, data)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

export async function deleteCapa(capaId: string) {
  await QualityServer.deleteCapa(capaId)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
}

// ============ Department Contact Actions ============

export async function createDepartmentContact(data: CreateDepartmentContactRequest) {
  const result = await QualityServer.createDepartmentContact(data)
  revalidatePath('/quality')
  revalidatePath('/quality/department-contacts')
  return result
}

export async function updateDepartmentContact(contactId: string, data: UpdateDepartmentContactRequest) {
  const result = await QualityServer.updateDepartmentContact(contactId, data)
  revalidatePath('/quality')
  revalidatePath('/quality/department-contacts')
  return result
}

export async function deleteDepartmentContact(contactId: string) {
  await QualityServer.deleteDepartmentContact(contactId)
  revalidatePath('/quality')
  revalidatePath('/quality/department-contacts')
}

// ============ Label Verification Server Actions ============

export async function fetchLabelVerificationsServer(params: { page: number; page_size: number }) {
  return QualityServer.fetchLabelVerifications(params)
}

// ============ Attachment Review Actions ============

export async function submitAttachmentReview(data: {
  deviation_id?: string | null
  capa_id?: string | null
  attachment_url: string
  content: string
}) {
  const response = await wrap<unknown>(QualityServer.submitAttachmentReview(data))
  revalidatePath('/quality')
  return response
}

export async function deleteAttachmentReview(reviewId: string) {
  const response = await wrap<unknown>(QualityServer.deleteAttachmentReview(reviewId))
  revalidatePath('/quality')
  return response
}

// ============ Additional CAPA Actions ============

export async function submitCapa(capaId: string) {
  const result = await QualityServer.submitCapa(capaId)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

export async function approveCapa(capaId: string, data: unknown) {
  const validated = parse(CapaApprovalSchema, data)
  const result = await QualityServer.approveCapa(capaId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

export async function resubmitCapa(capaId: string) {
  const result = await QualityServer.resubmitCapa(capaId)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

export async function addExecutionTrack(capaId: string, data: unknown) {
  const validated = parse(CapaExecutionTrackSchema, data)
  const result = await QualityServer.addExecutionTrack(capaId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

export async function deleteExecutionTrack(capaId: string, trackId: string) {
  await QualityServer.deleteExecutionTrack(capaId, trackId)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
}

export async function confirmExecution(capaId: string, data: unknown = {}) {
  const validated = parse(CapaExecutionConfirmSchema, data)
  const result = await QualityServer.confirmExecution(capaId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

export async function submitEvaluation(capaId: string, data: unknown) {
  const validated = parse(CapaEvaluationSchema, data)
  const result = await QualityServer.submitEvaluation(capaId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

export async function completeCapaPart(capaId: string, data: unknown) {
  const validated = parse(CapaPartCompleteSchema, data)
  const result = await QualityServer.completeCapaPart(capaId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

export async function confirmDeptHead(capaId: string, data: unknown) {
  const validated = parse(CapaDeptHeadConfirmSchema, data)
  const result = await QualityServer.confirmDeptHead(capaId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  revalidatePath(`/quality/capas/${capaId}`)
  return result
}

// ============ Additional Deviation Actions ============

export async function submitDeviation(deviationId: string) {
  const result = await QualityServer.submitDeviation(deviationId)
  revalidatePath('/quality')
  revalidatePath('/quality/deviations')
  revalidatePath(`/quality/deviations/${deviationId}`)
  return result
}

export async function submitInvestigation(deviationId: string, data: unknown) {
  const validated = parse(DeviationInvestigationSchema, data)
  const result = await QualityServer.submitInvestigation(deviationId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/deviations')
  revalidatePath(`/quality/deviations/${deviationId}`)
  return result
}

export async function submitReview(deviationId: string, data: unknown) {
  const validated = parse(DeviationReviewSchema, data)
  const result = await QualityServer.submitReview(deviationId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/deviations')
  revalidatePath(`/quality/deviations/${deviationId}`)
  return result
}

export async function submitFinalCode(deviationId: string, data: unknown) {
  const validated = parse(DeviationFinalCodeSchema, data)
  const result = await QualityServer.submitFinalCode(deviationId, validated)
  revalidatePath('/quality')
  revalidatePath('/quality/deviations')
  revalidatePath(`/quality/deviations/${deviationId}`)
  return result
}

export async function resubmitDeviation(deviationId: string) {
  const result = await QualityServer.resubmitDeviation(deviationId)
  revalidatePath('/quality')
  revalidatePath('/quality/deviations')
  revalidatePath(`/quality/deviations/${deviationId}`)
  return result
}

// ============ AI Config Actions ============

export async function saveAIConfig(data: unknown) {
  const validated = parse(AIConfigSaveSchema, data)
  const response = await wrap<unknown>(QualityServer.saveAIConfig(validated))
  revalidatePath('/quality/ai-config')
  return response
}

export async function resetAIConfig(data: unknown) {
  const validated = parse(AIConfigSaveSchema, data)
  const response = await wrap<unknown>(QualityServer.resetAIConfig(validated))
  revalidatePath('/quality/ai-config')
  return response
}

export async function testAIConnection(data: unknown) {
  const validated = parse(AIConfigTestSchema, data)
  return wrap<unknown>(QualityServer.testAIConnection(validated))
}

// ============ Deviation Automation Actions ============

export async function createDeviationTask(data: unknown) {
  const validated = parse(DeviationTaskCreateSchema, data)
  const response = await wrap<unknown>(QualityServer.createDeviationTask(validated))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function generateDeviationReport(taskId: string, data: unknown) {
  const validated = parse(DeviationReportGenerateSchema, data)
  const response = await wrap<unknown>(QualityServer.generateDeviationReport(taskId, validated))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function submitDeviationApproval(taskId: string, data: unknown) {
  const validated = parse(DeviationApprovalSchema, data)
  const response = await wrap<unknown>(QualityServer.submitDeviationApproval(taskId, validated))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function updateDeviationTask(taskId: string, data: unknown) {
  const validated = parse(DeviationTaskUpdateSchema, data)
  const response = await wrap<unknown>(QualityServer.updateDeviationTask(taskId, validated))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function updateDeviationTaskFields(taskId: string, data: unknown) {
  const validated = parse(DeviationTaskFieldsUpdateSchema, data)
  const response = await wrap<unknown>(QualityServer.updateDeviationTaskFields(taskId, validated))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function deleteDeviationTask(taskId: string) {
  const response = await wrap<unknown>(QualityServer.deleteDeviationTask(taskId))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function createDeviationTemplate(data: unknown) {
  const validated = parse(DeviationTemplateCreateSchema, data)
  const response = await wrap<unknown>(QualityServer.createDeviationTemplate(validated))
  revalidatePath('/quality/deviation-automation/templates')
  return response
}

export async function updateDeviationTemplate(templateId: string, data: unknown) {
  const validated = parse(DeviationTemplateCreateSchema.partial(), data)
  const response = await wrap<unknown>(QualityServer.updateDeviationTemplate(templateId, validated))
  revalidatePath('/quality/deviation-automation/templates')
  return response
}

export async function deleteDeviationTemplate(templateId: string | number) {
  const response = await wrap<unknown>(QualityServer.deleteDeviationTemplate(templateId))
  revalidatePath('/quality/deviation-automation/templates')
  return response
}

export async function createSopTemplate(data: unknown) {
  const validated = parse(SopTemplateCreateSchema, data)
  const response = await wrap<unknown>(QualityServer.createSopTemplate(validated))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function createSopFromTemplate(data: unknown) {
  const validated = parse(SopFromTemplateCreateSchema, data)
  const response = await wrap<unknown>(QualityServer.createSopFromTemplate(validated))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function updateSopTemplate(templateId: string, data: unknown) {
  const validated = parse(SopTemplateCreateSchema.partial(), data)
  const response = await wrap<unknown>(QualityServer.updateSopTemplate(templateId, validated))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function deleteSopTemplate(templateId: string) {
  const response = await wrap<unknown>(QualityServer.deleteSopTemplate(templateId))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function generateSop(data: unknown) {
  const validated = parse(SopGenerateSchema, data)
  const response = await wrap<unknown>(QualityServer.generateSop(validated))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

// ============ Additional Deviation Automation Actions ============

export async function uploadDeviationFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await wrap<unknown>(QualityServer.uploadDeviationFile(formData))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function triggerAIProcess(taskId: number) {
  const response = await wrap<unknown>(QualityServer.triggerAIProcess(taskId))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function updateAIResult(taskId: number, aiResult: unknown) {
  const response = await wrap<unknown>(QualityServer.updateAIResult(taskId, aiResult))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function generateStandard(taskId: number) {
  const response = await wrap<unknown>(QualityServer.generateStandard(taskId))
  revalidatePath('/quality/deviation-automation')
  return response
}

export async function updateDeviationTemplateStatus(id: number, isActive: boolean) {
  const response = await wrap<unknown>(QualityServer.updateDeviationTemplateStatus(id, isActive))
  revalidatePath('/quality/deviation-automation/templates')
  return response
}

export async function uploadDeviationTemplate(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await wrap<unknown>(QualityServer.uploadDeviationTemplate(formData))
  revalidatePath('/quality/deviation-automation/templates')
  return response
}

export async function deleteSopRule(id: number) {
  const response = await wrap<unknown>(QualityServer.deleteSopRule(id))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function updateSopRuleStatus(id: number | string, status: string | number) {
  const response = await wrap<unknown>(QualityServer.updateSopRuleStatus(id, status))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function createSopRule(data: unknown) {
  const validated = parse(SopRuleCreateSchema, data)
  const response = await wrap<unknown>(QualityServer.createSopRule(validated))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function uploadSopRule(ruleId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await wrap<unknown>(QualityServer.uploadSopRule(formData, ruleId))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function aiParseSopRule(ruleId: number) {
  const response = await wrap<unknown>(QualityServer.aiParseSopRule(ruleId))
  revalidatePath('/quality/deviation-automation/sop')
  return response
}

export async function uploadDeviationFileWithTask(taskId: number, file: File) {
  const formData = new FormData()
  formData.append('task_id', String(taskId))
  formData.append('file', file)
  const response = await wrap<unknown>(QualityServer.uploadDeviationFileWithTask(formData))
  revalidatePath('/quality/deviation-automation')
  return response
}
export async function uploadLcExcel(file: File): Promise<UploadLcResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await QualityServer.uploadLcExcel(formData)
  revalidatePath('/quality')
  return result
}
