# 66 — Replace `any` in components, stores, lib, e2e

**What to build:** All shared components, stores, utilities, and test files use proper types instead of `any`. This includes client-side API fetch helpers, Excel export utilities, PDF extraction, validation schemas, workflow templates, and e2e test setup.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All `any` types replaced with proper types in shared components
- [x] All `any` types replaced with proper types in stores
- [x] All `any` types replaced with proper types in lib utilities
- [x] All `any` types replaced with proper types in e2e tests
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows 0 `@typescript-eslint/no-explicit-any` warnings in components, stores, lib, e2e
- [x] Affected files: `components/hr/TrainingNotificationClient.tsx`, `lib/api/client.ts`, `lib/utils/export-excel.ts`, `lib/pdf-extract.ts`, `lib/validation/schemas.ts`, `lib/workflow-templates.ts`, `stores/regulation.ts`, `e2e/auth.setup.ts`, `e2e/routes.spec.ts`, `app/hr/training/select/page.tsx`
