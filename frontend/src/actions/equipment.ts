'use server'

import { revalidatePath } from 'next/cache'
import { getServerToken } from '@/lib/auth'
import type { components } from '@/types/generated/schema'
type CreateCategoryInput = components['schemas']['EquipmentCategoryCreate']
type UpdateCategoryInput = components['schemas']['EquipmentCategoryUpdate']
type CreateEquipmentInput = components['schemas']['EquipmentCreate']
type UpdateEquipmentInput = components['schemas']['EquipmentUpdate']

type CreateLocationInput = components['schemas']['LocationCreate']
type UpdateLocationInput = components['schemas']['LocationUpdate']
type CreateWorkOrderInput = components['schemas']['WorkOrderCreate']
type UpdateWorkOrderInput = components['schemas']['WorkOrderUpdate']
type AssignWorkOrderInput = components['schemas']['WorkOrderAssign']
type CompleteWorkOrderInput = components['schemas']['WorkOrderComplete']
type VerifyWorkOrderInput = components['schemas']['WorkOrderVerify']
type CreateCalibrationPlanInput = components['schemas']['CalibrationPlanCreate']
type UpdateCalibrationPlanInput = components['schemas']['CalibrationPlanUpdate']
type CreateCalibrationRecordInput = components['schemas']['app__modules__equipment__schemas__calibration__CalibrationRecordCreate']
type CreateSparePartInput = components['schemas']['SparePartCreate']
type UpdateSparePartInput = components['schemas']['SparePartUpdate']
type StockInboundInput = components['schemas']['StockInboundRequest']
type StockAdjustInput = components['schemas']['StockAdjustRequest']
type CreateMaintenancePlanInput = components['schemas']['MaintenancePlanCreate']
type UpdateMaintenancePlanInput = components['schemas']['MaintenancePlanUpdate']
type CreateInspectionTemplateInput = components['schemas']['InspectionTemplateCreate']
type UpdateInspectionTemplateInput = components['schemas']['InspectionTemplateUpdate']
type CreateInspectionTemplateItemInput = components['schemas']['InspectionTemplateItemCreate']
type UpdateInspectionTemplateItemInput = components['schemas']['InspectionTemplateItemUpdate']
type CreateFailureCodeInput = components['schemas']['FailureCodeCreate']
type UpdateFailureCodeInput = components['schemas']['FailureCodeUpdate']
import type {
  InspectionCompleteInput, MaterialConsumeInput,
} from '@/types/equipment'

import {
  createCategoryApi, updateCategoryApi, deleteCategoryApi,
  createLocationApi, updateLocationApi, deleteLocationApi,
  createEquipmentApi, updateEquipmentApi, deleteEquipmentApi,
  createFailureCodeApi, updateFailureCodeApi, deleteFailureCodeApi,
  createWorkOrderApi, updateWorkOrderApi, assignWorkOrderApi,
  startWorkOrderApi, completeWorkOrderApi, verifyWorkOrderApi, closeWorkOrderApi,
  createCalibrationPlanApi, updateCalibrationPlanApi, deleteCalibrationPlanApi,
  createCalibrationRecordApi,
  createSparePartApi, updateSparePartApi, deleteSparePartApi,
  stockInboundApi, stockAdjustApi,
  createMaintenancePlanApi, updateMaintenancePlanApi, deleteMaintenancePlanApi,
  createInspectionTemplateApi, updateInspectionTemplateApi, deleteInspectionTemplateApi,
  createInspectionTemplateItemApi, updateInspectionTemplateItemApi, deleteInspectionTemplateItemApi,
  completeInspectionApi, consumeMaterialsApi,
  uploadWorkOrderImagesApi, deleteWorkOrderImageApi,
  claimWorkOrderApi, updateClaimTimeoutConfigApi,
  downloadImportTemplateApi, importEquipmentsApi,
  previewEquipmentImportApi, batchImportEquipmentApi,
  createPersonnelRoleApi, updatePersonnelRoleApi, deletePersonnelRoleApi,
  addPersonnelApi, deletePersonnelApi, assignRolesApi, assignCategoriesApi, refreshFeishuApi,
  fetchCategoryTree, fetchLocationTree, fetchEquipments, fetchEquipmentStatistics,
  fetchDepartments, fetchWorkOrders, fetchWorkOrderStatistics, fetchFailureCodes,
  fetchCalibrationPlans, fetchCalibrationRecords, fetchMaintenancePlans,
  fetchInspectionTemplates, fetchCategories, fetchSpareParts, fetchStockWarnings,
  fetchOverdueMaintenancePlans,
} from '@/lib/api/server/equipment'

export {
  fetchCategoryTree, fetchLocationTree, fetchEquipments, fetchEquipmentStatistics,
  fetchDepartments, fetchWorkOrders, fetchWorkOrderStatistics, fetchFailureCodes,
  fetchCalibrationPlans, fetchCalibrationRecords, fetchMaintenancePlans,
  fetchInspectionTemplates, fetchCategories, fetchSpareParts, fetchStockWarnings,
  fetchOverdueMaintenancePlans,
}

async function authHeaders(): Promise<Record<string, string>> {
  return { Authorization: `Bearer ${await getServerToken()}` }
}

type FailureCodePath = 'symptoms' | 'causes' | 'actions'

