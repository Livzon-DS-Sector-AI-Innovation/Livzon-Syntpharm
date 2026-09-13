# 13 — Use router.push instead of window.location (@next/next/no-location-assign)

**What to build:** Replace `window.location` assignments with Next.js router.push for proper client-side navigation.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `window.location` assignments replaced with `router.push`
- [x] Navigation behavior preserved
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @next/next/no-location-assign warnings)

## Summary

Fixed 5 @next/next/no-location-assign warnings across 4 files:
- AnnualPlanListClient.tsx: added useRouter, replaced navigation after plan creation
- TrainingLedgerClient.tsx: added useRouter, replaced navigation on employee select
- TrainingLedgerNewClient.tsx: added useRouter, replaced 2 navigation instances
- TrainingSelectTasksClient.tsx: added useRouter, replaced navigation after token import

All navigation now uses Next.js router for proper client-side routing.
