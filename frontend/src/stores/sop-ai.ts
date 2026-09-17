/**
 * SOP AI 模块 Zustand 状态管理
 * 文件合规校验模块的状态存储
 */

import { create } from 'zustand'
import {
  CheckMain,
  CheckMainDetail,
  CheckProblem,
  CheckRecordFilter,
  SopAiConfig,
  ScheduledJob,
  PaginatedResponse,
  ApiResponse,
} from '@/types/sop-ai'

interface SopAiState {
  // 配置相关
  configs: SopAiConfig[]
  configsLoading: boolean
  setConfigs: (configs: SopAiConfig[]) => void
  setConfigsLoading: (loading: boolean) => void

  // 校验记录列表
  records: CheckMain[]
  recordsTotal: number
  recordsLoading: boolean
  recordsFilter: CheckRecordFilter
  setRecords: (records: CheckMain[], total: number) => void
  setRecordsLoading: (loading: boolean) => void
  setRecordsFilter: (filter: CheckRecordFilter) => void

  // 当前校验详情
  currentRecord: CheckMainDetail | null
  currentRecordLoading: boolean
  setCurrentRecord: (record: CheckMainDetail | null) => void
  setCurrentRecordLoading: (loading: boolean) => void

  // 定时任务
  jobs: ScheduledJob[]
  jobsLoading: boolean
  setJobs: (jobs: ScheduledJob[]) => void
  setJobsLoading: (loading: boolean) => void

  // UI 状态
  selectedProblems: string[]
  setSelectedProblems: (ids: string[]) => void
  toggleProblemSelection: (id: string) => void

  // 重置状态
  resetRecords: () => void
  resetCurrentRecord: () => void
}

export const useSopAiStore = create<SopAiState>((set) => ({
  // 配置相关
  configs: [],
  configsLoading: false,
  setConfigs: (configs) => set({ configs }),
  setConfigsLoading: (configsLoading) => set({ configsLoading }),

  // 校验记录列表
  records: [],
  recordsTotal: 0,
  recordsLoading: false,
  recordsFilter: { page: 1, page_size: 20 },
  setRecords: (records, recordsTotal) => set({ records, recordsTotal }),
  setRecordsLoading: (recordsLoading) => set({ recordsLoading }),
  setRecordsFilter: (recordsFilter) => set({ recordsFilter }),

  // 当前校验详情
  currentRecord: null,
  currentRecordLoading: false,
  setCurrentRecord: (currentRecord) => set({ currentRecord }),
  setCurrentRecordLoading: (currentRecordLoading) => set({ currentRecordLoading }),

  // 定时任务
  jobs: [],
  jobsLoading: false,
  setJobs: (jobs) => set({ jobs }),
  setJobsLoading: (jobsLoading) => set({ jobsLoading }),

  // UI 状态
  selectedProblems: [],
  setSelectedProblems: (selectedProblems) => set({ selectedProblems }),
  toggleProblemSelection: (id) =>
    set((state) => ({
      selectedProblems: state.selectedProblems.includes(id)
        ? state.selectedProblems.filter((p) => p !== id)
        : [...state.selectedProblems, id],
    })),

  // 重置
  resetRecords: () =>
    set({
      records: [],
      recordsTotal: 0,
      recordsFilter: { page: 1, page_size: 20 },
    }),
  resetCurrentRecord: () =>
    set({
      currentRecord: null,
      selectedProblems: [],
    }),
}))

// ============ 选择器 ============

export const selectSopAiConfigs = (state: SopAiState) => state.configs
export const selectSopAiConfigsLoading = (state: SopAiState) => state.configsLoading

export const selectCheckRecords = (state: SopAiState) => state.records
export const selectCheckRecordsTotal = (state: SopAiState) => state.recordsTotal
export const selectCheckRecordsLoading = (state: SopAiState) => state.recordsLoading
export const selectCheckRecordsFilter = (state: SopAiState) => state.recordsFilter

export const selectCurrentRecord = (state: SopAiState) => state.currentRecord
export const selectCurrentRecordLoading = (state: SopAiState) => state.currentRecordLoading

export const selectScheduledJobs = (state: SopAiState) => state.jobs
export const selectScheduledJobsLoading = (state: SopAiState) => state.jobsLoading

export const selectSelectedProblems = (state: SopAiState) => state.selectedProblems