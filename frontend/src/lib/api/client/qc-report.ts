/**
 * 质量检验台账：浏览器侧请求。
 *
 * 上传是本模块唯一走客户端直连的场景：Server Action 请求体默认上限 1MB，
 * 结果表动辄几百 KB 到数 MB，必须由浏览器直接提交并显示进度。
 */

import type {
  QcBatchImportResult,
  QcBatchPageData,
  QcImportCommitResult,
  QcImportPreview,
  QcItem,
  QcItemUpdatePayload,
  QcProductListItem,
  QcRejudgeResult,
  QcStats,
} from '@/types/qc-report'

const BASE = '/api/v1/quality/qc-report'

async function qcRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: 'no-store', ...init })
  if (!response.ok) {
    let message = `请求失败（${response.status}）`
    try {
      const body = await response.json()
      if (body?.message) message = body.message
      else if (typeof body?.detail === 'string') message = body.detail
    } catch {
      // 非 JSON 响应，保留默认文案
    }
    throw new Error(message)
  }
  const payload = await response.json()
  return payload.data as T
}

export async function fetchQcProductsClient(params?: {
  keyword?: string
  category?: string
  top_level?: string
}): Promise<QcProductListItem[]> {
  const search = new URLSearchParams()
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.category) search.set('category', params.category)
  if (params?.top_level) search.set('top_level', params.top_level)
  const query = search.toString()
  return qcRequest<QcProductListItem[]>(`${BASE}/products${query ? `?${query}` : ''}`)
}

export async function fetchQcBatchesClient(params: {
  productId: string
  page?: number
  page_size?: number
  batch_no?: string
  level?: string
}): Promise<QcBatchPageData> {
  const search = new URLSearchParams()
  if (params.page) search.set('page', String(params.page))
  if (params.page_size) search.set('page_size', String(params.page_size))
  if (params.batch_no) search.set('batch_no', params.batch_no)
  if (params.level) search.set('level', params.level)
  return qcRequest<QcBatchPageData>(`${BASE}/products/${params.productId}/batches?${search.toString()}`)
}

export async function fetchQcStatsClient(productId: string): Promise<QcStats> {
  return qcRequest<QcStats>(`${BASE}/products/${productId}/stats`)
}

async function postFiles(
  path: string,
  standardFile: File,
  resultFile: File,
  extra: Record<string, string>,
): Promise<QcImportPreview | QcImportCommitResult> {
  const form = new FormData()
  form.append('standard_file', standardFile)
  form.append('result_file', resultFile)
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') form.append(key, value)
  })
  return qcRequest<QcImportPreview | QcImportCommitResult>(path, { method: 'POST', body: form })
}

export async function previewQcImport(
  standardFile: File,
  resultFile: File,
  productId?: string,
  mapping?: Record<string, string>,
): Promise<QcImportPreview> {
  const extra: Record<string, string> = {}
  if (productId) extra.product_id = productId
  if (mapping && Object.keys(mapping).length > 0) {
    extra.manual_mapping = JSON.stringify(mapping)
  }
  return (await postFiles(`${BASE}/import/preview`, standardFile, resultFile, extra)) as QcImportPreview
}

export async function commitQcImport(payload: {
  standardFile: File
  resultFile: File
  name: string
  abbr: string
  category: string
  qualityStandard?: string
  manualMapping?: Record<string, string>
  /** 冲突裁决：{"列号|层": "docx" | "excel" | "none"} */
  resolutions?: Record<string, string>
}): Promise<QcImportCommitResult> {
  const extra: Record<string, string> = {
    name: payload.name,
    abbr: payload.abbr,
    category: payload.category,
  }
  if (payload.qualityStandard) extra.quality_standard = payload.qualityStandard
  if (payload.manualMapping && Object.keys(payload.manualMapping).length > 0) {
    extra.manual_mapping = JSON.stringify(payload.manualMapping)
  }
  if (payload.resolutions && Object.keys(payload.resolutions).length > 0) {
    extra.resolutions = JSON.stringify(payload.resolutions)
  }
  return (await postFiles(
    `${BASE}/import/commit`,
    payload.standardFile,
    payload.resultFile,
    extra,
  )) as QcImportCommitResult
}

export interface QcImportProgress {
  stage: 'uploading' | 'parsing' | 'writing'
  /** 0–100，来自上传字节数或服务端真实处理量 */
  percent: number
  /** 服务端给的进度描述，如「已写入 8000 / 46740 条检验值」 */
  message?: string
}

interface ServerProgressEvent {
  stage: 'parsing' | 'writing' | 'done' | 'error'
  percent?: number
  message?: string
  result?: QcImportCommitResult
}

