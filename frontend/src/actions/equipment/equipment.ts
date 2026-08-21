'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders, getServerToken, getImpersonateToken } from '@/lib/auth'
import {
  CreateCategoryInput, UpdateCategoryInput, CreateLocationInput, UpdateLocationInput, CreateEquipmentInput, UpdateEquipmentInput,
  CreateFailureCodeInput, UpdateFailureCodeInput,
  CreateWorkOrderInput, UpdateWorkOrderInput, AssignWorkOrderInput, CompleteWorkOrderInput, VerifyWorkOrderInput,
  CreateCalibrationPlanInput, UpdateCalibrationPlanInput, CreateCalibrationRecordInput,
  CreateSparePartInput, UpdateSparePartInput, StockInboundInput, StockAdjustInput,
  CreateMaintenancePlanInput, UpdateMaintenancePlanInput,
  CreateInspectionTemplateInput, UpdateInspectionTemplateInput,
  CreateInspectionTemplateItemInput, UpdateInspectionTemplateItemInput,
  InspectionCompleteInput, MaterialConsumeInput,
} from '@/types/equipment'
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
  createSparePartApi,
  updateSparePartApi,
  deleteSparePartApi,
  stockInboundApi,
  stockAdjustApi,
  createMaintenancePlanApi,
  updateMaintenancePlanApi,
  deleteMaintenancePlanApi,
  createInspectionTemplateApi,
  updateInspectionTemplateApi,
  deleteInspectionTemplateApi,
  createInspectionTemplateItemApi,
  updateInspectionTemplateItemApi,
  deleteInspectionTemplateItemApi,
  completeInspectionApi,
  consumeMaterialsApi,
  uploadWorkOrderImagesApi,
  deleteWorkOrderImageApi,
  claimWorkOrderApi,
  updateClaimTimeoutConfigApi,
  downloadImportTemplateApi,
  importEquipmentsApi,
} from '@/lib/api/server/equipment'

type ActionResult<T = unknown> = { success: true; data: T | null } | { success: false; error: string }


async function wrapApiCall<T>(fn: () => Promise<T>): Promise<ActionResult<T>> {
  try {
    const data = await fn()
    return { success: true, data: data as T }
  } catch (err) {
    const msg = (err as Error).message || '请求失败'
    return { success: false, error: msg }
  }
}

