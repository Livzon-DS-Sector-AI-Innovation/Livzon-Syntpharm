'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import * as safetyApi from '@/lib/api/server/safety'
import type { components } from '@/types/generated/schema'
import type {
  AccidentFormData,
  AccidentQueryParams,
  Accident,
  ConfirmCheckRequest,
  ContractorFormData,
  ContractorQueryParams,
  ContractorWorkRecordFormData,
  Contractor,
  ContractorWorkRecord,
  HazardReportFormData,
  HazardReportQueryParams,
  HazardReport,
  HazardStats,
  OperationRegulation,
  OperationRegulationFormData,
  OperationRegulationQueryParams,
  RegulationRevision,
  RegulationRevisionFormData,
  RegulationRevisionQueryParams,
  SafetyCheck,
  SafetyCheckFormData,
  SafetyCheckQueryParams,
  SafetyKnowledgeArticle,
  SafetyKnowledgeArticleFormData,
  SafetyKnowledgeArticleQueryParams,
  ParseDocumentResponse,
  DuplicateCheckRequest,
  SafetyTrainingFormData,
  SafetyTrainingQueryParams,
  SafetyTraining,
  TrainingRecord,
  SpecialOperationPermit,
  SpecialOperationPermitFormData,
  SpecialOperationPermitQueryParams,
  SpecialOperationPersonnel,
  SpecialOperationPersonnelFormData,
  SpecialOperationPersonnelQueryParams,
  SpecialOperationReport,
  SpecialOperationReportFormData,
  SpecialOperationReportQueryParams,
  SpecialOperationLedgerQueryParams,
  SpecialOperationLedgerStats,
  DailyRiskReportFormData,
  DailyRiskReportQueryParams,
  RectificationReplyRequest,
  VerifyLevelRequest,
  TrainingRecordFormData,
  ApiResponse,
  EhsChange,
  EhsChangeFormData,
  EhsChangeQueryParams,
  OhHazardMonitor,
  OhHazardMonitorFormData,
  OhHazardMonitorQueryParams,
  OhHealthExam,
  OhHealthExamFormData,
  OhHealthExamQueryParams,
  // knowledge
  GeneratePptRequest,
  KnowledgeCardContent,
  GenerateCardResponse,
  AgentUsageStats,
  BatchGenerateCardsResponse,
  GeneratePptResponse,
  PptHistoryResponse,
  GenerateSummaryResponse,
  DuplicateCheckResponse,
  VersionChainItem,
  NewVersionResponse,
  SemanticSearchResult,
  SyncKnowledgeResponse,
  HazardIdentification,
  HazardIdentificationFormData,
  HazardIdentificationQueryParams,
  HazardIdentificationStats,
  HazardIdentificationBatchCreateInput,
  HazardIdentificationBatchResponse,
  HazardLedgerStats,
  HazardLedgerExportRequest,
  HazardLedgerExportParsedFilters,
  RegulationStagesResponse,
  HazardRiskOption,
  DailyRiskReport,
  AIWorkflowConfig,
  ScheduledTask,
  ScheduledTaskLog,
  DataSourceOption,
  FeishuChat,
  HazardRevisionRecord,
  HazardRevisionArchive,
} from '@/types/safety'

// ============ SafetyCheck Actions ============

export async function getChecks(params: SafetyCheckQueryParams = {}): Promise<ApiResponse<SafetyCheck[]>> {
  const authHeaders = await getAuthHeaders()
  const result = await safetyApi.getChecks(params as Record<string, unknown>, authHeaders)
  return result as ApiResponse<SafetyCheck[]>
}

export async function getCheck(id: string): Promise<ApiResponse<SafetyCheck>> {
  const authHeaders = await getAuthHeaders()
  const result = await safetyApi.getCheck(id, authHeaders)
  return result as ApiResponse<SafetyCheck>
}

export async function createCheck(data: SafetyCheckFormData): Promise<ApiResponse<SafetyCheck>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createCheck(data, authHeaders)
  revalidatePath('/safety/check')
  return response as ApiResponse<SafetyCheck>
}

export async function updateCheck(id: string, data: Partial<SafetyCheckFormData>): Promise<ApiResponse<SafetyCheck>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateCheck(id, data, authHeaders)
  revalidatePath('/safety/check')
  return response as ApiResponse<SafetyCheck>
}
export async function submitCheck(id: string): Promise<ApiResponse<SafetyCheck>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitCheck(id, authHeaders)
  revalidatePath('/safety/check')
  return response as ApiResponse<SafetyCheck>
}

export async function reviewCheck(id: string, result: string): Promise<ApiResponse<SafetyCheck>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.reviewCheck(id, result, authHeaders)
  revalidatePath('/safety/check')
  return response as ApiResponse<SafetyCheck>
}

export async function deleteCheck(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteCheck(id, authHeaders)
  revalidatePath('/safety/check')
  return response as ApiResponse<null>
}

// ============ HazardReport Actions ============

export async function fetchHazardStats(): Promise<ApiResponse<HazardStats>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.fetchHazardStats(authHeaders) as Promise<ApiResponse<HazardStats>>
}

export async function getHazards(params: HazardReportQueryParams = {}): Promise<ApiResponse<HazardReport[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazards(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<HazardReport[]>>
}

export async function getHazard(id: string): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazard(id, authHeaders) as Promise<ApiResponse<HazardReport>>
}

/** 根据部门名称查询部门负责人 */
export async function getDepartmentLeader(departmentName: string): Promise<ApiResponse<{ leader_name: string; leader_id: string }>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDepartmentLeader(departmentName, authHeaders) as Promise<ApiResponse<{ leader_name: string; leader_id: string }>>
}

