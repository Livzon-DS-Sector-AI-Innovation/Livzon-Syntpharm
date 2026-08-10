import {safeApiFetch, buildQueryString, getApiBaseUrl} from '@/lib/api/server/base'

async function uploadFetch(
  endpoint: string,
  formData: FormData,
  authHeaders?: Record<string, string>
): Promise<any> {
  const { 'Content-Type': _, ...uploadHeaders } = authHeaders || {}
  const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
    method: 'POST',
    headers: uploadHeaders,
    body: formData,
    cache: 'no-store',
  })
  if (!response.ok) {
    let detail = ''
    try {
      const err = await response.json()
      detail = err.detail || err.message || ''
    } catch { /* ignore */ }
    throw new Error(`HTTP ${response.status}${detail ? ': ' + detail : ''}`)
  }
  return response.json()
}

// ============ SafetyCheck ============

export async function getChecks(
  params: Record<string, unknown> = {},
  authHeaders?: Record<string, string>
) {
  return safeApiFetch<any[]>(`/api/v1/safety/checks${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getCheck(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/checks/${id}`, { headers: authHeaders })
}

export async function createCheck(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/checks', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateCheck(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/checks/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function submitCheck(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/checks/${id}/submit`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function reviewCheck(id: string, result: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/checks/${id}/review?result=${result}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function deleteCheck(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/checks/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function confirmCheckApi(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/checks/${id}/confirm`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

// ============ HazardReport ============

export async function fetchHazardStats(authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/hazards/stats', { headers: authHeaders })
}

export async function getHazards(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/hazards${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getHazard(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}`, { headers: authHeaders })
}

export async function getDepartmentLeader(departmentName: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/department-leader?department_name=${encodeURIComponent(departmentName)}`, { headers: authHeaders })
}

export async function getDepartmentSafetyOfficer(departmentName: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/department-safety-officer?department_name=${encodeURIComponent(departmentName)}`, { headers: authHeaders })
}

export async function createHazard(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/hazards', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateHazard(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function startRectification(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/rectification/start`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function replyRectification(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/rectification/reply`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function verifyLevel(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/rectification/verify-level`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function notifyReviewer(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/rectification/notify-reviewer`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function notifyRectification(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/rectification/notify-rectification`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function triggerRectificationReview(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/rectification/review`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function reworkRectification(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/rectification/rework`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteHazard(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/hazards/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function uploadHazardPhoto(endpoint: string, file: File, authHeaders?: Record<string, string>) {
  const formData = new FormData()
  formData.append('file', file)
  return uploadFetch(endpoint, formData, authHeaders)
}

export async function runHazardAI(hazardId: string, scriptNumber: number, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${hazardId}/ai/run/${scriptNumber}`, {
    method: 'POST',
    headers: authHeaders,
    body: '{}',
  })
}

// ============ Accident ============

export async function getAccidents(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/accidents${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getAccident(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/accidents/${id}`, { headers: authHeaders })
}

export async function createAccident(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/accidents', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateAccident(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/accidents/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function investigateAccident(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/accidents/${id}/investigate`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function resolveAccident(id: string, params: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/accidents/${id}/resolve?${params}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function startCapa(id: string, params: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/accidents/${id}/start-capa?${params}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function verifyCapa(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/accidents/${id}/verify-capa`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function closeAccident(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/accidents/${id}/close`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function deleteAccident(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/accidents/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

// ============ Contractor ============

export async function getContractors(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/contractors${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getContractor(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/contractors/${id}`, { headers: authHeaders })
}

export async function createContractor(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/contractors', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateContractor(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/contractors/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteContractor(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/contractors/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function blacklistContractor(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/contractors/${id}/blacklist`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function activateContractor(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/contractors/${id}/activate`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function updateContractorTraining(id: string, params: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/contractors/${id}/update-training?${params}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function getWorkRecords(contractorId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/contractors/${contractorId}/work-records`, { headers: authHeaders })
}

export async function createWorkRecord(contractorId: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/contractors/${contractorId}/work-records`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateWorkRecord(contractorId: string, recordId: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/contractors/${contractorId}/work-records/${recordId}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteWorkRecord(contractorId: string, recordId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/contractors/${contractorId}/work-records/${recordId}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function evaluateWorkRecord(contractorId: string, recordId: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/contractors/${contractorId}/work-records/${recordId}/evaluate`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

// ============ SafetyTraining ============

export async function getTrainings(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/trainings${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getTraining(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/trainings/${id}`, { headers: authHeaders })
}

export async function createTraining(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/trainings', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateTraining(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/trainings/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function startTraining(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/trainings/${id}/start`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function completeTraining(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/trainings/${id}/complete`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function deleteTraining(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/trainings/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

// ============ TrainingRecord ============

export async function getTrainingRecords(trainingId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/trainings/${trainingId}/records`, { headers: authHeaders })
}

export async function createTrainingRecord(trainingId: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/trainings/${trainingId}/records`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateTrainingRecord(recordId: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/training-records/${recordId}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingRecord(recordId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/training-records/${recordId}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

// ============ TrainingCertificate ============

export async function getTrainingCertificates(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/training-certificates${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getExpiringCertificates(authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>('/api/v1/safety/training-certificates/expiring', { headers: authHeaders })
}

// ============ HazardIdentification ============

export async function getHazardIdentifications(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/hazard-identifications${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getHIStats(authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/hazard-identifications/stats', { headers: authHeaders })
}

export async function getHILedgerStats(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-identifications/ledger-stats${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getHazardIdentification(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-identifications/${id}`, { headers: authHeaders })
}

export async function createHazardIdentification(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/hazard-identifications', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function getRegulationStages(regulationId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/regulations/${regulationId}/stages`, { headers: authHeaders })
}

export async function createHazardIdentificationBatch(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/hazard-identifications/batch', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateHazardIdentification(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-identifications/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function submitHazardIdentification(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-identifications/${id}/submit`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function runHazardScript(id: string, body: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-identifications/${id}/run-script`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(body),
  })
}

export async function reviewHazardScript(id: string, body: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-identifications/${id}/review`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(body),
  })
}

export async function uploadHazardAttachment(id: string, formData: FormData, authHeaders?: Record<string, string>) {
  return uploadFetch(`/api/v1/safety/hazard-identifications/${id}/upload`, formData, authHeaders)
}

export async function deleteHazardIdentification(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/hazard-identifications/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function parseHazardExportQuery(naturalQuery: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/hazard-identifications/parse-query', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify({ natural_query: naturalQuery }),
  })
}

export async function exportHazardLedgerPdf(data: any, authHeaders?: Record<string, string>) {
  const response = await fetch(`${getApiBaseUrl()}/safety/hazard-identifications/export-pdf`, {
    method: 'POST',
    headers: authHeaders || {},
    body: JSON.stringify(data),
    cache: 'no-store',
  })
  if (!response.ok) {
    const errorText = await response.text()
    return { code: response.status, message: `导出失败: ${errorText}`, data: '' }
  }
  const arrayBuffer = await response.arrayBuffer()
  const base64 = Buffer.from(arrayBuffer).toString('base64')
  return { code: 0, message: 'ok', data: base64 }
}

export async function getSafetyEnums(authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/enums', { headers: authHeaders })
}

// ============ OperationRegulation ============

export async function getRegulations(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/regulations${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getRegulation(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/regulations/${id}`, { headers: authHeaders })
}

export async function createRegulation(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/regulations', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateRegulation(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/regulations/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteRegulation(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/regulations/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function uploadRegulationDocument(id: string, formData: FormData, authHeaders?: Record<string, string>) {
  return uploadFetch(`/api/v1/safety/regulations/${id}/upload`, formData, authHeaders)
}

export async function generateSop(formData: FormData, authHeaders?: Record<string, string>) {
  return uploadFetch('/api/v1/safety/regulations/generate', formData, authHeaders)
}

export async function updateSopContent(regulationId: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/regulations/${regulationId}/content`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function exportSopPdf(regulationId: string, authHeaders?: Record<string, string>) {
  const { 'Content-Type': _, ...headers } = authHeaders || {}
  const response = await fetch(`${getApiBaseUrl()}/safety/regulations/${regulationId}/export`, {
    method: 'POST',
    headers,
    cache: 'no-store',
  })
  if (!response.ok) {
    const text = await response.text()
    return { code: response.status, message: `导出 PDF 失败: ${text}` }
  }
  const blob = await response.blob()
  return { code: 0, message: 'ok', data: blob }
}

export async function exportRegulationPdfBase64(regulationId: string, authHeaders?: Record<string, string>) {
  const { 'Content-Type': _, ...headers } = authHeaders || {}
  const response = await fetch(`${getApiBaseUrl()}/safety/regulations/${regulationId}/export`, {
    method: 'POST',
    headers,
    cache: 'no-store',
  })
  if (!response.ok) {
    const text = await response.text()
    return { code: response.status, message: `导出 PDF 失败: ${text}`, data: '' }
  }
  const arrayBuffer = await response.arrayBuffer()
  const base64 = Buffer.from(arrayBuffer).toString('base64')
  return { code: 0, message: 'ok', data: base64 }
}

export async function reviseRegulation(regulationId: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/regulations/${regulationId}/revise`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

// ============ RegulationRevision ============

export async function getRevisions(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/revisions${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getRevision(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/revisions/${id}`, { headers: authHeaders })
}

export async function createRevision(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/revisions', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateRevision(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/revisions/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteRevision(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/revisions/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function manualRevisionComplete(revisionId: string, formData: FormData, authHeaders?: Record<string, string>) {
  return uploadFetch(`/api/v1/safety/revisions/${revisionId}/manual-complete`, formData, authHeaders)
}

export async function aiRevisionGenerate(revisionId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/revisions/${revisionId}/ai-generate`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function aiRevisionConfirm(revisionId: string, params: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/revisions/${revisionId}/ai-confirm?${params}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function identifyRevisionScope(revisionId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/revisions/${revisionId}/identify-scope`, {
    method: 'POST',
    headers: authHeaders,
  })
}

// ============ SpecialOperationPersonnel ============

export async function getPersonnelList(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/special-operation-personnel${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getPersonnel(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-personnel/${id}`, { headers: authHeaders })
}

export async function createPersonnel(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/special-operation-personnel', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updatePersonnel(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-personnel/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deletePersonnel(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/special-operation-personnel/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

// ============ SpecialOperationPermit ============

export async function getPermitList(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/special-operation-permits${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getPermit(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-permits/${id}`, { headers: authHeaders })
}

export async function createPermit(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/special-operation-permits', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updatePermit(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-permits/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deletePermit(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/special-operation-permits/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function submitPermit(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-permits/${id}/submit`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function approvePermit(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-permits/${id}/approve`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function rejectPermit(id: string, reason: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-permits/${id}/reject?reason=${encodeURIComponent(reason)}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function startPermit(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-permits/${id}/start`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function completePermit(id: string, method: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-permits/${id}/complete?method=${encodeURIComponent(method)}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function archivePermit(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-permits/${id}/archive`, {
    method: 'POST',
    headers: authHeaders,
  })
}

// ============ SafetyKnowledgeArticle ============

export async function getKnowledgeArticles(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/knowledge-articles${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getKnowledgeArticle(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${id}`, { headers: authHeaders })
}

export async function createKnowledgeArticle(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/knowledge-articles', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateKnowledgeArticle(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteKnowledgeArticle(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/knowledge-articles/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function publishKnowledgeArticle(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${id}/publish`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function archiveKnowledgeArticle(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${id}/archive`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function parseKnowledgeDocument(formData: FormData, authHeaders?: Record<string, string>) {
  return uploadFetch('/api/v1/safety/knowledge-articles/parse', formData, authHeaders)
}

export async function batchParseKnowledgeDocuments(formData: FormData, authHeaders?: Record<string, string>) {
  return uploadFetch('/api/v1/safety/knowledge-articles/batch-parse', formData, authHeaders)
}

export async function uploadKnowledgeAttachment(articleId: string, file: File, authHeaders?: Record<string, string>) {
  const formData = new FormData()
  formData.append('file', file)
  return uploadFetch(`/api/v1/safety/knowledge-articles/${articleId}/upload`, formData, authHeaders)
}

export async function checkDuplicateArticle(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/knowledge-articles/check-duplicate', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function getArticleVersions(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/knowledge-articles/${id}/versions`, { headers: authHeaders })
}

export async function createNewArticleVersion(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${id}/new-version`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function semanticSearchArticles(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/knowledge-articles/semantic-search${buildQueryString(params)}`, { headers: authHeaders })
}

export async function generateKnowledgeCard(articleId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${articleId}/generate-card`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function getAgentUsageStats(articleId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${articleId}/agent-stats`, { headers: authHeaders })
}

export async function batchGenerateKnowledgeCards(articleIds: string[], authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/knowledge-articles/batch/generate-cards', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify({ article_ids: articleIds }),
  })
}

export async function generatePpt(articleId: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${articleId}/generate-ppt`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function getPptHistory(articleId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${articleId}/ppt-history`, { headers: authHeaders })
}

export async function generateSummary(articleId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-articles/${articleId}/generate-summary`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function syncKnowledgeArticles(authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/knowledge-articles/sync', {
    method: 'POST',
    headers: authHeaders,
  })
}

// ============ SpecialOperationReport ============

export async function getSpecialOperationReports(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/special-operation-reports${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getSpecialOperationReport(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-reports/${id}`, { headers: authHeaders })
}

export async function createSpecialOperationReport(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/special-operation-reports', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateSpecialOperationReport(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-reports/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteSpecialOperationReport(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/special-operation-reports/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function submitSpecialOperationReport(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-reports/${id}/submit`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function approveSpecialOperationReport(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-reports/${id}/approve`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function rejectSpecialOperationReport(id: string, reason: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-reports/${id}/reject?reason=${encodeURIComponent(reason)}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function setSpecialOperationReportCritical(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/special-operation-reports/${id}/critical`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

// ============ SpecialOperationLedger ============

export async function getSpecialOperationLedger(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/special-operation-ledger${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getSpecialOperationLedgerStats(authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>('/api/v1/safety/special-operation-ledger/stats', { headers: authHeaders })
}

// ============ DailyRiskReport ============

export async function getDailyRiskReports(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/daily-risk-reports${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getDailyRiskReport(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/daily-risk-reports/${id}`, { headers: authHeaders })
}

export async function createDailyRiskReport(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/daily-risk-reports', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateDailyRiskReport(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/daily-risk-reports/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteDailyRiskReport(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/daily-risk-reports/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function submitDailyRiskReport(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/daily-risk-reports/${id}/submit`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function approveDailyRiskReport(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/daily-risk-reports/${id}/approve`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function rejectDailyRiskReport(id: string, reason: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/daily-risk-reports/${id}/reject?reason=${encodeURIComponent(reason)}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function getHazardRiskOptions(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/hazard-identifications/risk-options${buildQueryString(params)}`, { headers: authHeaders })
}

// ============ EhsChange ============

export async function getEhsChanges(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/ehs-changes${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getEhsChange(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}`, { headers: authHeaders })
}

export async function createEhsChange(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/ehs-changes', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateEhsChange(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteEhsChange(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/ehs-changes/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function submitEhsChange(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/submit`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function approveEhsChange(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/approve`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function rejectEhsChange(id: string, comments?: string, authHeaders?: Record<string, string>) {
  const params = comments ? `?comments=${encodeURIComponent(comments)}` : ''
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/reject${params}`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function startImplementationEhsChange(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/start-implementation`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function commissionEhsChange(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/commission`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function closeEhsChange(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/close`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function cancelEhsChange(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/cancel`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function addRiskAssessment(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/risk-assessments`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateActionItem(id: string, index: number, status: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/action-items/${index}?status=${encodeURIComponent(status)}`, {
    method: 'PUT',
    headers: authHeaders,
  })
}

export async function updatePSSRChecklist(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/pssr-checklist`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function submitVerification(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ehs-changes/${id}/verification`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

// ============ OhHazardMonitor ============

export async function getOhHazardMonitors(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/oh-hazard-monitors${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getOhHazardMonitor(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}`, { headers: authHeaders })
}

export async function createOhHazardMonitor(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/oh-hazard-monitors', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateOhHazardMonitor(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteOhHazardMonitor(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/oh-hazard-monitors/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function startMonitor(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}/start`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function completeMonitor(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}/complete`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function verifyMonitor(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}/verify`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function addDetectionResult(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}/detection-results`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateDetectionResult(id: string, index: number, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}/detection-results/${index}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteDetectionResult(id: string, index: number, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/oh-hazard-monitors/${id}/detection-results/${index}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function addMonitorAbnormality(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}/abnormality-records`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateMonitorAbnormalityStatus(id: string, index: number, status: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-hazard-monitors/${id}/abnormality-records/${index}?status=${encodeURIComponent(status)}`, {
    method: 'PUT',
    headers: authHeaders,
  })
}

// ============ OhHealthExam ============

export async function getOhHealthExams(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/oh-health-exams${buildQueryString(params)}`, { headers: authHeaders })
}

export async function getOhHealthExam(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}`, { headers: authHeaders })
}

export async function createOhHealthExam(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/oh-health-exams', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateOhHealthExam(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteOhHealthExam(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/oh-health-exams/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function startExam(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}/start`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function completeExam(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}/complete`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function archiveExam(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}/archive`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function addExamItem(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}/exam-items`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateExamItem(id: string, index: number, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}/exam-items/${index}`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function deleteExamItem(id: string, index: number, authHeaders?: Record<string, string>) {
  return safeApiFetch<null>(`/api/v1/safety/oh-health-exams/${id}/exam-items/${index}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function setExamConclusion(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}/conclusion`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function addExamAbnormality(id: string, data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}/abnormality-records`, {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify(data),
  })
}

export async function updateExamAbnormalityStatus(id: string, index: number, status: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/oh-health-exams/${id}/abnormality-records/${index}?status=${encodeURIComponent(status)}`, {
    method: 'PUT',
    headers: authHeaders,
  })
}

// ============ SpecialOps ============

export async function parseSpecialOpsExportQuery(query: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/special-ops/parse-export-query', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify({ natural_query: query }),
  })
}

export async function exportSpecialOpsLedger(data: any) {
  const response = await fetch(`${getApiBaseUrl()}/safety/special-ops/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error('导出失败')
  }
  return response.blob()
}

// ============ Knowledge Graph ============

export async function getFullGraph(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-graph/full-graph${buildQueryString(params)}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function getGraphNodes(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/knowledge-graph/nodes${buildQueryString(params)}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function getGraphEdges(params: Record<string, unknown> = {}, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/knowledge-graph/edges${buildQueryString(params)}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function searchGraphNodes(query: string, nodeTypes?: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/knowledge-graph/search${buildQueryString({ query, node_types: nodeTypes })}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function expandGraphNode(params: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/knowledge-graph/expand${buildQueryString(params)}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function triggerGraphGeneration(data: any, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/knowledge-graph/generate', {
    method: 'POST',
    headers: {
      ...authHeaders,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data || {}),
  })
}

// ============ AI Workflow Config APIs ============

export async function getAIWorkflowConfigs(params: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/ai-workflow-configs${buildQueryString(params)}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function createAIWorkflowConfig(data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/ai-workflow-configs', {
    method: 'POST',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateAIWorkflowConfig(id: string, data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ai-workflow-configs/${id}`, {
    method: 'PUT',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteAIWorkflowConfig(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/ai-workflow-configs/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

// ============ Scheduled Task APIs ============

export async function getScheduledTasks(params: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/scheduled-tasks${buildQueryString(params)}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function getScheduledTask(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/scheduled-tasks/${id}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function createScheduledTask(data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/scheduled-tasks', {
    method: 'POST',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateScheduledTask(id: string, data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/scheduled-tasks/${id}`, {
    method: 'PUT',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteScheduledTask(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/scheduled-tasks/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function toggleScheduledTask(id: string, enabled: boolean, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/scheduled-tasks/${id}/toggle`, {
    method: 'PUT',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_enabled: enabled }),
  })
}

export async function runScheduledTaskNow(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/scheduled-tasks/${id}/run`, {
    method: 'POST',
    headers: authHeaders,
  })
}

export async function getScheduledTaskLogs(taskId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/scheduled-tasks/${taskId}/logs`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function getDataSourceOptions(authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>('/api/v1/safety/scheduled-tasks/data-sources', {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function getFeishuChats(authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>('/api/v1/safety/scheduled-tasks/feishu-chats', {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function previewCard(data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/scheduled-tasks/preview-card', {
    method: 'POST',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

// ============ Hazard Legacy APIs ============

export async function completeRectification(id: string, data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/complete`, {
    method: 'PUT',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function verifyRectification(id: string, data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazards/${id}/verify`, {
    method: 'PUT',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

// ============ Hazard Revision APIs ============

export async function getHazardRevisionRecords(params: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/hazard-revision-records${buildQueryString(params)}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function createHazardRevisionRecord(data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/hazard-revision-records', {
    method: 'POST',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateHazardRevisionRecord(id: string, data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-revision-records/${id}`, {
    method: 'PUT',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteHazardRevisionRecord(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-revision-records/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}

export async function approveHazardRevision(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-revision-records/${id}/approve`, {
    method: 'PUT',
    headers: authHeaders,
  })
}

export async function uploadHazardRevisionDocument(id: string, formData: FormData, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-revision-records/${id}/upload-document`, {
    method: 'POST',
    headers: authHeaders,
    body: formData,
  })
}

export async function linkRevisionToArchive(revisionId: string, archiveId: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-revision-records/${revisionId}/link-archive`, {
    method: 'PUT',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify({ archive_id: archiveId }),
  })
}

export async function getHazardRevisionArchives(params: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any[]>(`/api/v1/safety/hazard-revision-archives${buildQueryString(params)}`, {
    method: 'GET',
    headers: authHeaders,
  })
}

export async function createHazardRevisionArchive(data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>('/api/v1/safety/hazard-revision-archives', {
    method: 'POST',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateHazardRevisionArchive(id: string, data: Record<string, unknown>, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-revision-archives/${id}`, {
    method: 'PUT',
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteHazardRevisionArchive(id: string, authHeaders?: Record<string, string>) {
  return safeApiFetch<any>(`/api/v1/safety/hazard-revision-archives/${id}`, {
    method: 'DELETE',
    headers: authHeaders,
  })
}
