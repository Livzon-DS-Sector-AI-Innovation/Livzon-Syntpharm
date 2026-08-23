'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import * as safetyApi from '@/lib/api/server/safety'
import type { components } from '@/types/generated/schema'
import type {
  AccidentFormData,
  AccidentQueryParams,
  ConfirmCheckRequest,
  ContractorFormData,
  ContractorQueryParams,
  ContractorWorkRecordFormData,
  HazardReportFormData,
  HazardReportQueryParams,
  OperationRegulationFormData,
  OperationRegulationQueryParams,
  RegulationRevision,
  RegulationRevisionFormData,
  RegulationRevisionQueryParams,
  SafetyCheckFormData,
  SafetyCheckQueryParams,
  SafetyKnowledgeArticleFormData,
  SafetyKnowledgeArticleQueryParams,
  ParseDocumentResponse,
  DuplicateCheckRequest,
  SafetyTrainingFormData,
  SafetyTrainingQueryParams,
  SpecialOperationPermitFormData,
  SpecialOperationPermitQueryParams,
  SpecialOperationPersonnelFormData,
  SpecialOperationPersonnelQueryParams,
  SpecialOperationReportFormData,
  SpecialOperationReportQueryParams,
  SpecialOperationLedgerQueryParams,
  DailyRiskReportFormData,
  DailyRiskReportQueryParams,
  RectificationReplyRequest,
  VerifyLevelRequest,
  TrainingRecordFormData,
  ApiResponse,
  EhsChangeFormData,
  EhsChangeQueryParams,
  OhHazardMonitorFormData,
  OhHazardMonitorQueryParams,
  OhHealthExamFormData,
  OhHealthExamQueryParams,
  // knowledge
  GeneratePptRequest,
} from '@/types/safety'

// ============ SafetyCheck Actions ============

