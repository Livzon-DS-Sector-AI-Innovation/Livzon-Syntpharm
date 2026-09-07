# 45.8 — Fix exhaustive-deps in Registration and Procurement modules

**What to build:** Fix all React hooks dependency warnings in the Registration and Procurement modules so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] RegulationDashboardClient.tsx has no exhaustive-deps warnings
- [ ] ReviewPageClient.tsx has no exhaustive-deps warnings
- [ ] PurchaseRequestFormClient.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