/** 根据部门名称查询分管安全员 */
export async function getDepartmentSafetyOfficer(departmentName: string): Promise<ApiResponse<{ safety_officer_name: string }>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDepartmentSafetyOfficer(departmentName, authHeaders) as Promise<ApiResponse<{ safety_officer_name: string }>>
}

export async function createHazard(data: HazardReportFormData): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazard(data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<HazardReport>
}

export async function updateHazard(id: string, data: Partial<HazardReportFormData>): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateHazard(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<HazardReport>
}

export async function startRectification(id: string): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startRectification(id, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<HazardReport>
}

export async function confirmCheck(id: string, data: ConfirmCheckRequest): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.confirmCheckApi(id, data, authHeaders)
  revalidatePath('/safety')
  return response as ApiResponse<HazardReport>
}

export async function replyRectification(id: string, data: RectificationReplyRequest): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.replyRectification(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<HazardReport>
}

export async function verifyLevel(id: string, data: VerifyLevelRequest): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.verifyLevel(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<HazardReport>
}

export async function notifyReviewer(id: string): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.notifyReviewer(id, authHeaders) as Promise<ApiResponse<HazardReport>>
}

export async function notifyRectification(id: string): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.notifyRectification(id, authHeaders) as Promise<ApiResponse<HazardReport>>
}

export async function triggerRectificationReview(id: string): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.triggerRectificationReview(id, authHeaders) as Promise<ApiResponse<HazardReport>>
}

export async function reworkRectification(id: string, data: RectificationReplyRequest): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.reworkRectification(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<HazardReport>
}

export async function deleteHazard(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteHazard(id, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<null>
}

export async function deleteHazards(ids: string[]) {
  const authHeaders = await getAuthHeaders()
  const results = await Promise.allSettled(
    ids.map((id) => safetyApi.deleteHazard(id, authHeaders))
  )
  revalidatePath('/safety/hazard')
  const succeeded = results.filter((r) => r.status === 'fulfilled').length
  const failed = results.filter((r) => r.status === 'rejected').length
  return { succeeded, failed, total: ids.length }
}

export async function uploadHazardPhoto(id: string, file: File): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.uploadHazardPhoto(`/safety/hazards/${id}/upload-photo`, file, authHeaders) as Promise<ApiResponse<HazardReport>>
}

export async function uploadRectificationPhoto(id: string, file: File): Promise<ApiResponse<HazardReport>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.uploadHazardPhoto(`/safety/hazards/${id}/upload-rectification-photo`, file, authHeaders) as Promise<ApiResponse<HazardReport>>
}

export async function runHazardAI(hazardId: string, scriptNumber: number): Promise<ApiResponse<unknown>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.runHazardAI(hazardId, scriptNumber, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<unknown>
}

// ============ Accident Actions ============

export async function getAccidents(params: AccidentQueryParams = {}): Promise<ApiResponse<Accident[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getAccidents(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<Accident[]>>
}

export async function getAccident(id: string): Promise<ApiResponse<Accident>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getAccident(id, authHeaders) as Promise<ApiResponse<Accident>>
}

export async function createAccident(data: AccidentFormData): Promise<ApiResponse<Accident>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createAccident(data, authHeaders)
  revalidatePath('/safety/accident')
  return response as ApiResponse<Accident>
}

export async function updateAccident(id: string, data: Partial<AccidentFormData>): Promise<ApiResponse<Accident>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateAccident(id, data, authHeaders)
  revalidatePath('/safety/accident')
  return response as ApiResponse<Accident>
}

export async function investigateAccident(id: string): Promise<ApiResponse<Accident>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.investigateAccident(id, authHeaders)
  revalidatePath('/safety/accident')
  return response as ApiResponse<Accident>
}

export async function resolveAccident(
  id: string,
  directCause: string,
  rootCause: string,
  handlingMeasures: string,
  correctiveActions?: string,
  investigationFindings?: string,
  investigationMethod?: string
): Promise<ApiResponse<Accident>> {
  const params = new URLSearchParams({ direct_cause: directCause, root_cause: rootCause, handling_measures: handlingMeasures })
  if (correctiveActions) params.set('corrective_actions', correctiveActions)
  if (investigationFindings) params.set('investigation_findings', investigationFindings)
  if (investigationMethod) params.set('investigation_method', investigationMethod)

  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.resolveAccident(id, params.toString(), authHeaders)
  revalidatePath('/safety/accident')
  return response as ApiResponse<Accident>
}

export async function startCapa(
  id: string,
  deadline: string,
  responsible: string
): Promise<ApiResponse<Accident>> {
  const params = new URLSearchParams({ corrective_action_deadline: deadline, corrective_action_responsible: responsible })
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startCapa(id, params.toString(), authHeaders)
  revalidatePath('/safety/accident')
  return response as ApiResponse<Accident>
}

export async function verifyCapa(id: string): Promise<ApiResponse<Accident>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.verifyCapa(id, authHeaders)
  revalidatePath('/safety/accident')
  return response as ApiResponse<Accident>
}

export async function closeAccident(id: string): Promise<ApiResponse<Accident>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.closeAccident(id, authHeaders)
  revalidatePath('/safety/accident')
  return response as ApiResponse<Accident>
}

export async function deleteAccident(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteAccident(id, authHeaders)
  revalidatePath('/safety/accident')
  return response as ApiResponse<null>
}

// ============ Contractor Actions ============

export async function getContractors(params: ContractorQueryParams = {}): Promise<ApiResponse<Contractor[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getContractors(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<Contractor[]>>
}

export async function getContractor(id: string): Promise<ApiResponse<Contractor>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getContractor(id, authHeaders) as Promise<ApiResponse<Contractor>>
}

export async function createContractor(data: ContractorFormData): Promise<ApiResponse<Contractor>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createContractor(data, authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<Contractor>
}

