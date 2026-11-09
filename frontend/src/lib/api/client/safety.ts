import type { components } from '@/types/generated/schema'
import type { HazardReport, ModuleInfo } from '@/types/safety'
import { apiGet } from '@/lib/api/client'

const API_BASE = '/api/v1'

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiGet(`${API_BASE}/safety`)
}

/** 隐患类别项（契约来自 OpenAPI） */
export type HazardCategoryItem = components['schemas']['HazardCategoryResponse']

type HazardCategoryListData = components['schemas']['HazardCategoryListApiResponse']['data']

// 类别字典变化频率极低：模块级缓存，新增类别后手动失效
let hazardCategoryCache: HazardCategoryItem[] | null = null

/** 失效类别缓存（新增类别成功后调用） */
export function invalidateHazardCategoryCache(): void {
  hazardCategoryCache = null
}

/** 获取隐患类别下拉数据（内置 7 类 + 用户新增，已按 sort_order 排序） */
export async function fetchHazardCategories(force = false): Promise<HazardCategoryItem[]> {
  if (!force && hazardCategoryCache) return hazardCategoryCache
  try {
    const data = await apiGet<HazardCategoryListData>(`${API_BASE}/safety/hazard-categories`)
    hazardCategoryCache = data ?? []
  } catch {
    // 字典接口不可用时不阻塞登记：回退为空，由表单内置 7 项兜底
    hazardCategoryCache = []
  }
  return hazardCategoryCache
}

/** 获取隐患详情（浏览器侧只读 API） */
export async function fetchHazard(id: string): Promise<HazardReport> {
  return apiGet(`${API_BASE}/safety/hazards/${id}`)
}

interface WaitForHazardAiOptions {
  /** 总等待时长，默认 180s（单次识别通常 30-90s） */
  timeoutMs?: number
  /** 轮询间隔，默认 2s */
  intervalMs?: number
}

/**
 * 等待后台 AI 工作流结束。
 *
 * 后端 `POST /hazards/{id}/ai/run/{n}` 已改为异步提交（AI 调用超出 HTTP 请求预算），
 * 提交前会把 `ai_node_progress` 置为 `running`，结束时写 `completed` / `failed`。
 * 这里轮询隐患详情，直到该字段不再为 `running`。
 *
 * @returns 结束后的隐患数据；超时返回 null
 */
export async function waitForHazardAiResult(
  hazardId: string,
  options?: WaitForHazardAiOptions,
): Promise<HazardReport | null> {
  const timeoutMs = options?.timeoutMs ?? 180_000
  const intervalMs = options?.intervalMs ?? 2_000
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
    try {
      const hazard = await fetchHazard(hazardId)
      if (hazard.ai_node_progress !== 'running') return hazard
    } catch {
      // 轮询期间的瞬时读取失败不终止等待，下一轮继续
    }
  }
  return null
}