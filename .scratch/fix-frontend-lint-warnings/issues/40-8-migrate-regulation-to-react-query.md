# 40.8 — Migrate regulation module to React Query

**What to build:** Regulation list, generator, and revision pages use React Query with tabbed interface. This involves three related pages sharing regulation data.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Replace useEffect+useState data fetching with useQuery in `regulation/page.tsx`
- [ ] Replace useEffect+useState data fetching with useQuery in `regulation/generator/[id]/page.tsx`
- [ ] Replace useEffect+useState data fetching with useQuery in `regulation/revise/[id]/page.tsx`
- [ ] Remove duplicate state from `regulationStore.ts` and `revisionStore.ts` (keep only UI state)
- [ ] Handle tabbed interface with separate useQuery hooks for regulations and revisions
- [ ] Ensure proper cache invalidation when mutations occur (create, update, delete, submit, approve)
- [ ] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from regulation module
- [ ] `tsc --noEmit` passes with no errors
- [ ] Manual smoke test: regulation list loads, generator works, revision flow works
