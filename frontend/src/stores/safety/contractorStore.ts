'use client'

import { create } from 'zustand'
import type { Contractor, ContractorQueryParams } from '@/types/safety'

interface ContractorState {
  // UI state only - data is managed by React Query
  currentItem: Contractor | null
  queryParams: ContractorQueryParams
  setCurrentItem: (item: Contractor | null) => void
  setQueryParams: (params: Partial<ContractorQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as Contractor | null,
  queryParams: { page: 1, page_size: 20 } as ContractorQueryParams,
}

export const useContractorStore = create<ContractorState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
