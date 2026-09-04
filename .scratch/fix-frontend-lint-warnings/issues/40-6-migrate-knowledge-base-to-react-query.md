# 40.6 — Migrate knowledge base module to React Query

**What to build:** Knowledge base list uses React Query with complex filtering and menu-based navigation. Handle client-side filtering for menu keys (pending_sync, sync_failed, no_card).

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Replace useEffect+useState data fetching with useQuery in `knowledge-base/page.tsx`
- [ ] Remove duplicate state from `knowledgeStore.ts` (keep only UI state like selectedRowKeys, formOpen)
- [ ] Handle complex queryKey with multiple filter dependencies (statusFilter, categoryFilter, smartSearch, searchText, selectedMenuKey)
- [ ] Implement client-side filtering for menu-based views (pending_sync, sync_failed, no_card)
- [ ] Ensure proper cache invalidation when mutations occur (sync, generate card, create new version)
- [ ] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from knowledge base module
- [ ] `tsc --noEmit` passes with no errors
- [ ] Manual smoke test: knowledge base list loads, menu navigation works, filters work
