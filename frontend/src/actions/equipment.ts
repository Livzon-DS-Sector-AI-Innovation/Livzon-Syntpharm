'use server'

import { revalidatePath } from 'next/cache'
import { getServerToken } from '@/lib/auth'
import type { components } from '@/types/generated/schema'
type CreateRoleInput = components['schemas']['RoleCreate']
type UpdateRoleInput = components['schemas']['RoleUpdate']
type AddPersonnelInput = components['schemas']['SpecialOperationPersonnelCreate']
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
} from '@/types/equipment/generated-bridge'

import {
  createCategoryApiTyped, updateCategoryApiTyped, deleteCategoryApi,
  createLocationApiTyped, updateLocationApiTyped, deleteLocationApi,
  createEquipmentApiTyped, updateEquipmentApiTyped, deleteEquipmentApi, batchDeleteEquipmentsApi,
  createFailureCodeApiTyped, updateFailureCodeApiTyped, deleteFailureCodeApi,
  createWorkOrderApiTyped, updateWorkOrderApiTyped, assignWorkOrderApiTyped,
  startWorkOrderApi, completeWorkOrderApiTyped, verifyWorkOrderApiTyped, closeWorkOrderApi,
  createCalibrationPlanApiTyped, updateCalibrationPlanApiTyped, deleteCalibrationPlanApi,
  createCalibrationRecordApiTyped,
  createSparePartApiTyped, updateSparePartApiTyped, deleteSparePartApi,
  stockInboundApiTyped, stockAdjustApiTyped,
  createMaintenancePlanApiTyped, updateMaintenancePlanApiTyped, deleteMaintenancePlanApi,
  createInspectionTemplateApiTyped, updateInspectionTemplateApiTyped, deleteInspectionTemplateApi,
  createInspectionTemplateItemApiTyped, updateInspectionTemplateItemApiTyped, deleteInspectionTemplateItemApi,
  completeInspectionApiTyped, consumeMaterialsApiTyped,
  uploadWorkOrderImagesApi, deleteWorkOrderImageApi,
  claimWorkOrderApi, updateClaimTimeoutConfigApiTyped,
  downloadImportTemplateApi, importEquipmentsApi,
  previewEquipmentImportApiTyped, batchImportEquipmentApiTyped,
  createPersonnelRoleApiTyped, updatePersonnelRoleApiTyped, deletePersonnelRoleApi,
  addPersonnelApiTyped, deletePersonnelApi, assignRolesApiTyped, assignCategoriesApiTyped, refreshFeishuApi,
} from '@/lib/api/server/equipment'

async function authHeaders(): Promise<Record<string, string>> {
  return { Authorization: `Bearer ${await getServerToken()}` }
}

type FailureCodePath = 'symptoms' | 'causes' | 'actions'

