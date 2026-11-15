'use client'

/**
 * 项目知识库的共用数据层：独立页面与「新建报告」内嵌弹窗共用同一份实现，
 * 避免两边各写一套轮询与统计后走偏。
 */
import { useQuery } from '@tanstack/react-query'
import { fetchKbDocuments, fetchKnowledgeBasesByProject } from '@/lib/api/client/research/knowledge-base'
import { hasPendingKbDocument, type KbDocumentItem } from '@/types/research/knowledge-base'

/**
 * 知识库文档盘点：只有 parsed 的文档才能被检索到。
 *
 * 这里把「排队中 / 入库中 / 处理失败 / 已取消」分开计数：原先 CANCEL 被并进 failed、
 * 排队也被算成「解析中」，导致点「失败」进去看到的是「已取消」，用户以为出了故障。
 */
export interface KbSummary {
  total: number
  parsed: number
  /** 正在入库（RUNNING） */
  parsing: number
  /** 排队等待（UNSTART） */
  queued: number
  /** 尚未结束的合计（排队 + 入库中），用于「还有 N 份在处理」这类提示 */
  pending: number
  /** 只有真的 FAIL 才算失败 */
  failed: number
  cancelled: number
}

export function summarizeKb(documents: KbDocumentItem[]): KbSummary {
  let parsed = 0
  let parsing = 0
  let queued = 0
  let failed = 0
  let cancelled = 0
  for (const doc of documents) {
    if (doc.run === 'DONE') parsed += 1
    else if (doc.run === 'RUNNING') parsing += 1
    else if (doc.run === 'UNSTART') queued += 1
    else if (doc.run === 'CANCEL') cancelled += 1
    else failed += 1
  }
  return {
    total: documents.length,
    parsed,
    parsing,
    queued,
    pending: parsing + queued,
    failed,
    cancelled,
  }
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
