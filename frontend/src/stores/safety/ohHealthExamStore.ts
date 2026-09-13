'use client'

import { create } from 'zustand'
import type { OhHealthExam, OhHealthExamQueryParams } from '@/types/safety'

interface OhHealthExamState {
  // UI state only - data is managed by React Query
  currentItem: OhHealthExam | null
  queryParams: OhHealthExamQueryParams
  setCurrentItem: (item: OhHealthExam | null) => void
  setQueryParams: (params: Partial<OhHealthExamQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as OhHealthExam | null,
  queryParams: { page: 1, page_size: 20 } as OhHealthExamQueryParams,
}

export const useOhHealthExamStore = create<OhHealthExamState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