export async function createCategory(data: CreateCategoryInput) {
  const result = await createCategoryApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateCategory(id: string, data: UpdateCategoryInput) {
  const result = await updateCategoryApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteCategory(id: string) {
  const result = await deleteCategoryApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createLocation(data: CreateLocationInput) {
  const result = await createLocationApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateLocation(id: string, data: UpdateLocationInput) {
  const result = await updateLocationApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteLocation(id: string) {
  const result = await deleteLocationApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createEquipment(data: CreateEquipmentInput) {
  const result = await createEquipmentApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateEquipment(id: string, data: UpdateEquipmentInput) {
  const result = await updateEquipmentApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteEquipment(id: string) {
  const result = await deleteEquipmentApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createFailureCode(path: FailureCodePath, data: CreateFailureCodeInput) {
  const result = await createFailureCodeApiTyped(path, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateFailureCode(path: FailureCodePath, id: string, data: UpdateFailureCodeInput) {
  const result = await updateFailureCodeApiTyped(path, id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteFailureCode(path: FailureCodePath, id: string) {
  const result = await deleteFailureCodeApi(path, id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createWorkOrder(data: CreateWorkOrderInput) {
  const result = await createWorkOrderApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateWorkOrder(id: string, data: UpdateWorkOrderInput) {
  const result = await updateWorkOrderApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function assignWorkOrder(id: string, data: AssignWorkOrderInput) {
  const result = await assignWorkOrderApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function startWorkOrder(id: string) {
  const result = await startWorkOrderApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function completeWorkOrder(id: string, data: CompleteWorkOrderInput) {
  const result = await completeWorkOrderApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function verifyWorkOrder(id: string, data: VerifyWorkOrderInput) {
  const result = await verifyWorkOrderApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function closeWorkOrder(id: string) {
  const result = await closeWorkOrderApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createCalibrationPlan(data: CreateCalibrationPlanInput) {
  const result = await createCalibrationPlanApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateCalibrationPlan(id: string, data: UpdateCalibrationPlanInput) {
  const result = await updateCalibrationPlanApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteCalibrationPlan(id: string) {
  const result = await deleteCalibrationPlanApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createCalibrationRecord(data: CreateCalibrationRecordInput) {
  const result = await createCalibrationRecordApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createSparePart(data: CreateSparePartInput) {
  const result = await createSparePartApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateSparePart(id: string, data: UpdateSparePartInput) {
  const result = await updateSparePartApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteSparePart(id: string) {
  const result = await deleteSparePartApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function stockInbound(sparePartId: string, data: StockInboundInput) {
  const result = await stockInboundApiTyped(sparePartId, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function stockAdjust(sparePartId: string, data: StockAdjustInput) {
  const result = await stockAdjustApiTyped(sparePartId, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createMaintenancePlan(data: CreateMaintenancePlanInput) {
  const result = await createMaintenancePlanApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateMaintenancePlan(id: string, data: UpdateMaintenancePlanInput) {
  const result = await updateMaintenancePlanApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteMaintenancePlan(id: string) {
  const result = await deleteMaintenancePlanApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createInspectionTemplate(data: CreateInspectionTemplateInput) {
  const result = await createInspectionTemplateApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateInspectionTemplate(id: string, data: UpdateInspectionTemplateInput) {
  const result = await updateInspectionTemplateApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteInspectionTemplate(id: string) {
  const result = await deleteInspectionTemplateApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createInspectionTemplateItem(templateId: string, data: CreateInspectionTemplateItemInput) {
  const result = await createInspectionTemplateItemApiTyped(templateId, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateInspectionTemplateItem(itemId: string, data: UpdateInspectionTemplateItemInput) {
  const result = await updateInspectionTemplateItemApiTyped(itemId, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteInspectionTemplateItem(itemId: string) {
  const result = await deleteInspectionTemplateItemApi(itemId, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function completeInspection(workOrderId: string, data: InspectionCompleteInput) {
  const result = await completeInspectionApiTyped(workOrderId, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function consumeMaterials(workOrderId: string, data: MaterialConsumeInput) {
  const result = await consumeMaterialsApiTyped(workOrderId, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function uploadWorkOrderImages(workOrderId: string, formData: FormData) {
  const result = await uploadWorkOrderImagesApi(workOrderId, formData, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteWorkOrderImage(workOrderId: string, imageId: string) {
  const result = await deleteWorkOrderImageApi(workOrderId, imageId, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function claimWorkOrder(id: string) {
  const result = await claimWorkOrderApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateClaimTimeoutConfig(data: { emergency?: number; high?: number; medium?: number; low?: number }) {
  const result = await updateClaimTimeoutConfigApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function downloadImportTemplate() {
  const result = await downloadImportTemplateApi(await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function importEquipments(formData: FormData) {
  const result = await importEquipmentsApi(formData, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function addPersonnel(data: components['schemas']['PersonnelAddRequest']) {
  const result = await addPersonnelApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deletePersonnel(id: string) {
  const result = await deletePersonnelApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function assignRoles(personnelId: string, data: components['schemas']['PersonnelRoleAssign']) {
  const result = await assignRolesApiTyped(personnelId, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function assignCategories(personnelId: string, data: components['schemas']['PersonnelCategoryAssign']) {
  const result = await assignCategoriesApiTyped(personnelId, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function refreshFeishu() {
  const result = await refreshFeishuApi(await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function createRole(data: components['schemas']['RoleCreate']) {
  const result = await createPersonnelRoleApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function updateRole(id: string, data: Record<string, unknown>) {
  const result = await updatePersonnelRoleApiTyped(id, data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function deleteRole(id: string) {
  const result = await deletePersonnelRoleApi(id, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function previewEquipmentImport(data: any) {
  console.log('[DEBUG] previewEquipmentImport called with:', {
    dataLength: data?.length,
    firstItem: data?.[0],
    firstItemType: typeof data?.[0],
  })
  const result = await previewEquipmentImportApiTyped(data, await authHeaders())
  return result
}

export async function batchImportEquipment(data: any) {
  const result = await batchImportEquipmentApiTyped(data, await authHeaders())
  revalidatePath('/equipment')
  return result
}

export async function batchDeleteEquipments(ids: string[]) {
  const result = await batchDeleteEquipmentsApi(ids, await authHeaders())
  revalidatePath('/equipment')
  return result
}
