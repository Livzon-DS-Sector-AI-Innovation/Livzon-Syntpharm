# 61 — Remove unused vars in app pages

**What to build:** Remove or prefix with `_` all unused variables/imports in src/app/(dashboard)/*/page.tsx files

**Status:** ready-for-agent

## Files to fix (sample)

- src/app/(dashboard)/administration/login-logs/page.tsx: LoginLog, queryClient
- src/app/(dashboard)/administration/vehicles/page.tsx: useQueryClient, refetch
- src/app/(dashboard)/equipment/assets/page.tsx: various unused vars
- src/app/(dashboard)/hr/onboarding/page.tsx: various unused vars
- src/app/(dashboard)/production/output/daily/page.tsx: various unused vars
- src/app/(dashboard)/quality/deviation/page.tsx: various unused vars
- src/app/(dashboard)/registration/validation-audit/page.tsx: various unused vars
- src/app/(dashboard)/research/projects/page.tsx: various unused vars
- src/app/(dashboard)/safety/hazard-inspection/ledger/page.tsx: various unused vars

## Acceptance Criteria

- [ ] All unused vars removed or prefixed with `_` in page.tsx files
- [ ] `pnpm lint` shows 0 `@typescript-eslint/no-unused-vars` warnings in src/app/
- [ ] `tsc --noEmit` passes
