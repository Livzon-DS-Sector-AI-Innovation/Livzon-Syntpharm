'use client'

import { create } from 'zustand'
import type { RegulationRevision, RegulationRevisionQueryParams } from '@/types/safety'

interface RevisionState {
  // UI state only - data is managed by React Query
  currentItem: RegulationRevision | null
  queryParams: RegulationRevisionQueryParams
  setCurrentItem: (item: RegulationRevision | null) => void
  setQueryParams: (params: Partial<RegulationRevisionQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as RegulationRevision | null,
  queryParams: { page: 1, page_size: 20 } as RegulationRevisionQueryParams,
}

export const useRevisionStore = create<RevisionState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
