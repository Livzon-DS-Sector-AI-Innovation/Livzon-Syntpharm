/**
 * Safety module domain model types (ViewModels).
 * These response types are not in the OpenAPI spec (backend uses dict responses).
 * API input types (Create/Update) use @/types/generated/schema.
 */

﻿// safety module TypeScript types

// Owned by types/common.ts; re-exported so existing importers keep working.
export type { ApiResponse } from '@/types/common'

export interface SafetyDashboardStats {
  total_checks: number
  pending_checks: number
  open_hazards: number
  overdue_hazards: number
  recent_accidents: number
  upcoming_trainings: number
}

export type { ModuleInfo } from '@/types/common'

