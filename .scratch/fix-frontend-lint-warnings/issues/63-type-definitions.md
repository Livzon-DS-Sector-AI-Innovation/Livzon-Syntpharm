# 63 — Replace `any` in type definitions (`src/types/`)

**What to build:** All type definition files in `src/types/` use proper types instead of `any`. This includes replacing `Record<string, any>` with specific field types or `Record<string, unknown>`, replacing `any[]` with typed arrays, and replacing `[key: string]: any` index signatures with specific interfaces. This makes the domain model type-safe and self-documenting.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `Record<string, any>` replaced with specific types or `Record<string, unknown>`
- [ ] All `any[]` replaced with typed arrays (e.g., `CapaProposal[]`, `ReportVersion[]`)
- [ ] All `[key: string]: any` index signatures replaced with specific interfaces
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows 0 `@typescript-eslint/no-explicit-any` warnings in `src/types/`
- [ ] Affected files: `quality.ts`, `material-report.ts`, `hr.ts`, `settings.ts`, `static-data.ts`, `equipment/equipment.ts`, `equipment/generated-bridge.ts`, `inspection-table.ts`, `quality-cpv.ts`, `doc-check.ts`, `research/process-optimization.ts`, `safety/hazard.ts`, `sop-ai.ts`
