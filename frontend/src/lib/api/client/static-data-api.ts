/**
 * 业务静态数据模块 — 客户端直连 API 客户端
 * 列表查询走客户端 fetch，避免 Server Action 在 Next.js 服务端的网络隔离问题
 * 新建/编辑/删除/上传等写操作仍通过 Server Action（需要 auth context）
 */

const API_BASE = '/api/v1'
const PREFIX = '/quality/static-data'

async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`)
  return data as T
}

// ========== 贮存条件 ==========
export async function listStorageCondition(params: {
  page?: number; page_size?: number;
  cond_code?: string; cond_name?: string; status?: number;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.cond_code) qs.set('cond_code', params.cond_code)
  if (params.cond_name) qs.set('cond_name', params.cond_name)
  if (params.status !== undefined) qs.set('status', String(params.status))
  return api(`${PREFIX}/storage-condition?${qs}`)
}

export async function getStorageCondition(id: number) {
  return api(`${PREFIX}/storage-condition/${id}`)
}

export async function createStorageCondition(data: Record<string, any>) {
  const res = await fetch(`${API_BASE}${PREFIX}/storage-condition`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function updateStorageCondition(id: number, data: Record<string, any>) {
  const res = await fetch(`${API_BASE}${PREFIX}/storage-condition/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function deleteStorageCondition(id: number) {
  const res = await fetch(`${API_BASE}${PREFIX}/storage-condition/${id}`, {
    method: 'DELETE',
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

// ========== 计量单位 ==========
export async function listUnit(params: {
  page?: number; page_size?: number;
  unit_code?: string; unit_name?: string; unit_type?: string; status?: number;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.unit_code) qs.set('unit_code', params.unit_code)
  if (params.unit_name) qs.set('unit_name', params.unit_name)
  if (params.unit_type) qs.set('unit_type', params.unit_type)
  if (params.status !== undefined) qs.set('status', String(params.status))
  return api(`${PREFIX}/unit?${qs}`)
}

// ========== 检验项目 ==========
export async function listTestItem(params: {
  page?: number; page_size?: number;
  item_code?: string; item_name?: string; item_category?: string; status?: number;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.item_code) qs.set('item_code', params.item_code)
  if (params.item_name) qs.set('item_name', params.item_name)
  if (params.item_category) qs.set('item_category', params.item_category)
  if (params.status !== undefined) qs.set('status', String(params.status))
  return api(`${PREFIX}/test-item?${qs}`)
}

// ========== 检测设备 ==========
export async function listEquipment(params: {
  page?: number; page_size?: number;
  eq_code?: string; eq_name?: string; eq_category?: string; eq_status?: number; verify_status?: string;
  start_date?: string; end_date?: string;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.eq_code) qs.set('eq_code', params.eq_code)
  if (params.eq_name) qs.set('eq_name', params.eq_name)
  if (params.eq_category) qs.set('eq_category', params.eq_category)
  if (params.eq_status !== undefined) qs.set('eq_status', String(params.eq_status))
  if (params.verify_status) qs.set('verify_status', params.verify_status)
  if (params.start_date) qs.set('start_date', params.start_date)
  if (params.end_date) qs.set('end_date', params.end_date)
  return api(`${PREFIX}/equipment?${qs}`)
}

// ========== 色谱柱 ==========
export async function listChromColumn(params: {
  page?: number; page_size?: number;
  col_code?: string; col_type?: string; col_status?: number;
  manufacturer?: string; spec?: string; column_category?: number;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.col_code) qs.set('col_code', params.col_code)
  if (params.col_type) qs.set('col_type', params.col_type)
  if (params.col_status !== undefined) qs.set('col_status', String(params.col_status))
  if (params.manufacturer) qs.set('manufacturer', params.manufacturer)
  if (params.spec) qs.set('spec', params.spec)
  if (params.column_category !== undefined) qs.set('column_category', String(params.column_category))
  return api(`${PREFIX}/chrom-column?${qs}`)
}

export async function downloadChromColumnTemplate() {
  const res = await fetch(`${API_BASE}${PREFIX}/chrom-column/template`)
  if (!res.ok) throw new Error('Download failed')
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '色谱柱导入模板.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export async function batchImportChromColumn(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}${PREFIX}/chrom-column/batch-import`, {
    method: 'POST',
    body: formData,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`)
  return data
}

export async function adjustHplcReferenceQuantity(id: number, quantity_change: number) {
  const res = await fetch(`${API_BASE}${PREFIX}/hplc-reference/${id}/adjust-quantity`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity_change }),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function consumeHplcReference(
  id: number,
  data: {
    usage_amount: number
    usage_unit?: string
    usage_person?: string
    usage_purpose?: string
    remark?: string
  },
) {
  const res = await fetch(`${API_BASE}${PREFIX}/hplc-reference/${id}/use`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function getHplcReferenceUsageHistory(id: number, page = 1, page_size = 20) {
  const qs = new URLSearchParams()
  qs.set('page', String(page))
  qs.set('page_size', String(page_size))
  return api(`${PREFIX}/hplc-reference/${id}/usage-history?${qs}`)
}

export async function getHplcReferencesNeedRecal() {
  return api(`${PREFIX}/hplc-reference/need-recal`)
}

// ========== 培养基 ==========
export async function listMedium(params: {
  page?: number; page_size?: number;
  medium_code?: string; medium_name?: string; medium_type?: string; status?: number;
  expire_start?: string; expire_end?: string;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.medium_code) qs.set('medium_code', params.medium_code)
  if (params.medium_name) qs.set('medium_name', params.medium_name)
  if (params.medium_type) qs.set('medium_type', params.medium_type)
  if (params.status !== undefined) qs.set('status', String(params.status))
  if (params.expire_start) qs.set('expire_start', params.expire_start)
  if (params.expire_end) qs.set('expire_end', params.expire_end)
  return api(`${PREFIX}/medium?${qs}`)
}

export async function getMedium(id: number) {
  return api(`${PREFIX}/medium/${id}`)
}

export async function createMedium(data: Record<string, any>) {
  const res = await fetch(`${API_BASE}${PREFIX}/medium`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function updateMedium(id: number, data: Record<string, any>) {
  const res = await fetch(`${API_BASE}${PREFIX}/medium/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function deleteMedium(id: number) {
  const res = await fetch(`${API_BASE}${PREFIX}/medium/${id}`, {
    method: 'DELETE',
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function adjustMediumStock(id: number, quantity: number) {
  const res = await fetch(`${API_BASE}${PREFIX}/medium/${id}/adjust-stock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity }),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

// ========== 标准品 ==========
export async function listStandard(params: {
  page?: number; page_size?: number;
  std_code?: string; std_name?: string; std_type?: string; std_status?: number;
  manufacturer?: string;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.std_code) qs.set('std_code', params.std_code)
  if (params.std_name) qs.set('std_name', params.std_name)
  if (params.std_type) qs.set('std_type', params.std_type)
  if (params.std_status !== undefined) qs.set('std_status', String(params.std_status))
  if (params.manufacturer) qs.set('manufacturer', params.manufacturer)
  return api(`${PREFIX}/standard?${qs}`)
}

export async function getStandard(id: number) {
  return api(`${PREFIX}/standard/${id}`)
}

export async function createStandard(data: Record<string, any>) {
  const res = await fetch(`${API_BASE}${PREFIX}/standard`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function updateStandard(id: number, data: Record<string, any>) {
  const res = await fetch(`${API_BASE}${PREFIX}/standard/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function deleteStandard(id: number) {
  const res = await fetch(`${API_BASE}${PREFIX}/standard/${id}`, {
    method: 'DELETE',
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

export async function adjustStandardQuantity(id: number, quantity: number) {
  const res = await fetch(`${API_BASE}${PREFIX}/standard/${id}/adjust-quantity`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity }),
  })
  const result = await res.json()
  if (!res.ok) throw new Error(result.message || `HTTP ${res.status}`)
  return result
}

// ========== 试剂 ==========
export async function listReagent(params: {
  page?: number; page_size?: number;
  reagent_code?: string; reagent_name?: string; danger_type?: string; status?: number;
  expire_start?: string; expire_end?: string;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.reagent_code) qs.set('reagent_code', params.reagent_code)
  if (params.reagent_name) qs.set('reagent_name', params.reagent_name)
  if (params.danger_type) qs.set('danger_type', params.danger_type)
  if (params.status !== undefined) qs.set('status', String(params.status))
  if (params.expire_start) qs.set('expire_start', params.expire_start)
  if (params.expire_end) qs.set('expire_end', params.expire_end)
  return api(`${PREFIX}/reagent?${qs}`)
}

// ========== 标准物质 ==========
export async function listStandardMaterial(params: {
  page?: number; page_size?: number;
  std_code?: string; std_name?: string; std_type?: string; status?: number;
  expire_start?: string; expire_end?: string;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.std_code) qs.set('std_code', params.std_code)
  if (params.std_name) qs.set('std_name', params.std_name)
  if (params.std_type) qs.set('std_type', params.std_type)
  if (params.status !== undefined) qs.set('status', String(params.status))
  if (params.expire_start) qs.set('expire_start', params.expire_start)
  if (params.expire_end) qs.set('expire_end', params.expire_end)
  return api(`${PREFIX}/standard-material?${qs}`)
}

// ========== 物料质量标准 ==========
export async function listMaterialStandard(params: {
  page?: number; page_size?: number;
  material_code?: string; material_name?: string; material_type?: string; status?: number;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.material_code) qs.set('material_code', params.material_code)
  if (params.material_name) qs.set('material_name', params.material_name)
  if (params.material_type) qs.set('material_type', params.material_type)
  if (params.status !== undefined) qs.set('status', String(params.status))
  return api(`${PREFIX}/material-standard?${qs}`)
}

// ========== 产品质量标准 ==========
export async function listProductStandard(params: {
  page?: number; page_size?: number;
  product_code?: string; product_name?: string; status?: number;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.product_code) qs.set('product_code', params.product_code)
  if (params.product_name) qs.set('product_name', params.product_name)
  if (params.status !== undefined) qs.set('status', String(params.status))
  return api(`${PREFIX}/product-standard?${qs}`)
}

// ========== 液相色谱对照品 ==========
export async function listHplcReference(params: {
  page?: number; page_size?: number;
  ref_code?: string; ref_name?: string; project_name?: string; ref_status?: number;
  expire_start?: string; expire_end?: string;
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.ref_code) qs.set('ref_code', params.ref_code)
  if (params.ref_name) qs.set('ref_name', params.ref_name)
  if (params.project_name) qs.set('project_name', params.project_name)
  if (params.ref_status !== undefined) qs.set('ref_status', String(params.ref_status))
  if (params.expire_start) qs.set('expire_start', params.expire_start)
  if (params.expire_end) qs.set('expire_end', params.expire_end)
  return api(`${PREFIX}/hplc-reference?${qs}`)
}

// ========== 液相色谱对照品 - 模板下载 ==========
export async function downloadHplcReferenceTemplate() {
  const res = await fetch(`${API_BASE}${PREFIX}/hplc-reference/template`)
  if (!res.ok) throw new Error('Download failed')
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'hplc_reference_template.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

// ========== 液相色谱对照品 - 批量导入 ==========
export async function batchImportHplcReference(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}${PREFIX}/hplc-reference/batch-import`, {
    method: 'POST',
    body: formData,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`)
  return data
}