export async function updateContractor(id: string, data: Partial<ContractorFormData>): Promise<ApiResponse<Contractor>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateContractor(id, data, authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<Contractor>
}

export async function deleteContractor(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteContractor(id, authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<null>
}

export async function blacklistContractor(id: string): Promise<ApiResponse<Contractor>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.blacklistContractor(id, authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<Contractor>
}

export async function activateContractor(id: string): Promise<ApiResponse<Contractor>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.activateContractor(id, authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<Contractor>
}

export async function updateContractorTraining(id: string, trainingStatus: string): Promise<ApiResponse<Contractor>> {
  const params = new URLSearchParams({ training_status: trainingStatus })
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateContractorTraining(id, params.toString(), authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<Contractor>
}

export async function getWorkRecords(contractorId: string): Promise<ApiResponse<ContractorWorkRecord[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getWorkRecords(contractorId, authHeaders) as Promise<ApiResponse<ContractorWorkRecord[]>>
}

export async function createWorkRecord(contractorId: string, data: ContractorWorkRecordFormData): Promise<ApiResponse<ContractorWorkRecord>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createWorkRecord(contractorId, data, authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<ContractorWorkRecord>
}

export async function updateWorkRecord(
  contractorId: string, recordId: string, data: Partial<ContractorWorkRecordFormData>
): Promise<ApiResponse<ContractorWorkRecord>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateWorkRecord(contractorId, recordId, data, authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<ContractorWorkRecord>
}

export async function deleteWorkRecord(contractorId: string, recordId: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteWorkRecord(contractorId, recordId, authHeaders)
  revalidatePath('/safety/contractor')
  return response as ApiResponse<null>
}

export async function evaluateWorkRecord(
  contractorId: string, recordId: string, score: number, comments?: string, evaluator?: string
): Promise<ApiResponse<ContractorWorkRecord>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.evaluateWorkRecord(
    contractorId,
    recordId,
    { score, comments, evaluator },
    authHeaders
  )
  revalidatePath('/safety/contractor')
  return response as ApiResponse<ContractorWorkRecord>
}

// ============ SafetyTraining Actions ============

export async function getTrainings(params: SafetyTrainingQueryParams = {}): Promise<ApiResponse<SafetyTraining[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getTrainings(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<SafetyTraining[]>>
}

export async function getTraining(id: string): Promise<ApiResponse<SafetyTraining>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getTraining(id, authHeaders) as Promise<ApiResponse<SafetyTraining>>
}

export async function createTraining(data: SafetyTrainingFormData): Promise<ApiResponse<SafetyTraining>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createTraining(data, authHeaders)
  revalidatePath('/safety/training')
  return response as ApiResponse<SafetyTraining>
}

export async function updateTraining(id: string, data: Partial<SafetyTrainingFormData>): Promise<ApiResponse<SafetyTraining>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateTraining(id, data, authHeaders)
  revalidatePath('/safety/training')
  return response as ApiResponse<SafetyTraining>
}

export async function startTraining(id: string): Promise<ApiResponse<SafetyTraining>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startTraining(id, authHeaders)
  revalidatePath('/safety/training')
  return response as ApiResponse<SafetyTraining>
}

export async function completeTraining(id: string): Promise<ApiResponse<SafetyTraining>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.completeTraining(id, authHeaders)
  revalidatePath('/safety/training')
  return response as ApiResponse<SafetyTraining>
}

export async function deleteTraining(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteTraining(id, authHeaders)
  revalidatePath('/safety/training')
  return response as ApiResponse<null>
}

// ============ TrainingRecord Actions ============

export async function getTrainingRecords(trainingId: string): Promise<ApiResponse<TrainingRecord[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getTrainingRecords(trainingId, authHeaders) as Promise<ApiResponse<TrainingRecord[]>>
}

export async function createTrainingRecord(trainingId: string, data: TrainingRecordFormData): Promise<ApiResponse<TrainingRecord>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createTrainingRecord(trainingId, { ...data, training_id: trainingId }, authHeaders)
  revalidatePath(`/safety/training`)
  return response as ApiResponse<TrainingRecord>
}

export async function updateTrainingRecord(recordId: string, data: Partial<TrainingRecordFormData>): Promise<ApiResponse<TrainingRecord>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateTrainingRecord(recordId, data, authHeaders)
  revalidatePath('/safety/training')
  return response as ApiResponse<TrainingRecord>
}

export async function deleteTrainingRecord(recordId: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteTrainingRecord(recordId, authHeaders)
  revalidatePath('/safety/training')
  return response as ApiResponse<null>
}

// ============ Training Certificate Actions ============

export async function getTrainingCertificates(
  params: { page?: number; page_size?: number; certificate_status?: string; keyword?: string } = {}
) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getTrainingCertificates(params, authHeaders) as Promise<ApiResponse<TrainingRecord[]>>
}

export async function getExpiringCertificates() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getExpiringCertificates(authHeaders) as Promise<ApiResponse<TrainingRecord[]>>
}

// ============ HazardIdentification Actions ============

export async function getHazardIdentifications(
  params: import('@/types/safety').HazardIdentificationQueryParams = {}
) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardIdentifications(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<HazardIdentification[]>>
}

export async function getHIStats() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHIStats(authHeaders) as Promise<ApiResponse<HazardIdentificationStats>>
}

export async function getHILedgerStats(
  params: {
    department?: string
    position?: string
    risk_level?: string
    date_from?: string
    date_to?: string
  } = {}
) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHILedgerStats(params, authHeaders) as Promise<ApiResponse<HazardLedgerStats>>
}

export async function getHazardIdentification(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardIdentification(id, authHeaders) as Promise<ApiResponse<HazardIdentification>>
}

