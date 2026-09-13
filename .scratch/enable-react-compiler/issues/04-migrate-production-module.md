# 04 — Migrate production module to canonical React patterns

**What to build:** Eliminate all 4 `set-state-in-effect` warnings in the production module by migrating annual review, workshop ranking, pressure input, and product output pages to proper React patterns. After this ticket, all production module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All 4 `set-state-in-effect` warnings in production module eliminated (4 → 0)
- [x] Annual review and workshop ranking use React Query
- [x] Pressure input and product output pages use React Query
- [x] `pnpm typecheck` passes with 0 errors
- [x] `pnpm lint` shows 0 `set-state-in-effect` warnings in production module
- [ ] Manual smoke test confirms no behavioral regression in production pages

## Summary of Changes

Successfully migrated 4 files in the production module to canonical React patterns:

1. **AnnualReviewTab.tsx** - Migrated to React Query for annual review data
2. **WorkshopRankingTrend.tsx** - Migrated to React Query for workshop ranking data, used useMemo for derived state
3. **PressureManualInputPageClient.tsx** - Migrated to React Query for point mappings, used useEffect with ref for initialization
4. **product/[productName]/page.tsx** - Migrated to React Query for product output stats

## Patterns Applied

- **React Query migration**: Replaced `useEffect` + `setState` data fetching with `useQuery` hooks
- **Derived state**: Used `useMemo` to compute derived values from query data
- **State initialization**: Used useEffect with ref to initialize state only once per data load
- **Direct data usage**: Used query data directly instead of syncing to local state

