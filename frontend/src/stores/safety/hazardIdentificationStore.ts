'use client'

import { create } from 'zustand'
import type { HazardIdentification, HazardIdentificationQueryParams } from '@/types/safety'

interface HazardIdentificationState {
  // UI state only - data is managed by React Query
  currentItem: HazardIdentification | null
  queryParams: HazardIdentificationQueryParams
  setCurrentItem: (item: HazardIdentification | null) => void
  setQueryParams: (params: Partial<HazardIdentificationQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as HazardIdentification | null,
  queryParams: { page: 1, page_size: 20 } as HazardIdentificationQueryParams,
}

export const useHazardIdentificationStore = create<HazardIdentificationState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