export async function createHazardIdentification(
  data: import('@/types/safety').HazardIdentificationFormData
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazardIdentification(data, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as ApiResponse<HazardIdentification>
}

// ── 批量辨识 ──

export async function getRegulationStages(regulationId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRegulationStages(regulationId, authHeaders) as Promise<ApiResponse<RegulationStagesResponse>>
}

export async function createHazardIdentificationBatch(
  data: import('@/types/safety').HazardIdentificationBatchCreateInput
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazardIdentificationBatch(data, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as ApiResponse<HazardIdentificationBatchResponse>
}

export async function updateHazardIdentification(
  id: string,
  data: Partial<import('@/types/safety').HazardIdentification>
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateHazardIdentification(id, data, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as ApiResponse<HazardIdentification>
}

export async function submitHazardIdentification(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitHazardIdentification(id, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as ApiResponse<HazardIdentification>
}

export async function runHazardScript(
  id: string,
  scriptNumber: number,
  aiOutput?: Record<string, unknown>
) {
  const body: Record<string, unknown> = { script_number: scriptNumber }
  if (aiOutput) {
    body.ai_output = aiOutput
  }
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.runHazardScript(id, body, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as ApiResponse<HazardIdentification>
}

export async function reviewHazardScript(
  id: string,
  scriptNumber: number,
  action: 'approved' | 'rejected'
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.reviewHazardScript(
    id,
    { script_number: scriptNumber, action },
    authHeaders
  )
  revalidatePath('/safety/hazard-identification')
  return response as ApiResponse<HazardIdentification>
}

export async function uploadHazardAttachment(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.uploadHazardAttachment(id, formData, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as ApiResponse<{ attachment_path: string }>
}

export async function deleteHazardIdentification(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteHazardIdentification(id, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as ApiResponse<null>
}

// ============ Hazard Identification AI Export ============

export async function parseHazardExportQuery(naturalQuery: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.parseHazardExportQuery(naturalQuery, authHeaders) as Promise<ApiResponse<HazardLedgerExportParsedFilters>>
}

export async function exportHazardLedgerPdf(
  params: import('@/types/safety').HazardLedgerExportRequest
): Promise<ApiResponse<string>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.exportHazardLedgerPdf(params, authHeaders) as Promise<ApiResponse<string>>
}

export async function getSafetyEnums() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSafetyEnums(authHeaders) as Promise<ApiResponse<Record<string, unknown>>>
}

// ============ OperationRegulation Actions ============

export async function getRegulations(params: OperationRegulationQueryParams = {}): Promise<ApiResponse<OperationRegulation[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRegulations(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<OperationRegulation[]>>
}

export async function getRegulation(id: string): Promise<ApiResponse<OperationRegulation>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRegulation(id, authHeaders) as Promise<ApiResponse<OperationRegulation>>
}

export async function createRegulation(data: OperationRegulationFormData): Promise<ApiResponse<OperationRegulation>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createRegulation(data, authHeaders)
  revalidatePath('/safety/regulation')
  return response as ApiResponse<OperationRegulation>
}

export async function updateRegulation(id: string, data: Partial<OperationRegulationFormData>): Promise<ApiResponse<OperationRegulation>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateRegulation(id, data, authHeaders)
  revalidatePath('/safety/regulation')
  return response as ApiResponse<OperationRegulation>
}

export async function deleteRegulation(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteRegulation(id, authHeaders)
  revalidatePath('/safety/regulation')
  return response as ApiResponse<null>
}

export async function uploadRegulationDocument(id: string, file: File): Promise<ApiResponse<OperationRegulation>> {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.uploadRegulationDocument(id, formData, authHeaders)
  revalidatePath('/safety/regulation')
  return response as ApiResponse<OperationRegulation>
}

// ============ SOP Generator Actions ============

export async function generateSop(file: File): Promise<ApiResponse<unknown>> {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.generateSop(formData, authHeaders)
  revalidatePath('/safety/regulation')
  return response as ApiResponse<unknown>
}

export async function updateSopContent(regulationId: string, content: string, status?: string): Promise<ApiResponse<OperationRegulation>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateSopContent(regulationId, { content, status }, authHeaders)
  revalidatePath('/safety/regulation')
  return response as ApiResponse<OperationRegulation>
}

export async function exportSopPdf(regulationId: string): Promise<ApiResponse<Blob>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.exportSopPdf(regulationId, authHeaders) as Promise<ApiResponse<Blob>>
}

export async function exportRegulationPdfBase64(regulationId: string): Promise<ApiResponse<string>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.exportRegulationPdfBase64(regulationId, authHeaders) as Promise<ApiResponse<string>>
}

export async function reviseRegulation(
  regulationId: string,
  content: string,
  revisionOpinion?: string,
  reviserName?: string,
): Promise<ApiResponse<RegulationRevision>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.reviseRegulation(regulationId, {
    content,
    revision_opinion: revisionOpinion || null,
    reviser_name: reviserName || null,
  }, authHeaders)
  revalidatePath('/safety/regulation')
  return response as ApiResponse<RegulationRevision>
}

// ============ RegulationRevision Actions ============

export async function getRevisions(params: RegulationRevisionQueryParams = {}): Promise<ApiResponse<RegulationRevision[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRevisions(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<RegulationRevision[]>>
}

export async function getRevision(id: string): Promise<ApiResponse<RegulationRevision>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRevision(id, authHeaders) as Promise<ApiResponse<RegulationRevision>>
}

export async function createRevision(data: RegulationRevisionFormData): Promise<ApiResponse<RegulationRevision>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createRevision(data, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as ApiResponse<RegulationRevision>
}

export async function updateRevision(id: string, data: Partial<RegulationRevision>): Promise<ApiResponse<RegulationRevision>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateRevision(id, data, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as ApiResponse<RegulationRevision>
}

