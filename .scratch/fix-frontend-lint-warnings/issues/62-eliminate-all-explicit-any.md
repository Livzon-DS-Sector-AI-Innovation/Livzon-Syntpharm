# 62 — Eliminate all `@typescript-eslint/no-explicit-any` warnings

## Problem Statement

The frontend codebase has 162 instances of `@typescript-eslint/no-explicit-any` warnings across 46 files. While currently set to "warn" level, these undermine the type safety guarantees that TypeScript provides. Every `any` is a hole in the type system — a place where runtime errors can slip through undetected by the compiler. Eliminating them will make the codebase safer, more self-documenting, and easier to refactor with confidence.

## Solution

Systematically replace every `any` type annotation with a proper type. The approach varies by pattern:

- **Type definitions** (`src/types/`): Replace `Record<string, any>` with specific field types or `Record<string, unknown>`; replace `any[]` with typed arrays; replace `[key: string]: any` index signatures with specific interfaces.
- **React state**: Replace `useState<any>(null)` with the actual record type (e.g., `useState<MeetingLedgerItem | null>(null)`).
- **Error handling**: Replace `catch (err: any)` with `catch (err: unknown)` and use type guards for error message extraction.
- **Table column renderers**: Replace `(_: any, record: any)` with the actual row type from the data model.
- **API response callbacks**: Replace `(data: any[])` with the actual response type; replace `(err: any)` with `(err: unknown)`.
- **Form handlers**: Replace `(values: any)` with the form's field type.
- **Generic API types**: Keep `eslint-disable` comments for the 2 foundational functions (`apiFetch`, `apiFetchFormData`) where the blast radius is too large (already done in ticket 59).

## User Stories

1. As a developer, I want all `any` types in `src/types/` replaced with proper types, so that my type definitions accurately model the domain and catch mismatches at compile time.
2. As a developer, I want all `useState<any>` calls replaced with specific types, so that state access is type-checked and IDE autocomplete works correctly.
3. As a developer, I want all `catch (err: any)` replaced with `catch (err: unknown)`, so that error handling is type-safe and forces explicit error shape checking.
4. As a developer, I want all Ant Design table column renderers typed with actual row types, so that column definitions are self-documenting and refactoring-safe.
5. As a developer, I want all API callback parameters typed with actual response types, so that data flowing from the backend is validated at the type level.
6. As a developer, I want all form handler parameters typed with the form's field interface, so that form field access is checked by the compiler.
7. As a developer, I want `pnpm lint` to show 0 `@typescript-eslint/no-explicit-any` warnings, so that new `any` usage can be caught immediately (by flipping the rule to "error" in the future).
8. As a developer, I want `tsc --noEmit` to pass with no errors after all changes, so that type safety is maintained throughout the refactor.

## Implementation Decisions

### Module structure — 6 sub-tickets by area

The work is split into 6 sub-tickets, each targeting a distinct area of the codebase. This allows parallel execution and incremental verification.

#### Ticket 62.1 — Type definitions (`src/types/`) — 37 warnings

Replace `any` in type definition files:
- `Record<string, any>` → specific field types based on backend API contracts, or `Record<string, unknown>` where the shape is truly dynamic
- `[key: string]: any` index signatures → specific interfaces with known fields
- `any[]` → typed arrays (e.g., `CapaProposal[]`, `ReportVersion[]`)
- Files: `quality.ts`, `material-report.ts`, `hr.ts`, `settings.ts`, `static-data.ts`, `equipment/equipment.ts`, `equipment/generated-bridge.ts`, `inspection-table.ts`, `quality-cpv.ts`, `doc-check.ts`, `research/process-optimization.ts`, `safety/hazard.ts`, `sop-ai.ts`

#### Ticket 62.2 — Administration pages — 20 warnings

Replace `any` in administration page components:
- `useState<any>(null)` → `useState<MeetingLedgerItem | null>(null)` etc.
- `(values: any)` → `(values: MeetingLedgerFormValues)` etc.
- `catch (err: any)` → `catch (err: unknown)` with type guards
- `(_: any, record: any)` → `(_: unknown, record: MeetingLedgerItem)` etc.
- Files: `meeting/ledger/page.tsx`, `meeting/requisitions/page.tsx`, `vehicles/page.tsx`

#### Ticket 62.3 — Quality & Registration pages — 49 warnings

