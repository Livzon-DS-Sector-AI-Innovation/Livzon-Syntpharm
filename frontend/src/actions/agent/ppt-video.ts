'use server'

/**
 * 智能体 - PPT 配音视频：全部写操作（Server Actions）。
 *
 * 约定（AGENTS.md）：Client 组件不得直接 fetch 写接口；失败不抛异常给客户端，
 * 统一返回 `{ success, message, data }`。本文件禁止 `export type` / `export interface`
 * （Turbopack 会在运行时把它当值导出而报 ReferenceError），类型放在
 * `src/types/agent/ppt-video.ts`。
 */
import { revalidatePath } from 'next/cache'

import { unwrapResponse } from '@/lib/api/server/base'
import {
  applySourceRequest,
  createAiConfigRequest,
  deleteAiConfigRequest,
  deleteProjectRequest,
  discoverAiModelsRequest,
  editSlideImageRequest,
  editSlideTextRequest,
  fetchAiConfigs,
  fetchEditableShapes,
  fetchPptVideoProject,
  fetchScriptRevisions,
  previewSlideRequest,
  previewSourceRequest,
  requestParseRequest,
  regeneratePageImagesRequest,
  regenerateScriptAiRequest,
  recheckCoverageRequest,
  requestRenderRequest,
  rewriteScriptsRequest,
  rollbackRevisionRequest,
  testAiConfigRequest,
  updateAiConfigRequest,
  updateGlobalAiSettingsRequest,
  updateProjectAiSettingsRequest,
  updateProjectRequest,
  updateSlideRequest,
} from '@/lib/api/server/agent'
import type {
  ActionResult,
  AiConfigCreateRequest,
  AiConfigListResponse,
  AiConfigTestRequest,
  AiConfigTestResponse,
  AiConfigUpdateRequest,
  AiModelsDiscoverRequest,
  AiModelsDiscoverResponse,
  EditableShapeList,
  GlobalAiSettingsRequest,
  JobAccepted,
  PageImagesAccepted,
  ParseAccepted,
  ProjectAiSettingsRequest,
  ProjectDetail,
  ProjectUpdateRequest,
  RenderAccepted,
  RevisionItem,
  ScriptRewriteRequest,
  ScriptRewriteResult,
  SlideUpdateRequest,
  SourceApplyResult,
} from '@/types/agent/ppt-video'

const LIST_PATH = '/agent/ppt-videos'

function toMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

export async function updateProjectSettings(
  projectId: string,
  payload: ProjectUpdateRequest,
): Promise<ActionResult<ProjectDetail>> {
  try {
    const raw = await updateProjectRequest(projectId, payload)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    revalidatePath(LIST_PATH)
    return { success: true, message: '设置已保存', data: unwrapResponse(raw) }
  } catch (error) {
    return { success: false, message: toMessage(error, '保存设置失败') }
  }
}

export async function saveSlideScript(
  projectId: string,
  slideUid: string,
  payload: SlideUpdateRequest,
  slideNo?: number,
): Promise<ActionResult<ProjectDetail>> {
  const label = slideNo ? `第 ${slideNo} 页` : '本页'
  try {
    await updateSlideRequest(projectId, slideUid, { ...payload })
    const detail = await fetchPptVideoProject(projectId)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: `${label}已保存`, data: detail }
  } catch (error) {
    return { success: false, message: toMessage(error, `${label}保存失败`) }
  }
}

/** 单页试听受理（202）：拿到 job_id 后由调用方轮询 `/jobs/{job_id}` */
export async function previewSlide(projectId: string, slideUid: string): Promise<ActionResult<JobAccepted>> {
  try {
    const raw = await previewSlideRequest(projectId, slideUid)
    return { success: true, message: '正在合成试听音频', data: unwrapResponse(raw) as JobAccepted }
  } catch (error) {
    return { success: false, message: toMessage(error, '试听失败，请稍后重试') }
  }
}

