'use server'

import { revalidatePath } from 'next/cache'
import {
  markDocumentRead as markDocumentReadApi,
  fetchAIAnalysis as fetchAIAnalysisApi,
  fetchAIBatchAnalysis as fetchAIBatchAnalysisApi,
} from '@/lib/api/server/regulatory-tracker'
import type { AIAnalysisResult, AIBatchAnalysisResult } from '@/types/regulatory-tracker'

export async function markDocumentRead(id: string): Promise<void> {
  await markDocumentReadApi(id)
  revalidatePath('/registration/regulation')
}

export async function fetchAIAnalysis(docId: string): Promise<AIAnalysisResult> {
  const result = await fetchAIAnalysisApi(docId)
  revalidatePath('/regulatory-tracker')
  return result as AIAnalysisResult
}

export async function fetchAIBatchAnalysis(docIds: string[]): Promise<AIBatchAnalysisResult> {
  const result = await fetchAIBatchAnalysisApi(docIds)
  revalidatePath('/regulatory-tracker')
  return result as AIBatchAnalysisResult
}