The largest group. Replace `any` in quality and registration page components:
- `static-data/page.tsx` (20 warnings) — the single largest file; needs careful typing of dynamic form fields and filter states
- `static-data/[module]/[id]/page.tsx` (14 warnings) — dynamic module rendering with typed field maps
- `inspection-table/[id]/page.tsx`, `instrument/list/page.tsx`, `deviation-flow/query/page.tsx`, `inspection/standards/page.tsx`, `material-report/` pages
- `registration/ledger/page.tsx`, `registration/validation-audit/` pages
- Pattern: many of these use dynamic data from backend that needs `Record<string, unknown>` or specific interfaces

#### Ticket 62.4 — Equipment, Production, Safety pages — 27 warnings

Replace `any` in equipment, production, and safety page components:
- `EquipmentPage.tsx` (6 warnings) — client-side API callbacks `(cats: any[])` → `(cats: EquipmentCategory[])`
- `equipment/inspection/page.tsx` (2 warnings)
- `production/product-output/` pages (17 warnings) — large page with complex data transformations
- `safety/hazard/[id]/page.tsx` (5 warnings)
- Pattern: mostly API response callbacks and error handlers

#### Ticket 62.5 — Components, stores, lib, e2e — 13 warnings

Replace `any` in shared components, stores, utilities, and tests:
- `components/hr/TrainingNotificationClient.tsx` (1)
- `lib/api/client.ts` (2) — client-side API fetch helpers
- `lib/utils/export-excel.ts` (2) — Excel export utility
- `lib/pdf-extract.ts` (1), `lib/validation/schemas.ts` (1), `lib/workflow-templates.ts` (1)
- `stores/regulation.ts` (1)
- `e2e/auth.setup.ts` (1), `e2e/routes.spec.ts` (2)
- `app/hr/training/select/page.tsx` (1)

#### Ticket 62.6 — Flip rule to error + final cleanup

After all 162 warnings are resolved:
- Change `@typescript-eslint/no-explicit-any` from "warn" to "error" in `eslint.config.mjs`
- Remove the `eslint-disable` comments from ticket 59 if the underlying functions have been migrated (unlikely — keep them if blast radius is still too large)
- Verify `pnpm lint` passes with 0 warnings

### Type replacement strategy

For each `any`, choose the most specific type available:

1. **If a type already exists** in `src/types/` → use it directly
2. **If the shape is known but no type exists** → define a new interface in the appropriate `src/types/` file
3. **If the shape is truly dynamic** (e.g., `field_mapping`, `static_data`) → use `Record<string, unknown>` and add type guards at usage sites
4. **If it's an error catch** → use `unknown` and extract message via `err instanceof Error ? err.message : String(err)`
5. **If it's a table column renderer** → use the row data type from the API response interface

### What NOT to change

- `apiFetch<T = any>` in `src/lib/api/server/base.ts` — already has `eslint-disable` from ticket 59; changing this would cascade to 755+ call sites
- `apiFetchFormData` return type in `src/lib/api/server/dossier-writer.ts` — same rationale
- `equipment.ts` server API functions — already have `eslint-disable` from ticket 59

## Testing Decisions

- **Primary test seam**: `tsc --noEmit` — this is the main verification that type replacements are correct. If TypeScript compiles, the types are structurally valid.
- **Secondary test seam**: `pnpm lint` — verify 0 `@typescript-eslint/no-explicit-any` warnings after each sub-ticket.
- **No new unit tests needed** — this is a type-only refactor. No runtime behavior changes.
- **Manual smoke test** deferred to ticket 50 (already marked done for automated verification; full browser testing should happen before production deploy).

## Out of Scope

- Changing backend API contracts to return more structured responses
- Adding runtime validation (e.g., Zod schemas) for API responses — that's a separate effort
- Refactoring the `apiFetch` generic default (ticket 59 already addressed this with eslint-disable)
- Fixing any new warnings introduced by other branches — rebase and fix forward

## Further Notes

- **Estimated effort**: ~2-3 hours of focused agent work across 6 sub-tickets
- **Risk**: Low. Each change is type-only and verified by `tsc --noEmit`. If a type is wrong, TypeScript will catch it immediately.
- **Rollback plan**: Each sub-ticket is a separate commit. If a sub-ticket causes issues, it can be reverted independently.
- **After completion**: Flip `@typescript-eslint/no-explicit-any` to "error" to prevent regression.
