'use client'

import { create } from 'zustand'
import type { Accident, AccidentQueryParams } from '@/types/safety'

interface AccidentState {
  // UI state only - data is managed by React Query
  currentItem: Accident | null
  queryParams: AccidentQueryParams
  setCurrentItem: (item: Accident | null) => void
  setQueryParams: (params: Partial<AccidentQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as Accident | null,
  queryParams: { page: 1, page_size: 20 } as AccidentQueryParams,
}

export const useAccidentStore = create<AccidentState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
