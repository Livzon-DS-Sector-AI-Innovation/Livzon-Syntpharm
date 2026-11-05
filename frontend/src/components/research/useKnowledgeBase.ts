'use client'

/**
 * 项目知识库的共用数据层：独立页面与「新建报告」内嵌弹窗共用同一份实现，
 * 避免两边各写一套轮询与统计后走偏。
 */
import { useQuery } from '@tanstack/react-query'
import { fetchKbDocuments, fetchKnowledgeBasesByProject } from '@/lib/api/client/research/knowledge-base'
import { hasPendingKbDocument, type KbDocumentItem } from '@/types/research/knowledge-base'

/** 知识库文档盘点：AI 生成报告只能用到 parsed 的那部分 */
export interface KbSummary {
  total: number
  parsed: number
  pending: number
  failed: number
}

export function summarizeKb(documents: KbDocumentItem[]): KbSummary {
  let parsed = 0
  let pending = 0
  let failed = 0
  for (const doc of documents) {
    if (doc.run === 'DONE') parsed += 1
    else if (doc.run === 'RUNNING' || doc.run === 'UNSTART') pending += 1
    else failed += 1 // FAIL / CANCEL
  }
  return { total: documents.length, parsed, pending, failed }
}

/** 项目当前的知识库（一个项目至多一个）；`enabled=false` 时不请求 */
export function useKnowledgeBase(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['knowledge-bases', projectId],
    queryFn: () => fetchKnowledgeBasesByProject(projectId),
    enabled: enabled && !!projectId,
  })
}

/** 文档列表：有未终态文档时每 3 秒回源一次，全部落定后自动停止 */
export function useKbDocuments(kbId?: string) {
  return useQuery({
    queryKey: ['kb-documents', kbId],
    queryFn: () => fetchKbDocuments(kbId as string),
    enabled: !!kbId,
    refetchInterval: (query) => (hasPendingKbDocument(query.state.data ?? []) ? 3000 : false),
  })
}
