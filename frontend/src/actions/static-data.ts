'use server'

import type {
  ApiResponse,
  PageParams,
  DictOption,
  WarningsResponse,
} from '@/types/static-data'
import {
  getDictEquipmentCategory as getDictEquipmentCategoryServer,
  getDictEquipmentStatus as getDictEquipmentStatusServer,
  getDictVerifyStatus as getDictVerifyStatusServer,
  getDictChromColumnStatus as getDictChromColumnStatusServer,
  getDictMediumType as getDictMediumTypeServer,
  getDictReagentPurity as getDictReagentPurityServer,
  getDictDangerType as getDictDangerTypeServer,
  getDictStdType as getDictStdTypeServer,
  getDictMaterialType as getDictMaterialTypeServer,
  getDictStandardSource as getDictStandardSourceServer,
  getDictLimitType as getDictLimitTypeServer,
  getDictTestItemCategory as getDictTestItemCategoryServer,
  getDictUnitType as getDictUnitTypeServer,
  getDictLab as getDictLabServer,
  listStorageCondition as listStorageConditionServer,
  getStorageConditionOptions as getStorageConditionOptionsServer,
  getStorageCondition as getStorageConditionServer,
  createStorageCondition as createStorageConditionServer,
  updateStorageCondition as updateStorageConditionServer,
  deleteStorageCondition as deleteStorageConditionServer,
  toggleStorageConditionStatus as toggleStorageConditionStatusServer,
  listUnit as listUnitServer,
  getUnitOptions as getUnitOptionsServer,
  getUnit as getUnitServer,
  createUnit as createUnitServer,
  updateUnit as updateUnitServer,
  deleteUnit as deleteUnitServer,
  listTestItem as listTestItemServer,
  getTestItemOptions as getTestItemOptionsServer,
  getTestItem as getTestItemServer,
  createTestItem as createTestItemServer,
  updateTestItem as updateTestItemServer,
  deleteTestItem as deleteTestItemServer,
  listEquipment as listEquipmentServer,
  getEquipment as getEquipmentServer,
  createEquipment as createEquipmentServer,
  updateEquipment as updateEquipmentServer,
  deleteEquipment as deleteEquipmentServer,
  listChromColumn as listChromColumnServer,
  getChromColumn as getChromColumnServer,
  createChromColumn as createChromColumnServer,
  updateChromColumn as updateChromColumnServer,
  deleteChromColumn as deleteChromColumnServer,
  incrementChromColumnUsage as incrementChromColumnUsageServer,
  listMedium as listMediumServer,
  getMedium as getMediumServer,
  createMedium as createMediumServer,
  updateMedium as updateMediumServer,
  deleteMedium as deleteMediumServer,
  listReagent as listReagentServer,
  getReagent as getReagentServer,
  createReagent as createReagentServer,
  updateReagent as updateReagentServer,
  deleteReagent as deleteReagentServer,
  listStandardMaterial as listStandardMaterialServer,
  getStandardMaterial as getStandardMaterialServer,
  createStandardMaterial as createStandardMaterialServer,
  updateStandardMaterial as updateStandardMaterialServer,
  deleteStandardMaterial as deleteStandardMaterialServer,
  listMaterialStandard as listMaterialStandardServer,
  getMaterialStandard as getMaterialStandardServer,
  createMaterialStandard as createMaterialStandardServer,
  updateMaterialStandard as updateMaterialStandardServer,
  deleteMaterialStandard as deleteMaterialStandardServer,
  listProductStandard as listProductStandardServer,
  getProductStandard as getProductStandardServer,
  createProductStandard as createProductStandardServer,
  updateProductStandard as updateProductStandardServer,
  deleteProductStandard as deleteProductStandardServer,
  getHplcReference as getHplcReferenceServer,
  createHplcReference as createHplcReferenceServer,
  updateHplcReference as updateHplcReferenceServer,
  deleteHplcReference as deleteHplcReferenceServer,
  getWarnings as getWarningsServer,
  listAuditLogs as listAuditLogsServer,
  getAuditModules as getAuditModulesServer,
  uploadFile as uploadFileServer,
  getDownloadUrl as getDownloadUrlServer,
  downloadExcelTemplate as downloadExcelTemplateServer,
  importExcel as importExcelServer,
  exportExcel as exportExcelServer,
} from '@/lib/api/server/static-data'

// ========== 字典接口 ==========

