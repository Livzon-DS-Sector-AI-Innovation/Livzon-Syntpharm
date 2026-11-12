'use server'

import { revalidatePath } from 'next/cache'
import type { components } from '@/types/generated/schema'
import type { ApiResponse } from '@/types/common'
import type {
  InspectionStandard,
  InspectionStandardItem,
  InspectionStandardFormData,
  StandardCopyData,
  ObsoleteData,
  ApprovalRecord,
  StandardQueryParams,
  CreateDepartmentContactRequest,
  UpdateDepartmentContactRequest,
  AiLogItem,
  AiLogListResponse,
  AiLogFilter,
  UploadLcResponse,
  DeviationAiAnalysisInput,
  DeviationAttachmentComment,
  DeviationAttachmentCommentCreateInput,
  DeviationAttachmentCommentUpdateInput,
  DeviationBatchResult,
  DeviationCrossDeptApproveInput,
  DeviationFinalCodeInput,
  DeviationInvestigationInput,
  DeviationJobState,
  DeviationLedgerBatchStatusInput,
  DeviationLedgerCreateInput,
  DeviationLedgerDetail,
  DeviationLedgerUpdateInput,
  DeviationNotifySettings,
  DeviationNotifySettingsUpdate,
  DeviationNotifyTestResult,
  DeviationResubmitInput,
  DeviationReviewInput,
  WeeklyConfirmationInput,
  WeeklyConfirmationItem,
} from '@/types/quality'

type CapaCreate = components['schemas']['CapaCreate']
type CapaUpdate = components['schemas']['CapaUpdate']

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
  parse
} from '@/lib/validation/schemas'
import * as QualityServer from '@/lib/api/server/quality'
import * as DocCheckServer from '@/lib/api/server/quality-doc-check'

/** 判断服务端函数的返回值是不是完整信封 `{code, message, data, meta}`。 */
function isEnvelope(value: unknown): value is components['schemas']['ApiResponse'] {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as { code?: unknown }).code === 'number' &&
    'data' in value
  )
}

/**
 * 统一归一服务端返回值：`lib/api/server/quality.ts` 里有的函数返回完整信封
 * （直接 `apiFetch`），有的已解包（`unwrapResponse`）。此前一律塞进 `data`，
 * 于是页面把 `{code,data,meta}` 当列表用，传给 antd Table 的 `dataSource`
 * 不是数组 → 整页崩（`xxx.some is not a function`）。
 *
 * 除 `data` 需要按调用方的类型参数收窄外，其余字段全部由契约类型推导。
 */