export async function deleteRevision(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteRevision(id, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as ApiResponse<null>
}

export async function manualRevisionComplete(revisionId: string, file: File): Promise<ApiResponse<RegulationRevision>> {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.manualRevisionComplete(revisionId, formData, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as ApiResponse<RegulationRevision>
}

export async function aiRevisionGenerate(revisionId: string): Promise<ApiResponse<unknown>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.aiRevisionGenerate(revisionId, authHeaders) as Promise<ApiResponse<unknown>>
}

export async function aiRevisionConfirm(
  revisionId: string,
  generatedContent: string,
  documentName?: string
): Promise<ApiResponse<RegulationRevision>> {
  const params = new URLSearchParams({ generated_content: generatedContent })
  if (documentName) params.set('document_name', documentName)

  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.aiRevisionConfirm(revisionId, params.toString(), authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as ApiResponse<RegulationRevision>
}

export async function identifyRevisionScope(revisionId: string): Promise<ApiResponse<RegulationRevision>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.identifyRevisionScope(revisionId, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as ApiResponse<RegulationRevision>
}

// ============ SpecialOperationPersonnel Actions ============

export async function getPersonnelList(params: SpecialOperationPersonnelQueryParams = {}): Promise<ApiResponse<SpecialOperationPersonnel[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPersonnelList(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<SpecialOperationPersonnel[]>>
}

export async function getPersonnel(id: string): Promise<ApiResponse<SpecialOperationPersonnel>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPersonnel(id, authHeaders) as Promise<ApiResponse<SpecialOperationPersonnel>>
}

export async function createPersonnel(data: SpecialOperationPersonnelFormData): Promise<ApiResponse<SpecialOperationPersonnel>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createPersonnel(data, authHeaders)
  revalidatePath('/safety/special-ops-personnel')
  return response as ApiResponse<SpecialOperationPersonnel>
}

export async function updatePersonnel(id: string, data: Partial<SpecialOperationPersonnelFormData>): Promise<ApiResponse<SpecialOperationPersonnel>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updatePersonnel(id, data, authHeaders)
  revalidatePath('/safety/special-ops-personnel')
  return response as ApiResponse<SpecialOperationPersonnel>
}

export async function deletePersonnel(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deletePersonnel(id, authHeaders)
  revalidatePath('/safety/special-ops-personnel')
  return response as ApiResponse<null>
}

// ============ SpecialOperationPermit Actions ============

export async function getPermitList(params: SpecialOperationPermitQueryParams = {}): Promise<ApiResponse<SpecialOperationPermit[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPermitList(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<SpecialOperationPermit[]>>
}

export async function getPermit(id: string): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPermit(id, authHeaders) as Promise<ApiResponse<SpecialOperationPermit>>
}

export async function createPermit(data: SpecialOperationPermitFormData): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createPermit(data, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<SpecialOperationPermit>
}

export async function updatePermit(id: string, data: Partial<SpecialOperationPermitFormData>): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updatePermit(id, data, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<SpecialOperationPermit>
}

export async function deletePermit(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deletePermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<null>
}

export async function submitPermit(id: string): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitPermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<SpecialOperationPermit>
}

export async function approvePermit(id: string): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approvePermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<SpecialOperationPermit>
}

export async function rejectPermit(id: string, reason: string): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.rejectPermit(id, reason, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<SpecialOperationPermit>
}

export async function startPermit(id: string): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startPermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<SpecialOperationPermit>
}

export async function completePermit(id: string, method: string): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.completePermit(id, method, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<SpecialOperationPermit>
}

export async function archivePermit(id: string): Promise<ApiResponse<SpecialOperationPermit>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.archivePermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as ApiResponse<SpecialOperationPermit>
}

// ============ Safety Knowledge Article Actions ============

export async function getKnowledgeArticles(params: SafetyKnowledgeArticleQueryParams = {}): Promise<ApiResponse<SafetyKnowledgeArticle[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getKnowledgeArticles(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<SafetyKnowledgeArticle[]>>
}

export async function getKnowledgeArticle(id: string): Promise<ApiResponse<SafetyKnowledgeArticle>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getKnowledgeArticle(id, authHeaders) as Promise<ApiResponse<SafetyKnowledgeArticle>>
}

export async function createKnowledgeArticle(data: SafetyKnowledgeArticleFormData): Promise<ApiResponse<SafetyKnowledgeArticle>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createKnowledgeArticle(data, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<SafetyKnowledgeArticle>
}

export async function updateKnowledgeArticle(id: string, data: Partial<SafetyKnowledgeArticleFormData>): Promise<ApiResponse<SafetyKnowledgeArticle>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateKnowledgeArticle(id, data, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<SafetyKnowledgeArticle>
}

export async function deleteKnowledgeArticle(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteKnowledgeArticle(id, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<null>
}

export async function publishKnowledgeArticle(id: string): Promise<ApiResponse<SafetyKnowledgeArticle>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.publishKnowledgeArticle(id, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<SafetyKnowledgeArticle>
}

export async function archiveKnowledgeArticle(id: string): Promise<ApiResponse<SafetyKnowledgeArticle>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.archiveKnowledgeArticle(id, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<SafetyKnowledgeArticle>
}

// ── AI 智能解析 ──

export async function parseKnowledgeDocument(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  return safetyApi.parseKnowledgeDocument(formData, authHeaders) as Promise<ApiResponse<ParseDocumentResponse>>
}

export async function batchParseKnowledgeDocuments(files: File[]) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  const authHeaders = await getAuthHeaders()
  return safetyApi.batchParseKnowledgeDocuments(formData, authHeaders) as Promise<ApiResponse<ParseDocumentResponse[]>>
}

// ── 附件上传 ──