export async function createCategory(data: CreateCategoryInput) {
  const result = await createCategoryApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateCategory(id: string, data: UpdateCategoryInput) {
  const result = await updateCategoryApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteCategory(id: string) {
  const result = await deleteCategoryApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createLocation(data: CreateLocationInput) {
  const result = await createLocationApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateLocation(id: string, data: UpdateLocationInput) {
  const result = await updateLocationApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteLocation(id: string) {
  const result = await deleteLocationApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createEquipment(data: CreateEquipmentInput) {
  const result = await createEquipmentApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateEquipment(id: string, data: UpdateEquipmentInput) {
  const result = await updateEquipmentApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteEquipment(id: string) {
  const result = await deleteEquipmentApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createFailureCode(path: FailureCodePath, data: CreateFailureCodeInput) {
  const result = await createFailureCodeApi(path, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateFailureCode(path: FailureCodePath, id: string, data: UpdateFailureCodeInput) {
  const result = await updateFailureCodeApi(path, id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteFailureCode(path: FailureCodePath, id: string) {
  const result = await deleteFailureCodeApi(path, id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createWorkOrder(data: CreateWorkOrderInput) {
  const result = await createWorkOrderApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateWorkOrder(id: string, data: UpdateWorkOrderInput) {
  const result = await updateWorkOrderApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function assignWorkOrder(id: string, data: AssignWorkOrderInput) {
  const result = await assignWorkOrderApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function startWorkOrder(id: string) {
  const result = await startWorkOrderApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function completeWorkOrder(id: string, data: CompleteWorkOrderInput) {
  const result = await completeWorkOrderApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function verifyWorkOrder(id: string, data: VerifyWorkOrderInput) {
  const result = await verifyWorkOrderApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function closeWorkOrder(id: string) {
  const result = await closeWorkOrderApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createCalibrationPlan(data: CreateCalibrationPlanInput) {
  const result = await createCalibrationPlanApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateCalibrationPlan(id: string, data: UpdateCalibrationPlanInput) {
  const result = await updateCalibrationPlanApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteCalibrationPlan(id: string) {
  const result = await deleteCalibrationPlanApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createCalibrationRecord(data: CreateCalibrationRecordInput) {
  const result = await createCalibrationRecordApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createSparePart(data: CreateSparePartInput) {
  const result = await createSparePartApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateSparePart(id: string, data: UpdateSparePartInput) {
  const result = await updateSparePartApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteSparePart(id: string) {
  const result = await deleteSparePartApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function stockInbound(sparePartId: string, data: StockInboundInput) {
  const result = await stockInboundApi(sparePartId, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function stockAdjust(sparePartId: string, data: StockAdjustInput) {
  const result = await stockAdjustApi(sparePartId, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createMaintenancePlan(data: CreateMaintenancePlanInput) {
  const result = await createMaintenancePlanApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateMaintenancePlan(id: string, data: UpdateMaintenancePlanInput) {
  const result = await updateMaintenancePlanApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteMaintenancePlan(id: string) {
  const result = await deleteMaintenancePlanApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createInspectionTemplate(data: CreateInspectionTemplateInput) {
  const result = await createInspectionTemplateApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateInspectionTemplate(id: string, data: UpdateInspectionTemplateInput) {
  const result = await updateInspectionTemplateApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteInspectionTemplate(id: string) {
  const result = await deleteInspectionTemplateApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createInspectionTemplateItem(templateId: string, data: CreateInspectionTemplateItemInput) {
  const result = await createInspectionTemplateItemApi(templateId, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateInspectionTemplateItem(itemId: string, data: UpdateInspectionTemplateItemInput) {
  const result = await updateInspectionTemplateItemApi(itemId, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteInspectionTemplateItem(itemId: string) {
  const result = await deleteInspectionTemplateItemApi(itemId, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function completeInspection(workOrderId: string, data: InspectionCompleteInput) {
  const result = await completeInspectionApi(workOrderId, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function consumeMaterials(workOrderId: string, data: MaterialConsumeInput) {
  const result = await consumeMaterialsApi(workOrderId, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function uploadWorkOrderImages(workOrderId: string, formData: FormData) {
  const result = await uploadWorkOrderImagesApi(workOrderId, formData, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteWorkOrderImage(workOrderId: string, imageId: string) {
  const result = await deleteWorkOrderImageApi(workOrderId, imageId, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function claimWorkOrder(id: string) {
  const result = await claimWorkOrderApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateClaimTimeoutConfig(data: { emergency?: number; high?: number; medium?: number; low?: number }) {
  const result = await updateClaimTimeoutConfigApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function downloadImportTemplate() {
  const result = await downloadImportTemplateApi(await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function importEquipments(formData: FormData) {
  const result = await importEquipmentsApi(formData, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function addPersonnel(data: Record<string, unknown>) {
  const result = await addPersonnelApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deletePersonnel(id: string) {
  const result = await deletePersonnelApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function assignRoles(personnelId: string, data: Record<string, unknown>) {
  const result = await assignRolesApi(personnelId, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function assignCategories(personnelId: string, data: Record<string, unknown>) {
  const result = await assignCategoriesApi(personnelId, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function refreshFeishu() {
  const result = await refreshFeishuApi(await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function createRole(data: Record<string, unknown>) {
  const result = await createPersonnelRoleApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function updateRole(id: string, data: Record<string, unknown>) {
  const result = await updatePersonnelRoleApi(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function deleteRole(id: string) {
  const result = await deletePersonnelRoleApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}

export async function previewEquipmentImport(data: any) {
  const result = await previewEquipmentImportApi(data, await authHeaders())
  return result as any
}

export async function batchImportEquipment(data: any) {
  const result = await batchImportEquipmentApi(data, await authHeaders())
  revalidatePath('/equipment')
  return result as any
}