export async function getDictEquipmentCategory() {
  return getDictEquipmentCategoryServer()
}
export async function getDictEquipmentStatus() {
  return getDictEquipmentStatusServer()
}
export async function getDictVerifyStatus() {
  return getDictVerifyStatusServer()
}
export async function getDictChromColumnStatus() {
  return getDictChromColumnStatusServer()
}
export async function getDictMediumType() {
  return getDictMediumTypeServer()
}
export async function getDictReagentPurity() {
  return getDictReagentPurityServer()
}
export async function getDictDangerType() {
  return getDictDangerTypeServer()
}
export async function getDictStdType() {
  return getDictStdTypeServer()
}
export async function getDictMaterialType() {
  return getDictMaterialTypeServer()
}
export async function getDictStandardSource() {
  return getDictStandardSourceServer()
}
export async function getDictLimitType() {
  return getDictLimitTypeServer()
}
export async function getDictTestItemCategory() {
  return getDictTestItemCategoryServer()
}
export async function getDictUnitType() {
  return getDictUnitTypeServer()
}
export async function getDictLab() {
  return getDictLabServer()
}

// ========== 贮存条件字典 ==========

export async function listStorageCondition(params: PageParams & { cond_code?: string; cond_name?: string; status?: number }) {
  return listStorageConditionServer(params as Record<string, unknown>)
}
export async function getStorageConditionOptions() {
  return getStorageConditionOptionsServer()
}
export async function getStorageCondition(id: number) {
  return getStorageConditionServer(id)
}
export async function createStorageCondition(data: any) {
  return createStorageConditionServer(data)
}
export async function updateStorageCondition(id: number, data: any) {
  return updateStorageConditionServer(id, data)
}
export async function deleteStorageCondition(id: number) {
  return deleteStorageConditionServer(id)
}
export async function toggleStorageConditionStatus(id: number) {
  return toggleStorageConditionStatusServer(id)
}

// ========== 计量单位字典 ==========

export async function listUnit(params: PageParams & { unit_code?: string; unit_name?: string; unit_type?: string; status?: number }) {
  return listUnitServer(params as Record<string, unknown>)
}
export async function getUnitOptions() {
  return getUnitOptionsServer()
}
export async function getUnit(id: number) {
  return getUnitServer(id)
}
export async function createUnit(data: any) {
  return createUnitServer(data)
}
export async function updateUnit(id: number, data: any) {
  return updateUnitServer(id, data)
}
export async function deleteUnit(id: number) {
  return deleteUnitServer(id)
}

// ========== 检验项目字典 ==========

export async function listTestItem(params: PageParams & { item_code?: string; item_name?: string; item_category?: string; status?: number }) {
  return listTestItemServer(params as Record<string, unknown>)
}
export async function getTestItemOptions() {
  return getTestItemOptionsServer()
}
export async function getTestItem(id: number) {
  return getTestItemServer(id)
}
export async function createTestItem(data: any) {
  return createTestItemServer(data)
}
export async function updateTestItem(id: number, data: any) {
  return updateTestItemServer(id, data)
}
export async function deleteTestItem(id: number) {
  return deleteTestItemServer(id)
}

// ========== 检测设备台账 ==========

export async function listEquipment(params: PageParams & { eq_code?: string; eq_name?: string; eq_category?: string; eq_status?: number; verify_status?: string }) {
  return listEquipmentServer(params as Record<string, unknown>)
}
export async function getEquipment(id: number) {
  return getEquipmentServer(id)
}
export async function createEquipment(data: any) {
  return createEquipmentServer(data)
}
export async function updateEquipment(id: number, data: any) {
  return updateEquipmentServer(id, data)
}
export async function deleteEquipment(id: number) {
  return deleteEquipmentServer(id)
}

// ========== 色谱柱管理 ==========

export async function listChromColumn(params: PageParams & { col_code?: string; col_type?: string; col_status?: number }) {
  return listChromColumnServer(params as Record<string, unknown>)
}
export async function getChromColumn(id: number) {
  return getChromColumnServer(id)
}
export async function createChromColumn(data: any) {
  return createChromColumnServer(data)
}
export async function updateChromColumn(id: number, data: any) {
  return updateChromColumnServer(id, data)
}
export async function deleteChromColumn(id: number) {
  return deleteChromColumnServer(id)
}
export async function incrementChromColumnUsage(id: number) {
  return incrementChromColumnUsageServer(id)
}

// ========== 培养基管理 ==========

export async function listMedium(params: PageParams & { medium_code?: string; medium_name?: string; medium_type?: string; status?: number }) {
  return listMediumServer(params as Record<string, unknown>)
}
export async function getMedium(id: number) {
  return getMediumServer(id)
}
export async function createMedium(data: any) {
  return createMediumServer(data)
}
export async function updateMedium(id: number, data: any) {
  return updateMediumServer(id, data)
}
export async function deleteMedium(id: number) {
  return deleteMediumServer(id)
}

// ========== 试剂管理 ==========

