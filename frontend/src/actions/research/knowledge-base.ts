'use server'

/**
 * 项目知识库写操作（Server Actions）。
 *
 * 上传不在这里：多文件 multipart 走浏览器直传（lib/api/client/research/knowledge-base.ts），
 * 其余写操作都在这里，统一做缓存失效。
 */
import { revalidatePath } from 'next/cache'
import type { components } from '@/types/generated/schema'
import {
  createKnowledgeBase as createKnowledgeBaseApi,
  deleteKbDocument as deleteKbDocumentApi,
  deleteKnowledgeBase as deleteKnowledgeBaseApi,
  reparseKbDocument as reparseKbDocumentApi,
} from '@/lib/api/server/research/knowledge-base'

type KnowledgeBaseItem = components['schemas']['KnowledgeBaseItem']
type KbDocumentItem = components['schemas']['KbDocumentItem']

/** 知识库页面路由，写操作后据此失效缓存 */
const KNOWLEDGE_BASE_PATH = '/research/knowledge-bases'

/** 为研发项目创建知识库：名称留空时后端按项目名生成 */
export async function createKnowledgeBase(payload: {
  project_id: string
  name?: string
  description?: string
}): Promise<KnowledgeBaseItem> {
  const kb = await createKnowledgeBaseApi({
    project_id: payload.project_id,
    name: payload.name ?? '',
    description: payload.description ?? '',
    // 留空表示用后端部署配置里的默认向量模型与切片方式
    embedding_model: '',
    chunk_method: '',
  })
  revalidatePath(KNOWLEDGE_BASE_PATH)
  return kb
}

/** 删除知识库（连同远端数据集） */
export async function deleteKnowledgeBase(kbId: string): Promise<void> {
  await deleteKnowledgeBaseApi(kbId)
  revalidatePath(KNOWLEDGE_BASE_PATH)
}

/** 从知识库移除一份文档，返回最新文档列表 */
export async function deleteKbDocument(kbId: string, documentRowId: string): Promise<KbDocumentItem[]> {
  const documents = await deleteKbDocumentApi(kbId, documentRowId)
  revalidatePath(KNOWLEDGE_BASE_PATH)
  return documents
}

/** 重新解析一份文档（用于解析失败或资料已更新），返回最新文档列表 */
export async function reparseKbDocument(kbId: string, documentRowId: string): Promise<KbDocumentItem[]> {
  const documents = await reparseKbDocumentApi(kbId, documentRowId)
  revalidatePath(KNOWLEDGE_BASE_PATH)
  return documents
}
