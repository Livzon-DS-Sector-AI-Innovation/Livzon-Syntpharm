# 40.9 — Migrate hazard detail module to React Query

**What to build:** Hazard detail page with complex workflow uses React Query. This is the largest file (1734 lines) with multi-step workflow, script execution, and safety officer loading.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Replace useEffect+useState data fetching with useQuery in `hazard/[id]/page.tsx`
- [x] Remove duplicate state from `hazardStore.ts` (keep only UI state)
- [x] Handle complex data loading with dependent queries (hazard data + safety officer info)
- [x] Ensure proper cache invalidation when workflow actions occur (run script, approve, reject)
- [x] Handle error cases and redirects when hazard not found
- [x] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from hazard detail module
- [x] `tsc --noEmit` passes with no errors
- [x] Manual smoke test: hazard detail loads, workflow steps work, script execution succeeds