export async function listReagent(params: PageParams & { reagent_code?: string; reagent_name?: string; danger_type?: string; status?: number }) {
  return listReagentServer(params as Record<string, unknown>)
}
export async function getReagent(id: number) {
  return getReagentServer(id)
}
export async function createReagent(data: any) {
  return createReagentServer(data)
}
export async function updateReagent(id: number, data: any) {
  return updateReagentServer(id, data)
}
export async function deleteReagent(id: number) {
  return deleteReagentServer(id)
}

// ========== 标准物质管理 ==========

export async function listStandardMaterial(params: PageParams & { std_code?: string; std_name?: string; std_type?: string; status?: number }) {
  return listStandardMaterialServer(params as Record<string, unknown>)
}
export async function getStandardMaterial(id: number) {
  return getStandardMaterialServer(id)
}
export async function createStandardMaterial(data: any) {
  return createStandardMaterialServer(data)
}
export async function updateStandardMaterial(id: number, data: any) {
  return updateStandardMaterialServer(id, data)
}
export async function deleteStandardMaterial(id: number) {
  return deleteStandardMaterialServer(id)
}

// ========== 物料质量标准 ==========

export async function listMaterialStandard(params: PageParams & { material_code?: string; material_name?: string; material_type?: string; status?: number }) {
  return listMaterialStandardServer(params as Record<string, unknown>)
}
export async function getMaterialStandard(id: number) {
  return getMaterialStandardServer(id)
}
export async function createMaterialStandard(data: any) {
  return createMaterialStandardServer(data)
}
export async function updateMaterialStandard(id: number, data: any) {
  return updateMaterialStandardServer(id, data)
}
export async function deleteMaterialStandard(id: number) {
  return deleteMaterialStandardServer(id)
}

// ========== 产品质量标准 ==========

export async function listProductStandard(params: PageParams & { product_code?: string; product_name?: string; status?: number }) {
  return listProductStandardServer(params as Record<string, unknown>)
}
export async function getProductStandard(id: number) {
  return getProductStandardServer(id)
}
export async function createProductStandard(data: any) {
  return createProductStandardServer(data)
}
export async function updateProductStandard(id: number, data: any) {
  return updateProductStandardServer(id, data)
}
export async function deleteProductStandard(id: number) {
  return deleteProductStandardServer(id)
}

// ========== 液相色谱对照品 ==========

export async function getHplcReference(id: number) {
  return getHplcReferenceServer(id)
}
export async function createHplcReference(data: any) {
  return createHplcReferenceServer(data)
}
export async function updateHplcReference(id: number, data: any) {
  return updateHplcReferenceServer(id, data)
}
export async function deleteHplcReference(id: number) {
  return deleteHplcReferenceServer(id)
}

// ========== 预警 ==========

export async function getWarnings(days = 30): Promise<ApiResponse<WarningsResponse>> {
  return getWarningsServer(days)
}

// ========== 审计日志 ==========

export interface AuditLogItem {
  id: number
  module_type: string
  record_id: number
  record_code: string | null
  operate_type: string
  operate_by: number
  operate_by_name?: string
  operate_time: string
  old_value: string | null
  new_value: string | null
  change_summary: string | null
}

export async function listAuditLogs(params: {
  page?: number
  page_size?: number
  module_type?: string
  record_id?: number
  operate_by?: number
  operate_type?: string
  start_date?: string
  end_date?: string
}): Promise<ApiResponse<AuditLogItem[]>> {
  return listAuditLogsServer(params as Record<string, unknown>)
}

export async function getAuditModules(): Promise<ApiResponse<{ module_type: string; module_label: string }[]>> {
  return getAuditModulesServer()
}

// ========== 文件上传下载 ==========

export interface UploadResponse {
  file_id: string
  original_name: string
  stored_name: string
  url: string
  size: number
  content_type: string
}

export async function uploadFile(file: File): Promise<ApiResponse<UploadResponse>> {
  const formData = new FormData()
  formData.append('file', file)
  return uploadFileServer(formData)
}

export async function getDownloadUrl(filename: string): Promise<string> {
  return getDownloadUrlServer(filename)
}

// ========== Excel 导入导出 ==========

export async function downloadExcelTemplate(moduleType: string): Promise<Blob> {
  return downloadExcelTemplateServer(moduleType)
}

export async function importExcel(moduleType: string, file: File): Promise<ApiResponse<{ success: number; failed: number; errors: string[] }>> {
  const formData = new FormData()
  formData.append('file', file)
  return importExcelServer(moduleType, formData)
}

export async function exportExcel(params: {
  module_type: string
  keyword?: string
  status?: number
  start_date?: string
  end_date?: string
}): Promise<Blob> {
  return exportExcelServer(params as Record<string, unknown>)
}