export async function uploadKnowledgeAttachment(articleId: string, file: File): Promise<ApiResponse<{ attachment_path: string; attachment_original_name: string }>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.uploadKnowledgeAttachment(articleId, file, authHeaders) as Promise<ApiResponse<{ attachment_path: string; attachment_original_name: string }>>
}

// ── 重复检测 ──

export async function checkDuplicateArticle(data: DuplicateCheckRequest): Promise<ApiResponse<DuplicateCheckResponse>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.checkDuplicateArticle(data, authHeaders) as Promise<ApiResponse<DuplicateCheckResponse>>
}

// ── 版本管理 ──

export async function getArticleVersions(id: string): Promise<ApiResponse<VersionChainItem[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getArticleVersions(id, authHeaders) as Promise<ApiResponse<VersionChainItem[]>>
}

export async function createNewArticleVersion(id: string): Promise<ApiResponse<NewVersionResponse>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createNewArticleVersion(id, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<NewVersionResponse>
}

// ── 语义搜索 ──

export async function semanticSearchArticles(q: string, page = 1, page_size = 20): Promise<ApiResponse<SemanticSearchResult[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.semanticSearchArticles({ q, page: String(page), page_size: String(page_size) }, authHeaders) as Promise<ApiResponse<SemanticSearchResult[]>>
}

// ── 知识卡片管理 ──

export async function generateKnowledgeCard(articleId: string): Promise<ApiResponse<GenerateCardResponse>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.generateKnowledgeCard(articleId, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<GenerateCardResponse>
}

export async function getAgentUsageStats(articleId: string): Promise<ApiResponse<AgentUsageStats>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getAgentUsageStats(articleId, authHeaders) as Promise<ApiResponse<AgentUsageStats>>
}

export async function batchGenerateKnowledgeCards(articleIds: string[]): Promise<ApiResponse<BatchGenerateCardsResponse>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.batchGenerateKnowledgeCards(articleIds, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<BatchGenerateCardsResponse>
}

// ── AI PPT 生成 ──

export async function generatePpt(articleId: string, data: GeneratePptRequest): Promise<ApiResponse<GeneratePptResponse>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.generatePpt(articleId, data, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<GeneratePptResponse>
}

export async function getPptHistory(articleId: string): Promise<ApiResponse<PptHistoryResponse>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPptHistory(articleId, authHeaders) as Promise<ApiResponse<PptHistoryResponse>>
}

// ── AI 摘要生成 ──

export async function generateSummary(articleId: string): Promise<ApiResponse<GenerateSummaryResponse>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.generateSummary(articleId, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<GenerateSummaryResponse>
}

// ── Bitable 同步 ──

export async function syncKnowledgeArticles(): Promise<ApiResponse<SyncKnowledgeResponse>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.syncKnowledgeArticles(authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as ApiResponse<SyncKnowledgeResponse>
}

// ==================== 八大特殊作业报备 Actions ====================

export async function getSpecialOperationReports(params?: SpecialOperationReportQueryParams): Promise<ApiResponse<SpecialOperationReport[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSpecialOperationReports((params || {}) as Record<string, unknown>, authHeaders) as Promise<ApiResponse<SpecialOperationReport[]>>
}

export async function getSpecialOperationReport(id: string): Promise<ApiResponse<SpecialOperationReport>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSpecialOperationReport(id, authHeaders) as Promise<ApiResponse<SpecialOperationReport>>
}

export async function createSpecialOperationReport(data: SpecialOperationReportFormData): Promise<ApiResponse<SpecialOperationReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createSpecialOperationReport(data, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as ApiResponse<SpecialOperationReport>
}

export async function updateSpecialOperationReport(id: string, data: Partial<SpecialOperationReportFormData>): Promise<ApiResponse<SpecialOperationReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateSpecialOperationReport(id, data, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as ApiResponse<SpecialOperationReport>
}

export async function deleteSpecialOperationReport(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteSpecialOperationReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as ApiResponse<null>
}

export async function submitSpecialOperationReport(id: string): Promise<ApiResponse<SpecialOperationReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitSpecialOperationReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as ApiResponse<SpecialOperationReport>
}

export async function approveSpecialOperationReport(id: string): Promise<ApiResponse<SpecialOperationReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approveSpecialOperationReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as ApiResponse<SpecialOperationReport>
}

export async function rejectSpecialOperationReport(id: string, reason: string): Promise<ApiResponse<SpecialOperationReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.rejectSpecialOperationReport(id, reason, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as ApiResponse<SpecialOperationReport>
}

export async function setSpecialOperationReportCritical(id: string, is_critical: boolean, reason?: string): Promise<ApiResponse<SpecialOperationReport>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.setSpecialOperationReportCritical(
    id,
    { is_critical, reason },
    authHeaders
  )
  revalidatePath('/safety/special-ops')
  return response as ApiResponse<SpecialOperationReport>
}

// ==================== 特殊作业台账 Actions ====================

export async function getSpecialOperationLedger(params?: SpecialOperationLedgerQueryParams): Promise<ApiResponse<SpecialOperationReport[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSpecialOperationLedger((params || {}) as Record<string, unknown>, authHeaders) as Promise<ApiResponse<SpecialOperationReport[]>>
}

export async function getSpecialOperationLedgerStats() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSpecialOperationLedgerStats(authHeaders) as Promise<ApiResponse<SpecialOperationLedgerStats[]>>
}

// ==================== 每日风险作业报备 Actions ====================

export async function getDailyRiskReports(params?: DailyRiskReportQueryParams) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDailyRiskReports((params || {}) as Record<string, unknown>, authHeaders) as Promise<ApiResponse<DailyRiskReport[]>>
}

export async function getDailyRiskReport(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDailyRiskReport(id, authHeaders) as Promise<ApiResponse<DailyRiskReport>>
}

