import { apiFetch, API_BASE_URL } from '@/lib/api/server/base'

const PREFIX = '/quality/static-data'

async function uploadFetch<T = any>(url: string, formData: FormData): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`
  const response = await fetch(fullUrl, {
    method: 'POST',
    body: formData,
    cache: 'no-store',
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.message || `HTTP ${response.status}`)
  }
  return response.json()
}

async function blobFetch(url: string): Promise<Blob> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`
  const response = await fetch(fullUrl, {
    cache: 'no-store',
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.blob()
}

// ===== 字典接口 =====

export async function getDictEquipmentCategory() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/equipment-category`)
}

export async function getDictEquipmentStatus() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/equipment-status`)
}

export async function getDictVerifyStatus() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/verify-status`)
}

export async function getDictChromColumnStatus() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/chrom-column-status`)
}

export async function getDictMediumType() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/medium-type`)
}

export async function getDictReagentPurity() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/reagent-purity`)
}

export async function getDictDangerType() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/danger-type`)
}

export async function getDictStdType() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/std-type`)
}

export async function getDictMaterialType() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/material-type`)
}

export async function getDictStandardSource() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/standard-source`)
}

export async function getDictLimitType() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/limit-type`)
}

export async function getDictTestItemCategory() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/test-item-category`)
}

export async function getDictUnitType() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/unit-type`)
}

export async function getDictLab() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/dict/lab`)
}

// ===== 贮存条件字典 =====

export async function listStorageCondition(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.cond_code) qs.set('cond_code', String(params.cond_code))
  if (params.cond_name) qs.set('cond_name', String(params.cond_name))
  if (params.status !== undefined) qs.set('status', String(params.status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/storage-condition?${qs}`)
}

export async function getStorageConditionOptions() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/storage-condition/options`)
}

export async function getStorageCondition(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/storage-condition/${id}`)
}

export async function createStorageCondition(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/storage-condition`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStorageCondition(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/storage-condition/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteStorageCondition(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/storage-condition/${id}`, {
    method: 'DELETE',
  })
}

export async function toggleStorageConditionStatus(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/storage-condition/${id}/toggle-status`, {
    method: 'POST',
  })
}

// ===== 计量单位字典 =====

export async function listUnit(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.unit_code) qs.set('unit_code', String(params.unit_code))
  if (params.unit_name) qs.set('unit_name', String(params.unit_name))
  if (params.unit_type) qs.set('unit_type', String(params.unit_type))
  if (params.status !== undefined) qs.set('status', String(params.status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/unit?${qs}`)
}

export async function getUnitOptions() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/unit/options`)
}

export async function getUnit(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/unit/${id}`)
}

export async function createUnit(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/unit`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateUnit(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/unit/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteUnit(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/unit/${id}`, {
    method: 'DELETE',
  })
}

// ===== 检验项目字典 =====

export async function listTestItem(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.item_code) qs.set('item_code', String(params.item_code))
  if (params.item_name) qs.set('item_name', String(params.item_name))
  if (params.item_category) qs.set('item_category', String(params.item_category))
  if (params.status !== undefined) qs.set('status', String(params.status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/test-item?${qs}`)
}

export async function getTestItemOptions() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/test-item/options`)
}

export async function getTestItem(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/test-item/${id}`)
}

export async function createTestItem(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/test-item`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTestItem(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/test-item/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTestItem(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/test-item/${id}`, {
    method: 'DELETE',
  })
}

// ===== 检测设备台账 =====

export async function listEquipment(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.eq_code) qs.set('eq_code', String(params.eq_code))
  if (params.eq_name) qs.set('eq_name', String(params.eq_name))
  if (params.eq_category) qs.set('eq_category', String(params.eq_category))
  if (params.eq_status !== undefined) qs.set('eq_status', String(params.eq_status))
  if (params.verify_status) qs.set('verify_status', String(params.verify_status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/equipment?${qs}`)
}

export async function getEquipment(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/equipment/${id}`)
}

export async function createEquipment(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/equipment`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEquipment(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/equipment/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteEquipment(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/equipment/${id}`, {
    method: 'DELETE',
  })
}

// ===== 色谱柱管理 =====

export async function listChromColumn(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.col_code) qs.set('col_code', String(params.col_code))
  if (params.col_type) qs.set('col_type', String(params.col_type))
  if (params.col_status !== undefined) qs.set('col_status', String(params.col_status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/chrom-column?${qs}`)
}

export async function getChromColumn(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/chrom-column/${id}`)
}

export async function createChromColumn(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/chrom-column`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateChromColumn(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/chrom-column/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteChromColumn(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/chrom-column/${id}`, {
    method: 'DELETE',
  })
}

export async function incrementChromColumnUsage(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/chrom-column/${id}/increment-usage`, {
    method: 'POST',
  })
}

// ===== 培养基管理 =====

export async function listMedium(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.medium_code) qs.set('medium_code', String(params.medium_code))
  if (params.medium_name) qs.set('medium_name', String(params.medium_name))
  if (params.medium_type) qs.set('medium_type', String(params.medium_type))
  if (params.status !== undefined) qs.set('status', String(params.status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/medium?${qs}`)
}

