# 64 — Replace `any` in quality & registration pages

**What to build:** All quality and registration page components use proper types instead of `any`. This is the largest group with 60 warnings. The `static-data/page.tsx` file alone has 20 warnings and needs careful typing of dynamic form fields and filter states. Many pages use dynamic data from backend that needs `Record<string, unknown>` or specific interfaces.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All `any` types replaced with proper types in quality pages
- [x] All `any` types replaced with proper types in registration pages
- [x] Dynamic form fields and filter states properly typed
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows 0 `@typescript-eslint/no-explicit-any` warnings in quality & registration pages
- [ ] Affected files: `static-data/page.tsx` (20 warnings), `static-data/[module]/[id]/page.tsx` (14 warnings), `inspection-table/[id]/page.tsx`, `instrument/list/page.tsx`, `deviation-flow/query/page.tsx`, `inspection/standards/page.tsx`, `material-report/` pages, `registration/ledger/page.tsx`, `registration/validation-audit/` pages
