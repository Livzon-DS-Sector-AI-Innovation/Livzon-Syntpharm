# 62 — Replace `any` in type definitions (`src/types/`)

**What to build:** All type definition files in `src/types/` use proper types instead of `any`. This includes replacing `Record<string, any>` with specific field types or `Record<string, unknown>`, replacing `any[]` with typed arrays, and replacing `[key: string]: any` index signatures with specific interfaces. This makes the domain model type-safe and self-documenting.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `Record<string, any>` replaced with specific types or `Record<string, unknown>`
- [x] All `any[]` replaced with typed arrays (e.g., `CapaProposal[]`, `ReportVersion[]`)
- [x] All `[key: string]: any` index signatures replaced with specific interfaces
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows 0 `@typescript-eslint/no-explicit-any` warnings in `src/types/`
- [x] Affected files: `quality.ts`, `material-report.ts`, `hr.ts`, `settings.ts`, `static-data.ts`, `equipment/equipment.ts`, `equipment/generated-bridge.ts`, `inspection-table.ts`, `quality-cpv.ts`, `doc-check.ts`, `research/process-optimization.ts`, `safety/hazard.ts`, `sop-ai.ts`

## Implementation Notes

### Key Changes

1. **Generic API Response Types**: Changed `ApiResponse<T = any>` to `ApiResponse<T = unknown>` in `doc-check.ts`, `sop-ai.ts`, and `static-data.ts`

2. **Feishu Configuration Types**: Defined proper interfaces for `FeishuConfig`, `FeishuConfigUpsert`, `FeishuDiagnosticStep`, and `FeishuDiagnosticResult` in `settings.ts` instead of using `any`

3. **CAPA Proposals**: Added `CapaProposal` interface in `quality.ts` and changed `capaProposals?: any[]` to `capaProposals?: CapaProposal[]`

4. **Equipment API Types**: Changed `AssignRolesInput` and `AssignCategoriesInput` from `any` to proper schema types from `components['schemas']`

5. **Lab Confirmation Parameters**: Changed `parameters: Record<string, unknown>` to `Record<string, string | number | boolean | null | undefined>` in `research/process-optimization.ts` to allow rendering as React nodes

6. **Index Signatures**: Changed all `[key: string]: any` to `[key: string]: unknown` in `quality.ts` and `static-data.ts`

### Cascading Type Fixes

The type changes in `src/types/` required updates in several component files to add proper type casts:
- `src/components/hr/TrainingSpecialistsClient.tsx`: Added type casts for query data
- `src/components/hr/TrainingSessionListClient.tsx`: Added type casts for select tasks
- `src/components/hr/TrainingSelectTasksClient.tsx`: Added `employee_numbers` property to `TaskItem` interface
- `src/app/(dashboard)/safety/hazard/[id]/page.tsx`: Added type cast for `aiResult.confidence`
- `src/app/(dashboard)/quality/material-report/`: Added type casts for `field_mapping` config objects
