'use client'

import { create } from 'zustand'
import type { SafetyKnowledgeArticle, SafetyKnowledgeArticleQueryParams } from '@/types/safety'

interface KnowledgeState {
  // UI state only - data is managed by React Query
  currentItem: SafetyKnowledgeArticle | null
  queryParams: SafetyKnowledgeArticleQueryParams
  selectedRowKeys: string[]
  setCurrentItem: (item: SafetyKnowledgeArticle | null) => void
  setQueryParams: (params: Partial<SafetyKnowledgeArticleQueryParams>) => void
  setSelectedRowKeys: (keys: string[]) => void
  reset: () => void
}

const initialState = {
  currentItem: null as SafetyKnowledgeArticle | null,
  queryParams: { page: 1, page_size: 200 } as SafetyKnowledgeArticleQueryParams,
  selectedRowKeys: [] as string[],
}

export const useKnowledgeStore = create<KnowledgeState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),
  setSelectedRowKeys: (selectedRowKeys) => set({ selectedRowKeys }),

  reset: () => set(initialState),
}))