async function wrap<T>(promise: Promise<unknown>): Promise<ApiResponse<T>> {
  const raw = await promise
  if (isEnvelope(raw)) {
    return {
      code: raw.code,
      message: raw.message,
      data: raw.data as T,
      meta: raw.meta,
    }
  }
  return { code: 200, message: 'ok', data: raw as T }
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

export async function getAiLogs(params: AiLogFilter = {}) {
  return wrap<AiLogListResponse>(QualityServer.getAiLogs(params))
}

export async function getAiLogById(id: string) {
  return wrap<AiLogItem>(QualityServer.getAiLogById(id))
}

// ============ CAPA Actions ============

export async function createCapa(data: CapaCreate) {
  const result = await QualityServer.createCapa(data)
  revalidatePath('/quality')
  revalidatePath('/quality/capas')
  return result
}

export async function updateCapa(capaId: string, data: CapaUpdate) {
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

export async function uploadLcExcel(file: File): Promise<UploadLcResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await QualityServer.uploadLcExcel(formData)
  revalidatePath('/quality')
  return result
}

// ============ Doc Check Actions ============

/** 启动文档 AI 预审 */
export async function startDocCheck(fileId: string, checkConfig: unknown) {
  const response = await wrap<{ task_id: string }>(DocCheckServer.startDocCheck(fileId, checkConfig))
  revalidatePath('/quality/doc-check')
  return response
}

/** 确认文档预审通过 */
export async function confirmDocCheckRecord(recordId: string) {
  const response = await wrap<null>(DocCheckServer.confirmDocCheckRecord(recordId))
  revalidatePath('/quality/doc-check')
  return response
}

/** 更新预审问题的处理结果 */
export async function updateDocCheckProblem(problemId: string, payload: components['schemas']['ProblemUpdate']) {
  const response = await wrap<null>(DocCheckServer.updateDocCheckProblem(problemId, payload))
  revalidatePath('/quality/doc-check')
  return response
}

// ============ 偏差台账 Actions ============

export interface DeviationLedgerActionResult {
  code: number
  message: string
  data: DeviationLedgerDetail | null
}

/** 新建偏差：成功后刷新看盘与台账两个页面数据 */
export async function createDeviationLedger(
  input: DeviationLedgerCreateInput,
): Promise<DeviationLedgerActionResult> {
  try {
    const response = await wrap<DeviationLedgerDetail>(QualityServer.fetchCreateDeviationLedger(input))
    revalidatePath('/quality/deviation')
    revalidatePath('/quality/deviation/ledger')
    return { code: response.code, message: response.message, data: response.data }
  } catch (error) {
    // 原始错误只进服务端日志，避免把内部细节透给浏览器
    console.error('偏差创建失败', error)
    return {
      code: 500,
      message: '偏差创建失败，请稍后重试',
      data: null,
    }
  }
}

/** 所有偏差详情写操作的统一收口：成功刷新详情 / 台账 / 看盘三处缓存。 */
async function runDeviationAction(
  id: string,
  call: () => Promise<DeviationLedgerDetail>,
  fallbackMessage: string,
): Promise<DeviationLedgerActionResult> {
  try {
    const data = await call()
    revalidatePath('/quality/deviation')
    revalidatePath('/quality/deviation/ledger')
    revalidatePath(`/quality/deviation/${id}`)
    return { code: 200, message: '操作成功', data }
  } catch (error) {
    console.error(fallbackMessage, error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : fallbackMessage,
      data: null,
    }
  }
}

export async function updateDeviationLedger(
  id: string,
  input: DeviationLedgerUpdateInput,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(id, () => QualityServer.fetchUpdateDeviationLedger(id, input), '偏差信息保存失败')
}

export interface DeviationJobActionResult {
  code: number
  message: string
  data: DeviationJobState | null
}

/** 提交 AI 分析任务：大模型耗时不可控，接口只返回 job_id，结果由轮询获取 */
export async function startDeviationAiAnalysis(id: string): Promise<DeviationJobActionResult> {
  try {
    const data = await QualityServer.fetchStartDeviationAiAnalysis(id)
    return { code: 200, message: '任务已提交', data }
  } catch (error) {
    console.error('AI 分析提交失败', error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : 'AI 分析提交失败',
      data: null,
    }
  }
}

/** 轮询 AI 分析任务状态 */
export async function getDeviationJobStatus(jobId: string): Promise<DeviationJobActionResult> {
  try {
    const data = await QualityServer.fetchDeviationJobStatus(jobId)
    return { code: 200, message: 'ok', data }
  } catch (error) {
    console.error('查询 AI 分析任务状态失败', error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : '查询任务状态失败',
      data: null,
    }
  }
}

export async function completeDeviationAiAnalysis(
  id: string,
  input: DeviationAiAnalysisInput,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(
    id,
    () => QualityServer.fetchCompleteDeviationAiAnalysis(id, input),
    'AI 分析保存失败',
  )
}

export async function submitDeviationInvestigation(
  id: string,
  input: DeviationInvestigationInput,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(
    id,
    () => QualityServer.fetchSubmitDeviationInvestigation(id, input),
    '调查报告提交失败',
  )
}

/** 审核阶段追加调查记录：只追加记录，不推进流程状态 */
export async function appendDeviationInvestigationRecord(
  id: string,
  input: DeviationInvestigationInput,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(
    id,
    () => QualityServer.fetchAppendDeviationInvestigationRecord(id, input),
    '调查记录追加失败',
  )
}

export async function approveDeviationCrossDeptRow(
  id: string,
  input: DeviationCrossDeptApproveInput,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(id, () => QualityServer.fetchApproveDeviationCrossDeptRow(id, input), '跨部门逐行审批失败')
}

export async function reviewDeviation(
  id: string,
  input: DeviationReviewInput,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(id, () => QualityServer.fetchReviewDeviationLedger(id, input), '审核操作失败')
}

export async function resubmitDeviation(
  id: string,
  input: DeviationResubmitInput,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(id, () => QualityServer.fetchResubmitDeviationLedger(id, input), '重新提交失败')
}

export async function submitDeviationFinalCode(
  id: string,
  input: DeviationFinalCodeInput,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(id, () => QualityServer.fetchSubmitDeviationFinalCode(id, input), '最终编号提交失败')
}

export async function uploadDeviationAttachment(
  id: string,
  formData: FormData,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(id, () => QualityServer.fetchUploadDeviationAttachment(id, formData), '附件上传失败')
}

export async function deleteDeviationAttachment(
  id: string,
  fileId: string,
): Promise<DeviationLedgerActionResult> {
  return runDeviationAction(
    id,
    () => QualityServer.fetchDeleteDeviationAttachment(id, fileId),
    '附件删除失败',
  )
}

/** 批注写操作独立收敛：返回批注对象，不复用要求返回台账详情的 runDeviationAction */
async function runAttachmentCommentAction<T>(
  id: string,
  call: () => Promise<T>,
  fallbackMessage: string,
): Promise<ApiResponse<T | null>> {
  try {
    const data = await call()
    revalidatePath(`/quality/deviation/${id}`)
    return { code: 200, message: '操作成功', data }
  } catch (error) {
    console.error(fallbackMessage, error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : fallbackMessage,
      data: null,
    }
  }
}

export async function createDeviationAttachmentComment(
  id: string,
  fileId: string,
  input: DeviationAttachmentCommentCreateInput,
): Promise<ApiResponse<DeviationAttachmentComment | null>> {
  return runAttachmentCommentAction(
    id,
    () => QualityServer.fetchCreateDeviationAttachmentComment(id, fileId, input),
    '批注提交失败',
  )
}

export async function updateDeviationAttachmentComment(
  id: string,
  fileId: string,
  commentId: string,
  input: DeviationAttachmentCommentUpdateInput,
): Promise<ApiResponse<DeviationAttachmentComment | null>> {
  return runAttachmentCommentAction(
    id,
    () => QualityServer.fetchUpdateDeviationAttachmentComment(id, fileId, commentId, input),
    '批注更新失败',
  )
}

export async function deleteDeviationAttachmentComment(
  id: string,
  fileId: string,
  commentId: string,
): Promise<ApiResponse<{ id: string; deleted: boolean } | null>> {
  return runAttachmentCommentAction(
    id,
    () => QualityServer.fetchDeleteDeviationAttachmentComment(id, fileId, commentId),
    '批注删除失败',
  )
}

export async function batchUpdateDeviationStatus(
  input: DeviationLedgerBatchStatusInput,
): Promise<ApiResponse<DeviationBatchResult | null>> {
  try {
    const data = await QualityServer.fetchBatchUpdateDeviationStatus(input)
    revalidatePath('/quality/deviation')
    revalidatePath('/quality/deviation/ledger')
    return { code: 200, message: '批量更新成功', data }
  } catch (error) {
    console.error('偏差批量更新失败', error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : '批量更新失败',
      data: null,
    }
  }
}

export async function deleteDeviationLedger(id: string): Promise<ApiResponse<null>> {
  try {
    await QualityServer.fetchRemoveDeviationLedger(id)
    revalidatePath('/quality/deviation')
    revalidatePath('/quality/deviation/ledger')
    return { code: 200, message: '删除成功', data: null }
  } catch (error) {
    console.error('偏差删除失败', error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : '删除失败',
      data: null,
    }
  }
}

export async function updateDeviationNotifySettingsAction(
  input: DeviationNotifySettingsUpdate,
): Promise<ApiResponse<DeviationNotifySettings | null>> {
  try {
    const data = await QualityServer.fetchUpdateDeviationNotifySettings(input)
    revalidatePath('/quality/department-contacts')
    return { code: 200, message: '通知设置已保存', data }
  } catch (error) {
    console.error('通知设置保存失败', error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : '通知设置保存失败',
      data: null,
    }
  }
}

export async function sendDeviationNotifyTestAction(): Promise<
  ApiResponse<DeviationNotifyTestResult | null>
> {
  try {
    const data = await QualityServer.fetchSendDeviationNotifyTest()
    return { code: 200, message: data.message, data }
  } catch (error) {
    console.error('偏差通知测试失败', error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : '偏差通知测试失败',
      data: null,
    }
  }
}

export async function submitWeeklyConfirmation(
  input: WeeklyConfirmationInput,
): Promise<ApiResponse<WeeklyConfirmationItem | null>> {
  try {
    const data = await QualityServer.upsertWeeklyConfirmation(input)
    revalidatePath('/quality/deviation')
    revalidatePath('/quality/department-contacts')
    return { code: 200, message: '确认成功', data }
  } catch (error) {
    console.error('部门周确认提交失败', error)
    return {
      code: 500,
      message: error instanceof Error ? error.message : '确认失败',
      data: null,
    }
  }
}
