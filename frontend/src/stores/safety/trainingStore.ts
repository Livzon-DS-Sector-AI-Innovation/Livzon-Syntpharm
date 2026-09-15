'use client'

import { create } from 'zustand'
import type { SafetyTraining, SafetyTrainingQueryParams } from '@/types/safety'

interface TrainingState {
  // UI state only - data is managed by React Query
  currentItem: SafetyTraining | null
  queryParams: SafetyTrainingQueryParams
  setCurrentItem: (item: SafetyTraining | null) => void
  setQueryParams: (params: Partial<SafetyTrainingQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as SafetyTraining | null,
  queryParams: { page: 1, page_size: 20 } as SafetyTrainingQueryParams,
}

export const useTrainingStore = create<TrainingState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
