'use server'

import { revalidatePath } from 'next/cache'
import {
  CreateCategoryInput, UpdateCategoryInput, CreateLocationInput, UpdateLocationInput, CreateEquipmentInput, UpdateEquipmentInput,
  CreateFailureCodeInput, UpdateFailureCodeInput,
  CreateWorkOrderInput, AssignWorkOrderInput, CompleteWorkOrderInput, VerifyWorkOrderInput,
  CreateCalibrationPlanInput, UpdateCalibrationPlanInput, CreateCalibrationRecordInput,
  ImportResult, ImportRowError,
} from '@/types/equipment'
export type { ImportResult, ImportRowError }
import {
  createCategoryApi,
  updateCategoryApi,
  deleteCategoryApi,
  createLocationApi,
  updateLocationApi,
  deleteLocationApi,
  createEquipmentApi,
  updateEquipmentApi,
  deleteEquipmentApi,
  createFailureCodeApi,
  updateFailureCodeApi,
  deleteFailureCodeApi,
  createWorkOrderApi,
  updateWorkOrderApi,
  assignWorkOrderApi,
  startWorkOrderApi,
  completeWorkOrderApi,
  verifyWorkOrderApi,
  closeWorkOrderApi,
  createCalibrationPlanApi,
  updateCalibrationPlanApi,
  deleteCalibrationPlanApi,
  createCalibrationRecordApi,
  createSparePartOldApi,
  updateSparePartOldApi,
  deleteSparePartOldApi,
  stockInboundOldApi,
  consumeMaterialsOldApi,
  uploadWorkOrderImagesOldApi,
  claimWorkOrderDataApi,
  updateClaimTimeoutConfigOldApi,
  completeInspectionOldApi,
  createMaintenancePlanOldApi,
  updateMaintenancePlanOldApi,
  deleteMaintenancePlanOldApi,
  createInspectionTemplateOldApi,
  updateInspectionTemplateOldApi,
  deleteInspectionTemplateOldApi,
  createInspectionTemplateItemOldApi,
  updateInspectionTemplateItemOldApi,
  deleteInspectionTemplateItemOldApi,
  createInspectionRouteOldApi,
  updateInspectionRouteOldApi,
  deleteInspectionRouteOldApi,
  setRouteLocationsOldApi,
  createScheduleOldApi,
  updateScheduleOldApi,
  deleteScheduleOldApi,
  createInspectionTaskOldApi,
  startInspectionTaskOldApi,
  closeInspectionTaskOldApi,
  submitEquipmentCheckOldApi,
  uploadInspectionPhotoOldApi,
  completeInspectionTaskOldApi,
  analyzeInspectionPhotoOldApi,
  addPersonnelOldApi,
  deletePersonnelOldApi,
  assignRolesOldApi,
  assignCategoriesOldApi,
  createRoleOldApi,
  updateRoleOldApi,
  deleteRoleOldApi,
  refreshFeishuOldApi,
  downloadImportTemplateOldApi,
  importEquipmentsOldApi,
} from '@/lib/api/server/equipment'

// 设备分类
export async function createCategory(data: CreateCategoryInput) {
  const result = await createCategoryApi(data)
  revalidatePath('/equipment')
  return result
}

export async function updateCategory(id: string, data: UpdateCategoryInput) {
  const result = await updateCategoryApi(id, data)
  revalidatePath('/equipment')
  return result
}

export async function deleteCategory(id: string) {
  const result = await deleteCategoryApi(id)
  revalidatePath('/equipment')
  return result
}

// 位置管理
export async function createLocation(data: CreateLocationInput) {
  const result = await createLocationApi(data)
  revalidatePath('/equipment')
  return result
}

export async function updateLocation(id: string, data: UpdateLocationInput) {
  const result = await updateLocationApi(id, data)
  revalidatePath('/equipment')
  return result
}

export async function deleteLocation(id: string) {
  const result = await deleteLocationApi(id)
  revalidatePath('/equipment')
  return result
}

// 设备管理
export async function createEquipment(data: CreateEquipmentInput) {
  const result = await createEquipmentApi(data)
  revalidatePath('/equipment')
  return result
}

export async function updateEquipment(id: string, data: UpdateEquipmentInput) {
  const result = await updateEquipmentApi(id, data)
  revalidatePath('/equipment')
  return result
}

export async function deleteEquipment(id: string) {
  const result = await deleteEquipmentApi(id)
  revalidatePath('/equipment')
  return result
}

// ==================== 故障代码 ====================
type FailureCodePath = 'symptoms' | 'causes' | 'actions'

export async function createFailureCode(path: FailureCodePath, data: CreateFailureCodeInput) {
  const result = await createFailureCodeApi(path, data)
  revalidatePath('/equipment')
  return result
}

export async function updateFailureCode(path: FailureCodePath, id: string, data: UpdateFailureCodeInput) {
  const result = await updateFailureCodeApi(path, id, data)
  revalidatePath('/equipment')
  return result
}