export async function getChecks(params: SafetyCheckQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getChecks(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getCheck(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getCheck(id, authHeaders) as any as any
}

export async function createCheck(data: SafetyCheckFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createCheck(data, authHeaders)
  revalidatePath('/safety/check')
  return response as any
}

export async function updateCheck(id: string, data: Partial<SafetyCheckFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateCheck(id, data, authHeaders)
  revalidatePath('/safety/check')
  return response as any
}

export async function submitCheck(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitCheck(id, authHeaders)
  revalidatePath('/safety/check')
  return response as any
}

export async function reviewCheck(id: string, result: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.reviewCheck(id, result, authHeaders)
  revalidatePath('/safety/check')
  return response as any
}

export async function deleteCheck(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteCheck(id, authHeaders)
  revalidatePath('/safety/check')
  return response as any
}

// ============ HazardReport Actions ============

export async function fetchHazardStats() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.fetchHazardStats(authHeaders) as any as any
}

export async function getHazards(params: HazardReportQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazards(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getHazard(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazard(id, authHeaders) as any as any
}

/** 根据部门名称查询部门负责人 */
export async function getDepartmentLeader(departmentName: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDepartmentLeader(departmentName, authHeaders) as any as any
}

/** 根据部门名称查询分管安全员 */
export async function getDepartmentSafetyOfficer(departmentName: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDepartmentSafetyOfficer(departmentName, authHeaders) as any as any
}

export async function createHazard(data: HazardReportFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazard(data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

export async function updateHazard(id: string, data: Partial<HazardReportFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateHazard(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

export async function startRectification(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startRectification(id, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

export async function confirmCheck(id: string, data: ConfirmCheckRequest) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.confirmCheckApi(id, data, authHeaders)
  revalidatePath('/safety')
  return response as any
}

export async function replyRectification(id: string, data: RectificationReplyRequest) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.replyRectification(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

export async function verifyLevel(id: string, data: VerifyLevelRequest) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.verifyLevel(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

export async function notifyReviewer(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.notifyReviewer(id, authHeaders) as any as any
}

export async function notifyRectification(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.notifyRectification(id, authHeaders) as any as any
}

export async function triggerRectificationReview(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.triggerRectificationReview(id, authHeaders) as any as any
}

export async function reworkRectification(id: string, data: RectificationReplyRequest) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.reworkRectification(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

export async function deleteHazard(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteHazard(id, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
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

export async function uploadHazardPhoto(id: string, file: File) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.uploadHazardPhoto(`/safety/hazards/${id}/upload-photo`, file, authHeaders) as any as any
}

export async function uploadRectificationPhoto(id: string, file: File) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.uploadHazardPhoto(`/safety/hazards/${id}/upload-rectification-photo`, file, authHeaders) as any as any
}

export async function runHazardAI(hazardId: string, scriptNumber: number) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.runHazardAI(hazardId, scriptNumber, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

// ============ Accident Actions ============

export async function getAccidents(params: AccidentQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getAccidents(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getAccident(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getAccident(id, authHeaders) as any as any
}

export async function createAccident(data: AccidentFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createAccident(data, authHeaders)
  revalidatePath('/safety/accident')
  return response as any
}

export async function updateAccident(id: string, data: Partial<AccidentFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateAccident(id, data, authHeaders)
  revalidatePath('/safety/accident')
  return response as any
}

export async function investigateAccident(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.investigateAccident(id, authHeaders)
  revalidatePath('/safety/accident')
  return response as any
}

export async function resolveAccident(
  id: string,
  directCause: string,
  rootCause: string,
  handlingMeasures: string,
  correctiveActions?: string,
  investigationFindings?: string,
  investigationMethod?: string
) {
  const params = new URLSearchParams({ direct_cause: directCause, root_cause: rootCause, handling_measures: handlingMeasures })
  if (correctiveActions) params.set('corrective_actions', correctiveActions)
  if (investigationFindings) params.set('investigation_findings', investigationFindings)
  if (investigationMethod) params.set('investigation_method', investigationMethod)

  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.resolveAccident(id, params.toString(), authHeaders)
  revalidatePath('/safety/accident')
  return response as any
}

export async function startCapa(
  id: string,
  deadline: string,
  responsible: string
) {
  const params = new URLSearchParams({ corrective_action_deadline: deadline, corrective_action_responsible: responsible })
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startCapa(id, params.toString(), authHeaders)
  revalidatePath('/safety/accident')
  return response as any
}

export async function verifyCapa(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.verifyCapa(id, authHeaders)
  revalidatePath('/safety/accident')
  return response as any
}

export async function closeAccident(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.closeAccident(id, authHeaders)
  revalidatePath('/safety/accident')
  return response as any
}

export async function deleteAccident(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteAccident(id, authHeaders)
  revalidatePath('/safety/accident')
  return response as any
}

// ============ Contractor Actions ============

export async function getContractors(params: ContractorQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getContractors(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getContractor(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getContractor(id, authHeaders) as any as any
}

export async function createContractor(data: ContractorFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createContractor(data, authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function updateContractor(id: string, data: Partial<ContractorFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateContractor(id, data, authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function deleteContractor(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteContractor(id, authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function blacklistContractor(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.blacklistContractor(id, authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function activateContractor(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.activateContractor(id, authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function updateContractorTraining(id: string, trainingStatus: string) {
  const params = new URLSearchParams({ training_status: trainingStatus })
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateContractorTraining(id, params.toString(), authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function getWorkRecords(contractorId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getWorkRecords(contractorId, authHeaders) as any as any
}

export async function createWorkRecord(contractorId: string, data: ContractorWorkRecordFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createWorkRecord(contractorId, data, authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function updateWorkRecord(
  contractorId: string, recordId: string, data: Partial<ContractorWorkRecordFormData>
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateWorkRecord(contractorId, recordId, data, authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function deleteWorkRecord(contractorId: string, recordId: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteWorkRecord(contractorId, recordId, authHeaders)
  revalidatePath('/safety/contractor')
  return response as any
}

export async function evaluateWorkRecord(
  contractorId: string, recordId: string, score: number, comments?: string, evaluator?: string
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.evaluateWorkRecord(
    contractorId,
    recordId,
    { score, comments, evaluator },
    authHeaders
  )
  revalidatePath('/safety/contractor')
  return response as any
}

// ============ SafetyTraining Actions ============

export async function getTrainings(params: SafetyTrainingQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getTrainings(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getTraining(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getTraining(id, authHeaders) as any as any
}

export async function createTraining(data: SafetyTrainingFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createTraining(data, authHeaders)
  revalidatePath('/safety/training')
  return response as any
}

export async function updateTraining(id: string, data: Partial<SafetyTrainingFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateTraining(id, data, authHeaders)
  revalidatePath('/safety/training')
  return response as any
}

export async function startTraining(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startTraining(id, authHeaders)
  revalidatePath('/safety/training')
  return response as any
}

export async function completeTraining(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.completeTraining(id, authHeaders)
  revalidatePath('/safety/training')
  return response as any
}

export async function deleteTraining(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteTraining(id, authHeaders)
  revalidatePath('/safety/training')
  return response as any
}

// ============ TrainingRecord Actions ============

export async function getTrainingRecords(trainingId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getTrainingRecords(trainingId, authHeaders) as any as any
}

export async function createTrainingRecord(trainingId: string, data: TrainingRecordFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createTrainingRecord(trainingId, { ...data, training_id: trainingId }, authHeaders)
  revalidatePath(`/safety/training`)
  return response as any
}

export async function updateTrainingRecord(recordId: string, data: Partial<TrainingRecordFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateTrainingRecord(recordId, data, authHeaders)
  revalidatePath('/safety/training')
  return response as any
}

export async function deleteTrainingRecord(recordId: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteTrainingRecord(recordId, authHeaders)
  revalidatePath('/safety/training')
  return response as any
}

// ============ Training Certificate Actions ============

export async function getTrainingCertificates(
  params: { page?: number; page_size?: number; certificate_status?: string; keyword?: string } = {}
) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getTrainingCertificates(params, authHeaders) as any as any
}

export async function getExpiringCertificates() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getExpiringCertificates(authHeaders) as any as any
}

// ============ HazardIdentification Actions ============

export async function getHazardIdentifications(
  params: import('@/types/safety').HazardIdentificationQueryParams = {}
) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardIdentifications(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getHIStats() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHIStats(authHeaders) as any as any
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
  return safetyApi.getHILedgerStats(params, authHeaders) as any as any
}

export async function getHazardIdentification(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardIdentification(id, authHeaders) as any as any
}

export async function createHazardIdentification(
  data: import('@/types/safety').HazardIdentificationFormData
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazardIdentification(data, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as any
}

// ── 批量辨识 ──

export async function getRegulationStages(regulationId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRegulationStages(regulationId, authHeaders) as any as any
}

export async function createHazardIdentificationBatch(
  data: import('@/types/safety').HazardIdentificationBatchCreateInput
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazardIdentificationBatch(data, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as any
}

export async function updateHazardIdentification(
  id: string,
  data: Partial<import('@/types/safety').HazardIdentification>
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateHazardIdentification(id, data, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as any
}

export async function submitHazardIdentification(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitHazardIdentification(id, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as any
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
  return response as any
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
  return response as any
}

export async function uploadHazardAttachment(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.uploadHazardAttachment(id, formData, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as any
}

export async function deleteHazardIdentification(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteHazardIdentification(id, authHeaders)
  revalidatePath('/safety/hazard-identification')
  return response as any
}

// ============ Hazard Identification AI Export ============

export async function parseHazardExportQuery(naturalQuery: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.parseHazardExportQuery(naturalQuery, authHeaders) as any as any
}

export async function exportHazardLedgerPdf(
  params: import('@/types/safety').HazardLedgerExportRequest
): Promise<ApiResponse<string>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.exportHazardLedgerPdf(params, authHeaders) as any as any
}

export async function getSafetyEnums() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSafetyEnums(authHeaders) as any as any
}

// ============ OperationRegulation Actions ============

export async function getRegulations(params: OperationRegulationQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRegulations(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getRegulation(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRegulation(id, authHeaders) as any as any
}

export async function createRegulation(data: OperationRegulationFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createRegulation(data, authHeaders)
  revalidatePath('/safety/regulation')
  return response as any
}

export async function updateRegulation(id: string, data: Partial<OperationRegulationFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateRegulation(id, data, authHeaders)
  revalidatePath('/safety/regulation')
  return response as any
}

export async function deleteRegulation(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteRegulation(id, authHeaders)
  revalidatePath('/safety/regulation')
  return response as any
}

export async function uploadRegulationDocument(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.uploadRegulationDocument(id, formData, authHeaders)
  revalidatePath('/safety/regulation')
  return response as any
}

// ============ SOP Generator Actions ============

export async function generateSop(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.generateSop(formData, authHeaders)
  revalidatePath('/safety/regulation')
  return response as any
}

export async function updateSopContent(regulationId: string, content: string, status?: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateSopContent(regulationId, { content, status }, authHeaders)
  revalidatePath('/safety/regulation')
  return response as any
}

export async function exportSopPdf(regulationId: string): Promise<ApiResponse<Blob>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.exportSopPdf(regulationId, authHeaders) as any as any as Promise<ApiResponse<Blob>>
}

export async function exportRegulationPdfBase64(regulationId: string): Promise<ApiResponse<string>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.exportRegulationPdfBase64(regulationId, authHeaders) as any as any
}

export async function reviseRegulation(
  regulationId: string,
  content: string,
  revisionOpinion?: string,
  reviserName?: string,
) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.reviseRegulation(regulationId, {
    content,
    revision_opinion: revisionOpinion || null,
    reviser_name: reviserName || null,
  }, authHeaders)
  revalidatePath('/safety/regulation')
  return response as any
}

// ============ RegulationRevision Actions ============

export async function getRevisions(params: RegulationRevisionQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRevisions(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getRevision(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getRevision(id, authHeaders) as any as any
}

export async function createRevision(data: RegulationRevisionFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createRevision(data, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as any
}

export async function updateRevision(id: string, data: Partial<RegulationRevision>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateRevision(id, data, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as any
}

export async function deleteRevision(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteRevision(id, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as any
}

export async function manualRevisionComplete(revisionId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.manualRevisionComplete(revisionId, formData, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as any
}

export async function aiRevisionGenerate(revisionId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.aiRevisionGenerate(revisionId, authHeaders) as any as any
}

export async function aiRevisionConfirm(
  revisionId: string,
  generatedContent: string,
  documentName?: string
) {
  const params = new URLSearchParams({ generated_content: generatedContent })
  if (documentName) params.set('document_name', documentName)

  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.aiRevisionConfirm(revisionId, params.toString(), authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as any
}

export async function identifyRevisionScope(revisionId: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.identifyRevisionScope(revisionId, authHeaders)
  revalidatePath('/safety/regulation-revision')
  return response as any
}

// ============ SpecialOperationPersonnel Actions ============

export async function getPersonnelList(params: SpecialOperationPersonnelQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPersonnelList(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getPersonnel(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPersonnel(id, authHeaders) as any as any
}

export async function createPersonnel(data: SpecialOperationPersonnelFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createPersonnel(data, authHeaders)
  revalidatePath('/safety/special-ops-personnel')
  return response as any
}

export async function updatePersonnel(id: string, data: Partial<SpecialOperationPersonnelFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updatePersonnel(id, data, authHeaders)
  revalidatePath('/safety/special-ops-personnel')
  return response as any
}

export async function deletePersonnel(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deletePersonnel(id, authHeaders)
  revalidatePath('/safety/special-ops-personnel')
  return response as any
}

// ============ SpecialOperationPermit Actions ============

export async function getPermitList(params: SpecialOperationPermitQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPermitList(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getPermit(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPermit(id, authHeaders) as any as any
}

export async function createPermit(data: SpecialOperationPermitFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createPermit(data, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

export async function updatePermit(id: string, data: Partial<SpecialOperationPermitFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updatePermit(id, data, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

export async function deletePermit(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deletePermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

export async function submitPermit(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitPermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

export async function approvePermit(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approvePermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

export async function rejectPermit(id: string, reason: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.rejectPermit(id, reason, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

export async function startPermit(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startPermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

export async function completePermit(id: string, method: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.completePermit(id, method, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

export async function archivePermit(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.archivePermit(id, authHeaders)
  revalidatePath('/safety/special-ops-permits')
  return response as any
}

// ============ Safety Knowledge Article Actions ============

export async function getKnowledgeArticles(params: SafetyKnowledgeArticleQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getKnowledgeArticles(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getKnowledgeArticle(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getKnowledgeArticle(id, authHeaders) as any as any
}

export async function createKnowledgeArticle(data: SafetyKnowledgeArticleFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createKnowledgeArticle(data, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

export async function updateKnowledgeArticle(id: string, data: Partial<SafetyKnowledgeArticleFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateKnowledgeArticle(id, data, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

export async function deleteKnowledgeArticle(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteKnowledgeArticle(id, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

export async function publishKnowledgeArticle(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.publishKnowledgeArticle(id, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

export async function archiveKnowledgeArticle(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.archiveKnowledgeArticle(id, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

// ── AI 智能解析 ──

export async function parseKnowledgeDocument(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  return safetyApi.parseKnowledgeDocument(formData, authHeaders) as any as any as Promise<ApiResponse<ParseDocumentResponse>>
}

export async function batchParseKnowledgeDocuments(files: File[]) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  const authHeaders = await getAuthHeaders()
  return safetyApi.batchParseKnowledgeDocuments(formData, authHeaders) as any as any as Promise<ApiResponse<ParseDocumentResponse[]>>
}

// ── 附件上传 ──

export async function uploadKnowledgeAttachment(articleId: string, file: File) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.uploadKnowledgeAttachment(articleId, file, authHeaders) as any as any
}

// ── 重复检测 ──

export async function checkDuplicateArticle(data: DuplicateCheckRequest) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.checkDuplicateArticle(data, authHeaders) as any as any
}

// ── 版本管理 ──

export async function getArticleVersions(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getArticleVersions(id, authHeaders) as any as any
}

export async function createNewArticleVersion(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createNewArticleVersion(id, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

// ── 语义搜索 ──

export async function semanticSearchArticles(q: string, page = 1, page_size = 20) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.semanticSearchArticles({ q, page: String(page), page_size: String(page_size) }, authHeaders) as any as any
}

// ── 知识卡片管理 ──

export async function generateKnowledgeCard(articleId: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.generateKnowledgeCard(articleId, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

export async function getAgentUsageStats(articleId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getAgentUsageStats(articleId, authHeaders) as any as any
}

export async function batchGenerateKnowledgeCards(articleIds: string[]) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.batchGenerateKnowledgeCards(articleIds, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

// ── AI PPT 生成 ──

export async function generatePpt(articleId: string, data: GeneratePptRequest) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.generatePpt(articleId, data, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

export async function getPptHistory(articleId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getPptHistory(articleId, authHeaders) as any as any
}

// ── AI 摘要生成 ──

export async function generateSummary(articleId: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.generateSummary(articleId, authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

// ── Bitable 同步 ──

export async function syncKnowledgeArticles() {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.syncKnowledgeArticles(authHeaders)
  revalidatePath('/safety/knowledge-base')
  return response as any
}

// ==================== 八大特殊作业报备 Actions ====================

export async function getSpecialOperationReports(params?: SpecialOperationReportQueryParams) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSpecialOperationReports((params || {}) as Record<string, unknown>, authHeaders) as any as any
}

export async function getSpecialOperationReport(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSpecialOperationReport(id, authHeaders) as any as any
}

export async function createSpecialOperationReport(data: SpecialOperationReportFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createSpecialOperationReport(data, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as any
}

export async function updateSpecialOperationReport(id: string, data: Partial<SpecialOperationReportFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateSpecialOperationReport(id, data, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as any
}

export async function deleteSpecialOperationReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteSpecialOperationReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as any
}

export async function submitSpecialOperationReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitSpecialOperationReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as any
}

export async function approveSpecialOperationReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approveSpecialOperationReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as any
}

export async function rejectSpecialOperationReport(id: string, reason: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.rejectSpecialOperationReport(id, reason, authHeaders)
  revalidatePath('/safety/risk-reporting')
  revalidatePath('/safety/special-ops')
  return response as any
}

export async function setSpecialOperationReportCritical(id: string, is_critical: boolean, reason?: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.setSpecialOperationReportCritical(
    id,
    { is_critical, reason },
    authHeaders
  )
  revalidatePath('/safety/special-ops')
  return response as any
}

// ==================== 特殊作业台账 Actions ====================

export async function getSpecialOperationLedger(params?: SpecialOperationLedgerQueryParams) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSpecialOperationLedger((params || {}) as Record<string, unknown>, authHeaders) as any as any
}

export async function getSpecialOperationLedgerStats() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getSpecialOperationLedgerStats(authHeaders) as any as any
}

// ==================== 每日风险作业报备 Actions ====================

export async function getDailyRiskReports(params?: DailyRiskReportQueryParams) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDailyRiskReports((params || {}) as Record<string, unknown>, authHeaders) as any as any
}

export async function getDailyRiskReport(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDailyRiskReport(id, authHeaders) as any as any
}

export async function createDailyRiskReport(data: DailyRiskReportFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createDailyRiskReport(data, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as any
}

export async function updateDailyRiskReport(id: string, data: Partial<DailyRiskReportFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateDailyRiskReport(id, data, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as any
}

export async function deleteDailyRiskReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteDailyRiskReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as any
}

export async function submitDailyRiskReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitDailyRiskReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as any
}

export async function approveDailyRiskReport(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approveDailyRiskReport(id, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as any
}

export async function rejectDailyRiskReport(id: string, reason: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.rejectDailyRiskReport(id, reason, authHeaders)
  revalidatePath('/safety/risk-reporting')
  return response as any
}

export async function getHazardRiskOptions(params?: {
  department?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardRiskOptions(params || {}, authHeaders) as any as any
}


// ============ EHS变更管理 (MOC) ============

// CRUD
export async function getEhsChanges(params: EhsChangeQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getEhsChanges(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getEhsChange(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getEhsChange(id, authHeaders) as any as any
}

export async function createEhsChange(data: EhsChangeFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createEhsChange(data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function updateEhsChange(id: string, data: Partial<EhsChangeFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateEhsChange(id, data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function deleteEhsChange(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

// Workflow
export async function submitEhsChange(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function approveEhsChange(id: string, decision: string, comments?: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approveEhsChange(id, { decision, comments }, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function rejectEhsChange(id: string, comments?: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.rejectEhsChange(id, comments, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function startImplementationEhsChange(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.startImplementationEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function commissionEhsChange(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.commissionEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function closeEhsChange(id: string, closedBy?: string, tempExpiryDate?: string, restoredDate?: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.closeEhsChange(id, {
    closed_by: closedBy,
    temp_expiry_date: tempExpiryDate,
    restored_date: restoredDate,
  }, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function cancelEhsChange(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.cancelEhsChange(id, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

// JSON sub-record operations
export async function addRiskAssessment(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.addRiskAssessment(id, data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function updateActionItem(id: string, index: number, status: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateActionItem(id, index, status, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function updatePSSRChecklist(id: string, data: Record<string, unknown>[] | object[]) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updatePSSRChecklist(id, data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}

export async function submitVerification(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.submitVerification(id, data, authHeaders)
  revalidatePath('/safety/ehs-change')
  return response as any
}


// ==================== 职业危害因素监测 Actions ====================


export async function getOhHazardMonitors(params: OhHazardMonitorQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getOhHazardMonitors(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getOhHazardMonitor(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getOhHazardMonitor(id, authHeaders) as any as any
}

export async function createOhHazardMonitor(data: OhHazardMonitorFormData) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.createOhHazardMonitor(data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function updateOhHazardMonitor(id: string, data: Partial<OhHazardMonitorFormData>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateOhHazardMonitor(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function deleteOhHazardMonitor(id: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.deleteOhHazardMonitor(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

// Monitor Workflow
export async function startMonitor(id: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.startMonitor(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function completeMonitor(id: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.completeMonitor(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function verifyMonitor(id: string, data: { verified_by?: string; comments?: string }) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.verifyMonitor(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

// Monitor Sub-records
export async function addDetectionResult(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.addDetectionResult(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function updateDetectionResult(id: string, index: number, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateDetectionResult(id, index, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function deleteDetectionResult(id: string, index: number) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.deleteDetectionResult(id, index, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function addMonitorAbnormality(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.addMonitorAbnormality(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function updateMonitorAbnormalityStatus(id: string, index: number, status: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateMonitorAbnormalityStatus(id, index, status, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}


// ==================== 职业健康体检 Actions ====================


export async function getOhHealthExams(params: OhHealthExamQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getOhHealthExams(params as Record<string, unknown>, authHeaders) as any as any
}

export async function getOhHealthExam(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getOhHealthExam(id, authHeaders) as any as any
}

export async function createOhHealthExam(data: OhHealthExamFormData) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.createOhHealthExam(data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function updateOhHealthExam(id: string, data: Partial<OhHealthExamFormData>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateOhHealthExam(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function deleteOhHealthExam(id: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.deleteOhHealthExam(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

// Exam Workflow
export async function startExam(id: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.startExam(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function completeExam(id: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.completeExam(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function archiveExam(id: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.archiveExam(id, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

// Exam Sub-records
export async function addExamItem(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.addExamItem(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function updateExamItem(id: string, index: number, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateExamItem(id, index, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function deleteExamItem(id: string, index: number) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.deleteExamItem(id, index, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function setExamConclusion(id: string, conclusion: string, remarks?: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.setExamConclusion(id, { conclusion, remarks }, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function addExamAbnormality(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.addExamAbnormality(id, data, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

export async function updateExamAbnormalityStatus(id: string, index: number, status: string) {
  const authHeaders = await getAuthHeaders()
  const res = await safetyApi.updateExamAbnormalityStatus(id, index, status, authHeaders)
  revalidatePath('/safety/occupational-health')
  return res as any
}

// ── Special Ops Export ──

export async function parseSpecialOpsExportQuery(query: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.parseSpecialOpsExportQuery(query, authHeaders) as any as any
}

export async function exportSpecialOpsLedger(filters: Record<string, unknown>): Promise<Blob> {
  return safetyApi.exportSpecialOpsLedger(filters) as any as any
}

// ============ AI Workflow Config Actions ============

export async function getAIWorkflowConfigs(params?: { page_size?: number; page?: number }) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getAIWorkflowConfigs(params || {}, authHeaders) as any as any
}

export async function createAIWorkflowConfig(data: components['schemas']['AIWorkflowConfigCreate']) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createAIWorkflowConfig(data, authHeaders)
  revalidatePath('/safety/ai-workflow-config')
  return response as any
}

export async function updateAIWorkflowConfig(id: string, data: components['schemas']['AIWorkflowConfigUpdate']) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateAIWorkflowConfig(id, data, authHeaders)
  revalidatePath('/safety/ai-workflow-config')
  return response as any
}

export async function deleteAIWorkflowConfig(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteAIWorkflowConfig(id, authHeaders)
  revalidatePath('/safety/ai-workflow-config')
  return response as any
}

// ============ Scheduled Task Actions ============

export async function getScheduledTasks(params: { page?: number; page_size?: number }) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getScheduledTasks(params, authHeaders) as any as any
}

export async function getScheduledTask(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getScheduledTask(id, authHeaders) as any as any
}

export async function createScheduledTask(data: components['schemas']['ScheduledTaskCreate']) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createScheduledTask(data, authHeaders)
  revalidatePath('/safety/scheduled-tasks')
  return response as any
}

export async function updateScheduledTask(id: string, data: components['schemas']['ScheduledTaskUpdate']) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateScheduledTask(id, data, authHeaders)
  revalidatePath('/safety/scheduled-tasks')
  return response as any
}

export async function deleteScheduledTask(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteScheduledTask(id, authHeaders)
  revalidatePath('/safety/scheduled-tasks')
  return response as any
}

export async function toggleScheduledTask(id: string, enabled: boolean) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.toggleScheduledTask(id, enabled, authHeaders) as any as any
}

export async function runScheduledTaskNow(id: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.runScheduledTaskNow(id, authHeaders) as any as any
}

export async function getScheduledTaskLogs(taskId: string) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getScheduledTaskLogs(taskId, authHeaders) as any as any
}

export async function getDataSourceOptions() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getDataSourceOptions(authHeaders) as any as any
}

export async function getFeishuChats() {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getFeishuChats(authHeaders) as any as any
}

export async function previewCard(data: components['schemas']['CardPreviewRequest']) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.previewCard(data, authHeaders) as any as any
}

// ============ Hazard Legacy Actions ============

export async function completeRectification(id: string, data?: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.completeRectification(id, data || {}, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

export async function verifyRectification(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.verifyRectification(id, data, authHeaders)
  revalidatePath('/safety/hazard')
  return response as any
}

// ============ Hazard Revision Actions ============

export async function getHazardRevisionRecords(params: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardRevisionRecords(params, authHeaders) as any as any
}

export async function createHazardRevisionRecord(data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazardRevisionRecord(data, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}

export async function updateHazardRevisionRecord(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateHazardRevisionRecord(id, data, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}

export async function deleteHazardRevisionRecord(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteHazardRevisionRecord(id, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}

export async function approveHazardRevision(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.approveHazardRevision(id, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}

export async function uploadHazardRevisionDocument(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.uploadHazardRevisionDocument(id, formData, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}

export async function linkRevisionToArchive(revisionId: string, archiveId: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.linkRevisionToArchive(revisionId, archiveId, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}

export async function getHazardRevisionArchives(params: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getHazardRevisionArchives(params, authHeaders) as any as any
}

export async function createHazardRevisionArchive(data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.createHazardRevisionArchive(data, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}

export async function updateHazardRevisionArchive(id: string, data: Record<string, unknown>) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.updateHazardRevisionArchive(id, data, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}

export async function deleteHazardRevisionArchive(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await safetyApi.deleteHazardRevisionArchive(id, authHeaders)
  revalidatePath('/safety/hazard-identification-legacy')
  return response as any
}