/** 重试解析（上传后解析失败时用）：202 受理，前端轮询解析进度 */
export async function requestParse(projectId: string): Promise<ActionResult<ParseAccepted>> {
  try {
    const raw = await requestParseRequest(projectId)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: '已重新加入解析队列', data: unwrapResponse(raw) as ParseAccepted }
  } catch (error) {
    return { success: false, message: toMessage(error, '重试解析失败') }
  }
}

/** 重新生成 AI 讲稿初稿：只填空页，返回最新详情（202 语义） */
export async function regenerateScriptDraft(projectId: string): Promise<ActionResult<ProjectDetail>> {
  try {
    const raw = await regenerateScriptAiRequest(projectId)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: '已开始生成剩余空页的讲稿初稿', data: unwrapResponse(raw) }
  } catch (error) {
    return { success: false, message: toMessage(error, '发起讲稿初稿生成失败') }
  }
}

/** 提交渲染：立刻返回 job_id（202），前端轮询 `/job` */
export async function requestRender(projectId: string): Promise<ActionResult<RenderAccepted>> {
  try {
    const raw = await requestRenderRequest(projectId)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    revalidatePath(LIST_PATH)
    return { success: true, message: '已加入渲染队列', data: unwrapResponse(raw) as RenderAccepted }
  } catch (error) {
    return { success: false, message: toMessage(error, '提交渲染失败') }
  }
}

/**
 * 页图重生成（老项目回填 / 页图渲染失败后手动重试）。
 * 返回 job_id 供左栏进度条开始轮询；走 Server Action 而非客户端 fetch 写接口。
 */
export async function regeneratePageImages(projectId: string): Promise<ActionResult<PageImagesAccepted>> {
  try {
    const raw = await regeneratePageImagesRequest(projectId)
    return { success: true, message: '已开始生成页图', data: unwrapResponse(raw) }
  } catch (error) {
    return { success: false, message: toMessage(error, '重新生成页图失败') }
  }
}

export async function deletePptVideoProject(projectId: string): Promise<ActionResult<null>> {
  try {
    await deleteProjectRequest(projectId)
    revalidatePath(LIST_PATH)
    return { success: true, message: '项目已删除', data: null }
  } catch (error) {
    return { success: false, message: toMessage(error, '删除项目失败') }
  }
}

/** 详情重取：换源/改写后前端要整体刷新一次，避免只更新局部导致状态错位 */
export async function reloadPptVideoProject(projectId: string): Promise<ActionResult<ProjectDetail>> {
  try {
    const detail = await fetchPptVideoProject(projectId)
    return { success: true, message: '', data: detail }
  } catch (error) {
    return { success: false, message: toMessage(error, '刷新项目详情失败') }
  }
}

// ── AI 配置 ────────────────────────────────────────────────────────────────

/** 读 AI 配置（列表页首屏由 RSC 传下来，这里给抽屉内的手动刷新用） */
export async function loadAiConfigs(): Promise<ActionResult<AiConfigListResponse>> {
  try {
    const data = await fetchAiConfigs()
    return { success: true, message: '', data }
  } catch (error) {
    return { success: false, message: toMessage(error, '读取 AI 配置失败') }
  }
}

export async function createAiConfig(payload: AiConfigCreateRequest): Promise<ActionResult<AiConfigListResponse>> {
  try {
    const raw = await createAiConfigRequest(payload)
    revalidatePath(LIST_PATH)
    return { success: true, message: '自定义模型已保存，仅本人可见', data: unwrapResponse(raw) }
  } catch (error) {
    return { success: false, message: toMessage(error, '保存自定义模型失败') }
  }
}

/** 按接口地址与 Key 拉取可用模型；失败时前端允许手动填写模型名 */
export async function discoverAiModels(
  payload: AiModelsDiscoverRequest,
): Promise<ActionResult<AiModelsDiscoverResponse>> {
  try {
    const raw = await discoverAiModelsRequest(payload)
    const data = unwrapResponse(raw)
    return { success: data.ok, message: data.message, data }
  } catch (error) {
    return {
      success: false,
      message: toMessage(error, '获取模型失败，可手动填写模型名'),
      data: { ok: false, message: '', models: [] },
    }
  }
}