export async function deleteFailureCode(path: FailureCodePath, id: string) {
  const result = await deleteFailureCodeApi(path, id)
  revalidatePath('/equipment')
  return result
}

// ==================== 维修工单 ====================
export async function createWorkOrder(data: CreateWorkOrderInput) {
  const result = await createWorkOrderApi(data)
  revalidatePath('/equipment')
  return result
}

export async function assignWorkOrder(id: string, data: AssignWorkOrderInput) {
  const result = await assignWorkOrderApi(id, data)
  revalidatePath('/equipment')
  return result
}

export async function startWorkOrder(id: string) {
  const result = await startWorkOrderApi(id)
  revalidatePath('/equipment')
  return result
}

export async function completeWorkOrder(id: string, data: CompleteWorkOrderInput) {
  const result = await completeWorkOrderApi(id, data)
  revalidatePath('/equipment')
  return result
}

export async function verifyWorkOrder(id: string, data: VerifyWorkOrderInput) {
  const result = await verifyWorkOrderApi(id, data)
  revalidatePath('/equipment')
  return result
}

export async function closeWorkOrder(id: string) {
  const result = await closeWorkOrderApi(id)
  revalidatePath('/equipment')
  return result
}

// ==================== 校准计划 ====================
export async function createCalibrationPlan(data: CreateCalibrationPlanInput) {
  const result = await createCalibrationPlanApi(data)
  revalidatePath('/equipment')
  return result
}

export async function updateCalibrationPlan(id: string, data: UpdateCalibrationPlanInput) {
  const result = await updateCalibrationPlanApi(id, data)
  revalidatePath('/equipment')
  return result
}

export async function deleteCalibrationPlan(id: string) {
  const result = await deleteCalibrationPlanApi(id)
  revalidatePath('/equipment')
  return result
}

// ==================== 校准记录 ====================
export async function createCalibrationRecord(data: CreateCalibrationRecordInput) {
  const result = await createCalibrationRecordApi(data)
  revalidatePath('/equipment')
  return result
}

// ==================== 设备导入 ====================

export async function downloadImportTemplate(): Promise<any> {
  const blob = await downloadImportTemplateOldApi()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '设备导入模板.xlsx'
  a.click()
  window.URL.revokeObjectURL(url)
}

export async function importEquipments(file: File | FormData): Promise<ImportResult> {
  const fd = file instanceof FormData ? file : new FormData()
  if (!(file instanceof FormData)) fd.append('file', file)
  const res = await importEquipmentsOldApi(fd, {})
  revalidatePath('/equipment')
  return res
}

