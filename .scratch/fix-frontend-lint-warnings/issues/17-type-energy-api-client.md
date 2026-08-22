# 17 — Type energy API client

**What to build:** Replace all `any` types in energy API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `any` types replaced with proper types in energy API client
- [x] Types sourced from `@/types/energy` or `@/types/generated/schema`
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in energy API)

## Summary

Fixed 17 @typescript-eslint/no-explicit-any warnings in energy API client:

**Added new types to types/energy.ts:**
- EnergyPlatform: { code: string; name: string }
- MonthlySummary: Record<string, { total_value: number; unit: string }>

**Updated API functions:**
- fetchPlatformsClient: any[] → EnergyPlatform[]
- fetchAlertRules: params any → RuleQueryParams, return PaginatedResponse<AlertRule>
- fetchAlertRecords: params any → RecordQueryParams, return PaginatedResponse<AlertRecord>
- fetchMonthlyRecordsClient: params any → MonthlyRecordQueryParams, return PaginatedResponse<EnergyMonthlyRecord>
- fetchWorkshopsClient: params any → WorkshopQueryParams, return EnergyWorkshop[]
- fetchMonthlySummaryClient: params any → MonthlyRecordQueryParams, return MonthlySummary

All energy API functions now have fully typed parameters and return values.