function buildCommitForm(payload: {
  standardFile: File
  resultFile: File
  name: string
  abbr: string
  category: string
  qualityStandard?: string
  manualMapping?: Record<string, string>
  resolutions?: Record<string, string>
}): FormData {
  const form = new FormData()
  form.append('standard_file', payload.standardFile)
  form.append('result_file', payload.resultFile)
  form.append('name', payload.name)
  form.append('abbr', payload.abbr)
  form.append('category', payload.category)
  if (payload.qualityStandard) form.append('quality_standard', payload.qualityStandard)
  if (payload.manualMapping && Object.keys(payload.manualMapping).length > 0) {
    form.append('manual_mapping', JSON.stringify(payload.manualMapping))
  }
  if (payload.resolutions && Object.keys(payload.resolutions).length > 0) {
    form.append('resolutions', JSON.stringify(payload.resolutions))
  }
  return form
}

/**
 * 带真实进度的导入。
 *
 * 后端以 text/event-stream 边写库边推进度，这里用 XMLHttpRequest 增量读取：
 * - upload.onprogress 拿上传字节进度（映射到 0–5%）
 * - onprogress 里按 `\n\n` 切分事件，把服务端的真实百分比透传给界面
 */
export function commitQcImportWithProgress(
  payload: Parameters<typeof buildCommitForm>[0],
  onProgress: (progress: QcImportProgress) => void,
): Promise<QcImportCommitResult> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', `${BASE}/import/commit`)
    request.timeout = 300000

    let cursor = 0
    let buffer = ''
    let finalResult: QcImportCommitResult | null = null
    let failure: string | null = null

    const pump = () => {
      const text = request.responseText ?? ''
      buffer += text.slice(cursor)
      cursor = text.length
      let cut = buffer.indexOf('\n\n')
      while (cut >= 0) {
        const block = buffer.slice(0, cut)
        buffer = buffer.slice(cut + 2)
        for (const line of block.split('\n')) {
          if (!line.startsWith('data: ')) continue
          let event: ServerProgressEvent
          try {
            event = JSON.parse(line.slice(6)) as ServerProgressEvent
          } catch {
            continue
          }
          if (event.stage === 'done') {
            finalResult = event.result ?? null
          } else if (event.stage === 'error') {
            failure = event.message ?? '导入失败'
          } else {
            onProgress({
              stage: event.stage,
              percent: event.percent ?? 0,
              message: event.message,
            })
          }
        }
        cut = buffer.indexOf('\n\n')
      }
    }

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      onProgress({
        stage: 'uploading',
        percent: Math.min(5, Math.round((event.loaded / event.total) * 5)),
      })
    }
    request.upload.onload = () =>
      onProgress({ stage: 'parsing', percent: 5, message: '正在解析两份文件' })
    request.upload.onerror = () => reject(new Error('文件上传中断，请检查网络后重试'))

    request.onprogress = pump

    request.onload = () => {
      pump()
      if (request.status >= 200 && request.status < 300) {
        if (failure) {
          reject(new Error(failure))
          return
        }
        const result = finalResult
        if (result) {
          resolve(result)
          return
        }
        reject(new Error('导入未返回结果，请刷新后查看'))
        return
      }
      // 409 / 400 仍是普通 JSON
      let message = `导入失败（${request.status}）`
      try {
        const body = JSON.parse(request.responseText) as { message?: string }
        if (body?.message) message = body.message
      } catch {
        // 响应体不是 JSON，保留默认文案
      }
      reject(new Error(message))
    }
    request.onerror = () => reject(new Error('网络异常，导入中断'))
    request.ontimeout = () => reject(new Error('导入超时，请稍后重试'))

    onProgress({ stage: 'uploading', percent: 0 })
    request.send(buildCommitForm(payload))
  })
}

export function qcExportUrl(productId: string, params?: { batch_no?: string; level?: string }): string {
  const search = new URLSearchParams()
  if (params?.batch_no) search.set('batch_no', params.batch_no)
  if (params?.level) search.set('level', params.level)
  const query = search.toString()
  return `${BASE}/products/${productId}/export${query ? `?${query}` : ''}`
}

/** 上传结果表，批量新增该品种的检验批次（列按位置对应已有项目）。 */
export async function importQcBatches(
  productId: string,
  file: File,
): Promise<QcBatchImportResult> {
  const form = new FormData()
  form.append('file', file)
  return qcRequest<QcBatchImportResult>(`${BASE}/products/${productId}/batches/import`, {
    method: 'POST',
    body: form,
  })
}

/** 读该品种全部检验项目与三层标准。 */
export async function fetchQcItems(productId: string): Promise<QcItem[]> {
  return qcRequest<QcItem[]>(`${BASE}/products/${productId}/items`)
}

/** 修改单个项目的标准（留空表示该层不参与判定）。 */
export async function updateQcItem(
  itemId: string,
  payload: QcItemUpdatePayload,
): Promise<QcItem> {
  return qcRequest<QcItem>(`${BASE}/items/${itemId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

/** 按当前标准重算该品种全部批次。 */
export async function rejudgeQcProduct(productId: string): Promise<QcRejudgeResult> {
  return qcRequest<QcRejudgeResult>(`${BASE}/products/${productId}/rejudge`, { method: 'POST' })
}

/** 删除品种（软删除，连带其下检验项目、批次与检验值）。 */
export async function deleteQcProduct(productId: string): Promise<void> {
  await qcRequest<null>(`${BASE}/products/${productId}`, { method: 'DELETE' })
}