// ==================== 巡检管理 ====================
export async function createInspectionTemplate(data: any) {
  const result = await createInspectionTemplateOldApi(data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function updateInspectionTemplate(id: string, data: any) {
  const result = await updateInspectionTemplateOldApi(id, data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function deleteInspectionTemplate(id: string) {
  const result = await deleteInspectionTemplateOldApi(id)
  revalidatePath('/equipment/inspection')
  return result
}

export async function createInspectionTemplateItem(templateId: string, data: any) {
  const result = await createInspectionTemplateItemOldApi(templateId, data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function updateInspectionTemplateItem(id: string, data: any) {
  const result = await updateInspectionTemplateItemOldApi(id, data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function deleteInspectionTemplateItem(id: string) {
  const result = await deleteInspectionTemplateItemOldApi(id)
  revalidatePath('/equipment/inspection')
  return result
}

export async function createInspectionRoute(data: any) {
  const result = await createInspectionRouteOldApi(data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function updateInspectionRoute(id: string, data: any) {
  const result = await updateInspectionRouteOldApi(id, data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function deleteInspectionRoute(id: string) {
  const result = await deleteInspectionRouteOldApi(id)
  revalidatePath('/equipment/inspection')
  return result
}

export async function setRouteLocations(routeId: string, items: any) {
  const result = await setRouteLocationsOldApi(routeId, items)
  revalidatePath('/equipment/inspection')
  return result
}

export async function createSchedule(routeId: string, data: any) {
  const result = await createScheduleOldApi(routeId, data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function updateSchedule(routeId: string, id: string, data: any) {
  const result = await updateScheduleOldApi(routeId, id, data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function deleteSchedule(routeId: string, id: string) {
  const result = await deleteScheduleOldApi(routeId, id)
  revalidatePath('/equipment/inspection')
  return result
}

export async function createInspectionTask(data: any) {
  const result = await createInspectionTaskOldApi(data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function startInspectionTask(id: string) {
  const result = await startInspectionTaskOldApi(id)
  revalidatePath('/equipment/inspection')
  return result
}

export async function closeInspectionTask(id: string) {
  const result = await closeInspectionTaskOldApi(id)
  revalidatePath('/equipment/inspection')
  return result
}

export async function submitEquipmentCheck(taskId: string, equipmentId: string, data: any) {
  const result = await submitEquipmentCheckOldApi(taskId, equipmentId, data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function uploadInspectionPhoto(taskId: string, equipmentId: string, formData: FormData) {
  const result = await uploadInspectionPhotoOldApi(taskId, equipmentId, formData, {})
  revalidatePath('/equipment/inspection')
  return result
}

export async function completeInspectionTask(id: string, data: any) {
  const result = await completeInspectionTaskOldApi(id, data)
  revalidatePath('/equipment/inspection')
  return result
}

export async function analyzeInspectionPhoto(taskId: string, equipmentId: string, base64: string, mimeType: string) {
  const result = await analyzeInspectionPhotoOldApi(taskId, equipmentId, base64, mimeType)
  return result
}

// ==================== 维护计划 ====================
export async function createMaintenancePlan(data: any) {
  const result = await createMaintenancePlanOldApi(data)
  revalidatePath('/equipment/maintenance')
  return result
}

export async function updateMaintenancePlan(id: string, data: any) {
  const result = await updateMaintenancePlanOldApi(id, data)
  revalidatePath('/equipment/maintenance')
  return result
}

export async function deleteMaintenancePlan(id: string) {
  const result = await deleteMaintenancePlanOldApi(id)
  revalidatePath('/equipment/maintenance')
  return result
}

export async function updateClaimTimeoutConfig(config: any) {
  const result = await updateClaimTimeoutConfigOldApi(config)
  revalidatePath('/equipment/maintenance')
  return result
}

export async function completeInspection(workOrderId: string, data: any) {
  const result = await completeInspectionOldApi(workOrderId, data)
  revalidatePath('/equipment/maintenance')
  return result
}

// ==================== 备件管理 ====================
export async function createSparePart(data: any) {
  const result = await createSparePartOldApi(data)
  revalidatePath('/equipment/spare-parts')
  return result
}

export async function updateSparePart(id: string, data: any) {
  const result = await updateSparePartOldApi(id, data)
  revalidatePath('/equipment/spare-parts')
  return result
}

export async function deleteSparePart(id: string) {
  const result = await deleteSparePartOldApi(id)
  revalidatePath('/equipment/spare-parts')
  return result
}

export async function stockInbound(sparePartId: string, data: any) {
  const result = await stockInboundOldApi(sparePartId, data)
  revalidatePath('/equipment/spare-parts')
  return result
}

export async function consumeMaterials(workOrderId: string, data: any) {
  const result = await consumeMaterialsOldApi(workOrderId, data)
  revalidatePath('/equipment/maintenance')
  return result
}

// ==================== 工单扩展 ====================
export async function claimWorkOrder(id: string, data?: any) {
  const result = await claimWorkOrderDataApi(id, data)
  revalidatePath('/equipment/maintenance')
  return result
}

export async function uploadWorkOrderImages(id: string, formData: FormData) {
  const result = await uploadWorkOrderImagesOldApi(id, formData, {})
  revalidatePath('/equipment/maintenance')
  return result
}

// ==================== 人员管理 ====================
export async function addPersonnel(data: any) {
  const result = await addPersonnelOldApi(data)
  revalidatePath('/equipment/personnel')
  return result
}

export async function deletePersonnel(id: string) {
  const result = await deletePersonnelOldApi(id)
  revalidatePath('/equipment/personnel')
  return result
}

export async function assignRoles(personnelId: string, data: any) {
  const result = await assignRolesOldApi(personnelId, data)
  revalidatePath('/equipment/personnel')
  return result
}

export async function assignCategories(personnelId: string, data: any) {
  const result = await assignCategoriesOldApi(personnelId, data)
  revalidatePath('/equipment/personnel')
  return result
}

export async function createRole(data: any) {
  const result = await createRoleOldApi(data)
  revalidatePath('/equipment/personnel')
  return result
}

export async function updateRole(id: string, data: any) {
  const result = await updateRoleOldApi(id, data)
  revalidatePath('/equipment/personnel')
  return result
}

export async function deleteRole(id: string) {
  const result = await deleteRoleOldApi(id)
  revalidatePath('/equipment/personnel')
  return result
}

export async function refreshFeishu() {
  const result = await refreshFeishuOldApi()
  revalidatePath('/equipment/personnel')
  return result
}

export async function updateWorkOrder(id: string, data: any) {
  const result = await updateWorkOrderApi(id, data)
  revalidatePath('/equipment/maintenance')
  return result
}

const API_BASE_URL = process.env.API_BASE_URL || 'http://backend:8000'

export async function previewEquipmentImport(data: any[]) {
  const response = await fetch(`${API_BASE_URL}/api/v1/equipment/import/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return response.json()
}

export async function batchImportEquipment(data: any[]) {
  const response = await fetch(`${API_BASE_URL}/api/v1/equipment/import/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return response.json()
}