export async function updateAiConfig(
  configId: string,
  payload: AiConfigUpdateRequest,
): Promise<ActionResult<AiConfigListResponse>> {
  try {
    const raw = await updateAiConfigRequest(configId, payload)
    revalidatePath(LIST_PATH)
    return { success: true, message: '配置已更新', data: unwrapResponse(raw) }
  } catch (error) {
    return { success: false, message: toMessage(error, '更新配置失败') }
  }
}

export async function deleteAiConfig(configId: string): Promise<ActionResult<AiConfigListResponse>> {
  try {
    const raw = await deleteAiConfigRequest(configId)
    revalidatePath(LIST_PATH)
    return { success: true, message: '配置已删除', data: unwrapResponse(raw) }
  } catch (error) {
    return { success: false, message: toMessage(error, '删除配置失败') }
  }
}

export async function testAiConfig(
  payload: AiConfigTestRequest,
): Promise<ActionResult<AiConfigTestResponse>> {
  try {
    const raw = await testAiConfigRequest(payload)
    const data = unwrapResponse(raw)
    return { success: data.ok, message: data.message, data }
  } catch (error) {
    return { success: false, message: toMessage(error, '测试失败，请检查接口地址与 Key') }
  }
}

/** 全局默认模型与全局提示词指南（需平台管理员） */
export async function saveGlobalAiSettings(
  payload: GlobalAiSettingsRequest,
): Promise<ActionResult<AiConfigListResponse>> {
  try {
    const raw = await updateGlobalAiSettingsRequest(payload)
    revalidatePath(LIST_PATH)
    return { success: true, message: '全局 AI 配置已保存', data: unwrapResponse(raw) }
  } catch (error) {
    return { success: false, message: toMessage(error, '保存全局 AI 配置失败') }
  }
}

/** 项目级覆盖：模型与提示词指南留空即继承全局 */
export async function saveProjectAiSettings(
  projectId: string,
  payload: ProjectAiSettingsRequest,
): Promise<ActionResult<ProjectDetail>> {
  try {
    const raw = await updateProjectAiSettingsRequest(projectId, payload)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: '项目 AI 设置已保存', data: unwrapResponse(raw) }
  } catch (error) {
    return { success: false, message: toMessage(error, '保存项目 AI 设置失败') }
  }
}

// ── 讲稿改写 / 修订回滚 ────────────────────────────────────────────────────

export async function rewriteScripts(
  projectId: string,
  payload: ScriptRewriteRequest,
): Promise<ActionResult<ScriptRewriteResult>> {
  try {
    const raw = await rewriteScriptsRequest(projectId, payload)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    const data = unwrapResponse(raw)
    const message = data.status === 'queued' ? '改写任务已提交，完成后页面自动刷新' : '讲稿已更新'
    return { success: true, message, data }
  } catch (error) {
    return { success: false, message: toMessage(error, '改写讲稿失败') }
  }
}

/**
 * 补全本页漏讲内容：走 fill_missing 改写模式（保留原讲稿，按漏讲要点补写）。
 * 与其他改写一样只入队，前端拿 revision_id 轮询，完成后回拉详情。
 */
export async function completeMissing(
  projectId: string,
  slideUid: string,
  missing: string[],
): Promise<ActionResult<ScriptRewriteResult>> {
  const points = missing.map((item) => item.trim()).filter(Boolean)
  if (!points.length) {
    return { success: false, message: '本页没有可补全的漏讲要点' }
  }
  try {
    const raw = await rewriteScriptsRequest(projectId, {
      mode: 'fill_missing',
      slide_uids: [slideUid],
      instruction: `本页漏讲要点（按页面阅读顺序补讲）：${points.join('；')}`,
    })
    const data = unwrapResponse(raw)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: '已提交补全任务，完成后自动刷新', data }
  } catch (error) {
    return { success: false, message: toMessage(error, '补全本页失败') }
  }
}

