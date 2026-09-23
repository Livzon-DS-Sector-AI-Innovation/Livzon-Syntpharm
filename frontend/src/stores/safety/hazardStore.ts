'use client'

import { create } from 'zustand'
import type { HazardReport, HazardReportQueryParams } from '@/types/safety'

interface HazardState {
  // UI state only - data is managed by React Query
  currentItem: HazardReport | null
  queryParams: HazardReportQueryParams
  setCurrentItem: (item: HazardReport | null) => void
  setQueryParams: (params: Partial<HazardReportQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as HazardReport | null,
  queryParams: { page: 1, page_size: 20 } as HazardReportQueryParams,
}

export const useHazardStore = create<HazardState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