export async function createDailyRiskReport(data: DailyRiskReportFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createDailyRiskReport(data, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as ApiResponse<DailyRiskReport>
}

export async function updateDailyRiskReport(id: string, data: Partial<DailyRiskReportFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateDailyRiskReport(id, data, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as ApiResponse<DailyRiskReport>
}

export async function deleteDailyRiskReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteDailyRiskReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as ApiResponse<null>
}

export async function submitDailyRiskReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitDailyRiskReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as ApiResponse<DailyRiskReport>
}

export async function approveDailyRiskReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approveDailyRiskReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as ApiResponse<DailyRiskReport>
}

export async function rejectDailyRiskReport(id: string, reason: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.rejectDailyRiskReport(id, reason, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as ApiResponse<DailyRiskReport>
}

export async function getHazardRiskOptions(params?: {
  department?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardRiskOptions(params || {}, authHeaders) as Promise<ApiResponse<HazardRiskOption[]>>
}


// ============ EHS变更管理 (MOC) ============

// CRUD
export async function getEhsChanges(params: EhsChangeQueryParams = {}): Promise<ApiResponse<EhsChange[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getEhsChanges(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<EhsChange[]>>
}

export async function getEhsChange(id: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getEhsChange(id, authHeaders) as Promise<ApiResponse<EhsChange>>
}

export async function createEhsChange(data: EhsChangeFormData): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createEhsChange(data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function updateEhsChange(id: string, data: Partial<EhsChangeFormData>): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateEhsChange(id, data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function deleteEhsChange(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<null>
}

// Workflow
export async function submitEhsChange(id: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function approveEhsChange(id: string, decision: string, comments?: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approveEhsChange(id, { decision, comments }, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function rejectEhsChange(id: string, comments?: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.rejectEhsChange(id, comments, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function startImplementationEhsChange(id: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startImplementationEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function commissionEhsChange(id: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.commissionEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function closeEhsChange(id: string, closedBy?: string, tempExpiryDate?: string, restoredDate?: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.closeEhsChange(id, {
    closed_by: closedBy,
    temp_expiry_date: tempExpiryDate,
    restored_date: restoredDate,
  }, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function cancelEhsChange(id: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.cancelEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

// JSON sub-record operations
export async function addRiskAssessment(id: string, data: Record<string, unknown>): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.addRiskAssessment(id, data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function updateActionItem(id: string, index: number, status: string): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateActionItem(id, index, status, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function updatePSSRChecklist(id: string, data: Record<string, unknown>[] | object[]): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updatePSSRChecklist(id, data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}

export async function submitVerification(id: string, data: Record<string, unknown>): Promise<ApiResponse<EhsChange>> {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitVerification(id, data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as ApiResponse<EhsChange>
}


// ==================== 职业危害因素监测 Actions ====================


export async function getOhHazardMonitors(params: OhHazardMonitorQueryParams = {}): Promise<ApiResponse<OhHazardMonitor[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getOhHazardMonitors(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<OhHazardMonitor[]>>
}

export async function getOhHazardMonitor(id: string): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getOhHazardMonitor(id, authHeaders) as Promise<ApiResponse<OhHazardMonitor>>
}

export async function createOhHazardMonitor(data: OhHazardMonitorFormData): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.createOhHazardMonitor(data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}

export async function updateOhHazardMonitor(id: string, data: Partial<OhHazardMonitorFormData>): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateOhHazardMonitor(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}

export async function deleteOhHazardMonitor(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.deleteOhHazardMonitor(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<null>
}

// Monitor Workflow
export async function startMonitor(id: string): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.startMonitor(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}

export async function completeMonitor(id: string): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.completeMonitor(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}

export async function verifyMonitor(id: string, data: { verified_by?: string; comments?: string }): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.verifyMonitor(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}

// Monitor Sub-records
export async function addDetectionResult(id: string, data: Record<string, unknown>): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.addDetectionResult(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}

export async function updateDetectionResult(id: string, index: number, data: Record<string, unknown>): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateDetectionResult(id, index, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}

export async function deleteDetectionResult(id: string, index: number): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.deleteDetectionResult(id, index, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<null>
}

export async function addMonitorAbnormality(id: string, data: Record<string, unknown>): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.addMonitorAbnormality(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}

export async function updateMonitorAbnormalityStatus(id: string, index: number, status: string): Promise<ApiResponse<OhHazardMonitor>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateMonitorAbnormalityStatus(id, index, status, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHazardMonitor>
}


// ==================== 职业健康体检 Actions ====================


export async function getOhHealthExams(params: OhHealthExamQueryParams = {}): Promise<ApiResponse<OhHealthExam[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getOhHealthExams(params as Record<string, unknown>, authHeaders) as Promise<ApiResponse<OhHealthExam[]>>
}

export async function getOhHealthExam(id: string): Promise<ApiResponse<OhHealthExam>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getOhHealthExam(id, authHeaders) as Promise<ApiResponse<OhHealthExam>>
}

export async function createOhHealthExam(data: OhHealthExamFormData): Promise<ApiResponse<OhHealthExam>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.createOhHealthExam(data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

export async function updateOhHealthExam(id: string, data: Partial<OhHealthExamFormData>): Promise<ApiResponse<OhHealthExam>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateOhHealthExam(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

export async function deleteOhHealthExam(id: string): Promise<ApiResponse<null>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.deleteOhHealthExam(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<null>
}

// Exam Workflow
export async function startExam(id: string): Promise<ApiResponse<OhHealthExam>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.startExam(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

export async function completeExam(id: string): Promise<ApiResponse<OhHealthExam>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.completeExam(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

export async function archiveExam(id: string): Promise<ApiResponse<OhHealthExam>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.archiveExam(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

// Exam Sub-records
export async function addExamItem(id: string, data: Record<string, unknown>): Promise<ApiResponse<OhHealthExam>> {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.addExamItem(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

export async function updateExamItem(id: string, index: number, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateExamItem(id, index, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

export async function deleteExamItem(id: string, index: number) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.deleteExamItem(id, index, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<null>
}

export async function setExamConclusion(id: string, conclusion: string, remarks?: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.setExamConclusion(id, { conclusion, remarks }, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

export async function addExamAbnormality(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.addExamAbnormality(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

export async function updateExamAbnormalityStatus(id: string, index: number, status: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateExamAbnormalityStatus(id, index, status, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as ApiResponse<OhHealthExam>
}

// ── Special Ops Export ──

export async function parseSpecialOpsExportQuery(query: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.parseSpecialOpsExportQuery(query, authHeaders) as Promise<ApiResponse<{ explanation?: string; filters?: Record<string, unknown> }>>
}

export async function exportSpecialOpsLedger(filters: Record<string, unknown>): Promise<Blob> {
  return safetyApi.exportSpecialOpsLedger(filters) as Promise<Blob>
}

// ============ AI Workflow Config Actions ============

export async function getAIWorkflowConfigs(params?: { page_size?: number; page?: number }) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getAIWorkflowConfigs(params || {}, authHeaders) as Promise<ApiResponse<AIWorkflowConfig[]>>
}

export async function createAIWorkflowConfig(data: components['schemas']['AIWorkflowConfigCreate']) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createAIWorkflowConfig(data, authHeaders)
  revalidatePath('/safety/ai-workflow-config')
  return response as ApiResponse<AIWorkflowConfig>
}

export async function updateAIWorkflowConfig(id: string, data: components['schemas']['AIWorkflowConfigUpdate']) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateAIWorkflowConfig(id, data, authHeaders)
  revalidatePath('/safety/ai-workflow-config')
  return response as ApiResponse<AIWorkflowConfig>
}

export async function deleteAIWorkflowConfig(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteAIWorkflowConfig(id, authHeaders)
  revalidatePath('/safety/ai-workflow-config')
  return response as ApiResponse<null>
}

// ============ Scheduled Task Actions ============

export async function getScheduledTasks(params: { page?: number; page_size?: number }) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getScheduledTasks(params, authHeaders) as Promise<ApiResponse<ScheduledTask[]>>
}

export async function getScheduledTask(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getScheduledTask(id, authHeaders) as Promise<ApiResponse<ScheduledTask>>
}

export async function createScheduledTask(data: components['schemas']['ScheduledTaskCreate']) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createScheduledTask(data, authHeaders)
  revalidatePath('/safety/scheduled-tasks')
  return response as ApiResponse<ScheduledTask>
}

export async function updateScheduledTask(id: string, data: components['schemas']['ScheduledTaskUpdate']) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateScheduledTask(id, data, authHeaders)
  revalidatePath('/safety/scheduled-tasks')
  return response as ApiResponse<ScheduledTask>
}

export async function deleteScheduledTask(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteScheduledTask(id, authHeaders)
  revalidatePath('/safety/scheduled-tasks')
  return response as ApiResponse<null>
}

export async function toggleScheduledTask(id: string, enabled: boolean) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.toggleScheduledTask(id, enabled, authHeaders) as Promise<ApiResponse<ScheduledTask>>
}

export async function runScheduledTaskNow(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.runScheduledTaskNow(id, authHeaders) as Promise<ApiResponse<Record<string, unknown>>>
}

export async function getScheduledTaskLogs(taskId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getScheduledTaskLogs(taskId, authHeaders) as Promise<ApiResponse<ScheduledTaskLog[]>>
}

export async function getDataSourceOptions() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDataSourceOptions(authHeaders) as Promise<ApiResponse<DataSourceOption[]>>
}

export async function getFeishuChats() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getFeishuChats(authHeaders) as Promise<ApiResponse<FeishuChat[]>>
}

export async function previewCard(data: components['schemas']['CardPreviewRequest']) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.previewCard(data, authHeaders) as Promise<ApiResponse<Record<string, unknown>>>
}

// ============ Hazard Legacy Actions ============

export async function completeRectification(id: string, data?: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.completeRectification(id, data || {}, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<HazardReport>
}

export async function verifyRectification(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.verifyRectification(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as ApiResponse<HazardReport>
}

// ============ Hazard Revision Actions ============

export async function getHazardRevisionRecords(params: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardRevisionRecords(params, authHeaders) as Promise<ApiResponse<HazardRevisionRecord[]>>
}

export async function createHazardRevisionRecord(data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazardRevisionRecord(data, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<HazardRevisionRecord>
}

export async function updateHazardRevisionRecord(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateHazardRevisionRecord(id, data, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<HazardRevisionRecord>
}

export async function deleteHazardRevisionRecord(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteHazardRevisionRecord(id, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<null>
}

export async function approveHazardRevision(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approveHazardRevision(id, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<HazardRevisionRecord>
}

export async function uploadHazardRevisionDocument(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.uploadHazardRevisionDocument(id, formData, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<Record<string, unknown>>
}

export async function linkRevisionToArchive(revisionId: string, archiveId: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.linkRevisionToArchive(revisionId, archiveId, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<HazardRevisionRecord>
}

export async function getHazardRevisionArchives(params: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardRevisionArchives(params, authHeaders) as Promise<ApiResponse<HazardRevisionArchive[]>>
}

export async function createHazardRevisionArchive(data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazardRevisionArchive(data, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<HazardRevisionArchive>
}

export async function updateHazardRevisionArchive(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateHazardRevisionArchive(id, data, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<HazardRevisionArchive>
}

export async function deleteHazardRevisionArchive(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteHazardRevisionArchive(id, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as ApiResponse<null>
}