/** 手工重算单页覆盖度：页文本或讲稿在别处被改过时用 */
export async function recheckCoverage(projectId: string, slideUid: string): Promise<ActionResult<ProjectDetail>> {
  try {
    await recheckCoverageRequest(projectId, slideUid)
    const detail = await fetchPptVideoProject(projectId)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: '覆盖度已重算', data: detail }
  } catch (error) {
    return { success: false, message: toMessage(error, '重算覆盖度失败') }
  }
}

export async function loadScriptRevisions(
  projectId: string,
  limit = 30,
): Promise<ActionResult<RevisionItem[]>> {
  try {
    const items = await fetchScriptRevisions(projectId, limit)
    return { success: true, message: '', data: items }
  } catch (error) {
    return { success: false, message: toMessage(error, '读取修订记录失败') }
  }
}

export async function rollbackRevision(projectId: string, revisionId: string): Promise<ActionResult<ProjectDetail>> {
  try {
    await rollbackRevisionRequest(projectId, revisionId)
    const detail = await fetchPptVideoProject(projectId)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: '已回滚，受影响页需要重新渲染', data: detail }
  } catch (error) {
    return { success: false, message: toMessage(error, '回滚失败') }
  }
}

// ── 换源 ───────────────────────────────────────────────────────────────────

/** 第一步：上传新 PPT 受理（202），比对在 worker 里跑，差异由轮询任务取回 */
export async function previewSourceReplace(projectId: string, file: File): Promise<ActionResult<JobAccepted>> {
  try {
    const raw = await previewSourceRequest(projectId, file)
    return { success: true, message: '已上传，正在比对页序列', data: unwrapResponse(raw) as JobAccepted }
  } catch (error) {
    return { success: false, message: toMessage(error, 'PPT 比对失败，请确认文件未损坏') }
  }
}

/** 第二步：确认应用；未变页保留讲稿与音频，变更页自动重写 */
export async function applySourceReplace(
  projectId: string,
  autoRewrite = true,
): Promise<ActionResult<SourceApplyResult>> {
  try {
    const raw = await applySourceRequest(projectId, autoRewrite)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    revalidatePath(LIST_PATH)
    const result = unwrapResponse(raw)
    return {
      success: true,
      message: `已切换到第 ${result.source_version} 版源文件，${result.rewrite_uids?.length ?? 0} 页讲稿待重写`,
      data: result,
    }
  } catch (error) {
    return { success: false, message: toMessage(error, '应用换源失败，原有数据未改动') }
  }
}

// ── 轻量页级编辑 ───────────────────────────────────────────────────────────

export async function loadEditableShapes(
  projectId: string,
  slideUid: string,
): Promise<ActionResult<EditableShapeList>> {
  try {
    const data = await fetchEditableShapes(projectId, slideUid)
    return { success: true, message: '', data }
  } catch (error) {
    return { success: false, message: toMessage(error, '读取页面元素失败') }
  }
}

export async function editSlideText(
  projectId: string,
  slideUid: string,
  shapeIndex: number,
  text: string,
): Promise<ActionResult<ProjectDetail>> {
  try {
    await editSlideTextRequest(projectId, slideUid, shapeIndex, text)
    const detail = await fetchPptVideoProject(projectId)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: '页面文字已修改，重渲后生效', data: detail }
  } catch (error) {
    return { success: false, message: toMessage(error, '修改页面文字失败') }
  }
}

export async function editSlideImage(
  projectId: string,
  slideUid: string,
  shapeIndex: number,
  file: File,
): Promise<ActionResult<ProjectDetail>> {
  try {
    await editSlideImageRequest(projectId, slideUid, shapeIndex, file)
    const detail = await fetchPptVideoProject(projectId)
    revalidatePath(`${LIST_PATH}/${projectId}`)
    return { success: true, message: '图片已替换，重渲后生效', data: detail }
  } catch (error) {
    return { success: false, message: toMessage(error, '替换图片失败') }
  }
}