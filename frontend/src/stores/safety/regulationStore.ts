'use client'

import { create } from 'zustand'
import type { OperationRegulation, OperationRegulationQueryParams } from '@/types/safety'

interface RegulationState {
  // UI state only - data is managed by React Query
  currentItem: OperationRegulation | null
  queryParams: OperationRegulationQueryParams
  setCurrentItem: (item: OperationRegulation | null) => void
  setQueryParams: (params: Partial<OperationRegulationQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as OperationRegulation | null,
  queryParams: { page: 1, page_size: 20 } as OperationRegulationQueryParams,
}

export const useRegulationStore = create<RegulationState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