// 设备分类
export async function createCategory(data: CreateCategoryInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createCategoryApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateCategory(id: string, data: UpdateCategoryInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateCategoryApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteCategory(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteCategoryApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// 位置管理
export async function createLocation(data: CreateLocationInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createLocationApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateLocation(id: string, data: UpdateLocationInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateLocationApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteLocation(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteLocationApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// 设备管理
export async function createEquipment(data: CreateEquipmentInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createEquipmentApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateEquipment(id: string, data: UpdateEquipmentInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateEquipmentApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteEquipment(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteEquipmentApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 故障代码 ====================
type FailureCodePath = 'symptoms' | 'causes' | 'actions'

export async function createFailureCode(path: FailureCodePath, data: CreateFailureCodeInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createFailureCodeApi(path, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateFailureCode(path: FailureCodePath, id: string, data: UpdateFailureCodeInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateFailureCodeApi(path, id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteFailureCode(path: FailureCodePath, id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteFailureCodeApi(path, id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 维修工单 ====================
export async function createWorkOrder(data: CreateWorkOrderInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createWorkOrderApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateWorkOrder(id: string, data: UpdateWorkOrderInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateWorkOrderApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function assignWorkOrder(id: string, data: AssignWorkOrderInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => assignWorkOrderApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function startWorkOrder(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => startWorkOrderApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function completeWorkOrder(id: string, data: CompleteWorkOrderInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => completeWorkOrderApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function verifyWorkOrder(id: string, data: VerifyWorkOrderInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => verifyWorkOrderApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function closeWorkOrder(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => closeWorkOrderApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 校准计划 ====================
export async function createCalibrationPlan(data: CreateCalibrationPlanInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createCalibrationPlanApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateCalibrationPlan(id: string, data: UpdateCalibrationPlanInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateCalibrationPlanApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteCalibrationPlan(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteCalibrationPlanApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 校准记录 ====================
export async function createCalibrationRecord(data: CreateCalibrationRecordInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createCalibrationRecordApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 备件管理 ====================
export async function createSparePart(data: CreateSparePartInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createSparePartApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateSparePart(id: string, data: UpdateSparePartInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateSparePartApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteSparePart(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteSparePartApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function stockInbound(sparePartId: string, data: StockInboundInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => stockInboundApi(sparePartId, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function stockAdjust(sparePartId: string, data: StockAdjustInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => stockAdjustApi(sparePartId, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 维护计划 ====================
export async function createMaintenancePlan(data: CreateMaintenancePlanInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createMaintenancePlanApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateMaintenancePlan(id: string, data: UpdateMaintenancePlanInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateMaintenancePlanApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteMaintenancePlan(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteMaintenancePlanApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 巡检模板 ====================
export async function createInspectionTemplate(data: CreateInspectionTemplateInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createInspectionTemplateApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateInspectionTemplate(id: string, data: UpdateInspectionTemplateInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateInspectionTemplateApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteInspectionTemplate(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteInspectionTemplateApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function createInspectionTemplateItem(templateId: string, data: CreateInspectionTemplateItemInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createInspectionTemplateItemApi(templateId, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function updateInspectionTemplateItem(itemId: string, data: UpdateInspectionTemplateItemInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateInspectionTemplateItemApi(itemId, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function deleteInspectionTemplateItem(itemId: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteInspectionTemplateItemApi(itemId, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

export async function completeInspection(workOrderId: string, data: InspectionCompleteInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => completeInspectionApi(workOrderId, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 工单物料领用 ====================
export async function consumeMaterials(workOrderId: string, data: MaterialConsumeInput): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => consumeMaterialsApi(workOrderId, data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 工单图片 ====================
export async function uploadWorkOrderImages(workOrderId: string, formData: FormData): Promise<ActionResult> {
  try {
    const token = await getServerToken()
    const impToken = await getImpersonateToken()
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
    if (impToken) headers['Cookie'] = `impersonate_token=${impToken}`
    const data = await uploadWorkOrderImagesApi(workOrderId, formData, headers)
    revalidatePath('/equipment')
    return { success: true, data }
  } catch (err) {
    return { success: false, error: (err as Error).message || '上传失败' }
  }
}

export async function deleteWorkOrderImage(workOrderId: string, imageId: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteWorkOrderImageApi(workOrderId, imageId, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 抢单 ====================
export async function claimWorkOrder(id: string): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => claimWorkOrderApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== 配置 ====================
export async function updateClaimTimeoutConfig(data: { emergency?: number; high?: number; medium?: number; low?: number }): Promise<ActionResult> {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateClaimTimeoutConfigApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment')
  return result
}

// ==================== Excel 导入 ====================
export interface ImportRowError {
  row: number
  message: string
}

export interface ImportResult {
  imported: number
  skipped: number
  errors: ImportRowError[]
  warnings: ImportRowError[]
}

export async function downloadImportTemplate(): Promise<ActionResult<string>> {
  try {
    const authHeaders = await getAuthHeaders()
    const data = await downloadImportTemplateApi(authHeaders)
    return { success: true, data }
  } catch (err) {
    return { success: false, error: (err as Error).message || '下载模板失败' }
  }
}

export async function importEquipments(formData: FormData): Promise<ActionResult<ImportResult>> {
  try {
    const authHeaders = await getAuthHeaders()
    const { 'Content-Type': _ct, ...uploadHeaders } = authHeaders
    const data = await importEquipmentsApi(formData, uploadHeaders)
    revalidatePath('/equipment')
    return { success: true, data: data as ImportResult }
  } catch (err) {
    return { success: false, error: (err as Error).message || '导入失败' }
  }
}