export async function getMedium(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/medium/${id}`)
}

export async function createMedium(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/medium`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateMedium(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/medium/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteMedium(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/medium/${id}`, {
    method: 'DELETE',
  })
}

// ===== 试剂管理 =====

export async function listReagent(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.reagent_code) qs.set('reagent_code', String(params.reagent_code))
  if (params.reagent_name) qs.set('reagent_name', String(params.reagent_name))
  if (params.danger_type) qs.set('danger_type', String(params.danger_type))
  if (params.status !== undefined) qs.set('status', String(params.status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/reagent?${qs}`)
}

export async function getReagent(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/reagent/${id}`)
}

export async function createReagent(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/reagent`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateReagent(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/reagent/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteReagent(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/reagent/${id}`, {
    method: 'DELETE',
  })
}

// ===== 标准物质管理 =====

export async function listStandardMaterial(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.std_code) qs.set('std_code', String(params.std_code))
  if (params.std_name) qs.set('std_name', String(params.std_name))
  if (params.std_type) qs.set('std_type', String(params.std_type))
  if (params.status !== undefined) qs.set('status', String(params.status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/standard-material?${qs}`)
}

export async function getStandardMaterial(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/standard-material/${id}`)
}

export async function createStandardMaterial(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/standard-material`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStandardMaterial(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/standard-material/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteStandardMaterial(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/standard-material/${id}`, {
    method: 'DELETE',
  })
}

// ===== 物料质量标准 =====

export async function listMaterialStandard(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.material_code) qs.set('material_code', String(params.material_code))
  if (params.material_name) qs.set('material_name', String(params.material_name))
  if (params.material_type) qs.set('material_type', String(params.material_type))
  if (params.status !== undefined) qs.set('status', String(params.status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/material-standard?${qs}`)
}

export async function getMaterialStandard(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/material-standard/${id}`)
}

export async function createMaterialStandard(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/material-standard`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateMaterialStandard(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/material-standard/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteMaterialStandard(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/material-standard/${id}`, {
    method: 'DELETE',
  })
}

// ===== 产品质量标准 =====

export async function listProductStandard(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.product_code) qs.set('product_code', String(params.product_code))
  if (params.product_name) qs.set('product_name', String(params.product_name))
  if (params.status !== undefined) qs.set('status', String(params.status))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/product-standard?${qs}`)
}

export async function getProductStandard(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/product-standard/${id}`)
}

export async function createProductStandard(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/product-standard`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProductStandard(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/product-standard/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteProductStandard(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/product-standard/${id}`, {
    method: 'DELETE',
  })
}

// ===== 液相色谱对照品 =====

export async function getHplcReference(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/hplc-reference/${id}`)
}

export async function createHplcReference(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/hplc-reference`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateHplcReference(id: number, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/hplc-reference/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteHplcReference(id: number) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/hplc-reference/${id}`, {
    method: 'DELETE',
  })
}

// ===== 预警 =====

export async function getWarnings(days: number = 30) {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/warnings?days=${days}`)
}

// ===== 审计日志 =====

export async function listAuditLogs(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.module_type) qs.set('module_type', String(params.module_type))
  if (params.record_id !== undefined) qs.set('record_id', String(params.record_id))
  if (params.operate_by !== undefined) qs.set('operate_by', String(params.operate_by))
  if (params.operate_type) qs.set('operate_type', String(params.operate_type))
  if (params.start_date) qs.set('start_date', String(params.start_date))
  if (params.end_date) qs.set('end_date', String(params.end_date))
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/audit?${qs}`)
}

export async function getAuditModules() {
  return apiFetch(`${API_BASE_URL}/api/v1${PREFIX}/audit/modules`)
}

// ===== 文件上传下载 =====

export async function uploadFile(formData: FormData) {
  return uploadFetch(`${API_BASE_URL}/api/v1${PREFIX}/upload`, formData)
}

export async function getDownloadUrl(filename: string) {
  return `${API_BASE_URL}/api/v1${PREFIX}/download/${encodeURIComponent(filename)}`
}

// ===== Excel 导入导出 =====

export async function downloadExcelTemplate(moduleType: string) {
  return blobFetch(`${API_BASE_URL}/api/v1${PREFIX}/excel/template/${moduleType}`)
}

export async function importExcel(moduleType: string, formData: FormData) {
  return uploadFetch(`${API_BASE_URL}/api/v1${PREFIX}/excel/import/${moduleType}`, formData)
}

export async function exportExcel(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.keyword) qs.set('keyword', String(params.keyword))
  if (params.status !== undefined) qs.set('status', String(params.status))
  if (params.start_date) qs.set('start_date', String(params.start_date))
  if (params.end_date) qs.set('end_date', String(params.end_date))
  return blobFetch(`${API_BASE_URL}/api/v1${PREFIX}/excel/export/${params.module_type}?${qs}`)
}