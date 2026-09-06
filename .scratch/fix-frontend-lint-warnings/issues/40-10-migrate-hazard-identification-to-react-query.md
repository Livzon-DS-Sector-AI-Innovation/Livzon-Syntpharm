# 40.10 — Migrate hazard identification module to React Query

**What to build:** Hazard identification creation and detail pages use React Query with AI workflow integration. This involves two related pages with complex state management.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Replace useEffect+useState data fetching with useQuery in `hazard-identification/new/page.tsx`
- [x] Replace useEffect+useState data fetching with useQuery in `hazard-identification/[id]/page.tsx`
- [x] Remove duplicate state from `hazardIdentificationStore.ts` (keep only UI state)
- [x] Handle regulation loading for the creation form
- [x] Ensure proper cache invalidation when AI workflow actions occur (run script, approve, reject)
- [x] Handle error cases and redirects when identification not found
- [x] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from hazard identification module
- [x] `tsc --noEmit` passes with no errors
- [x] Manual smoke test: creation form loads regulations, detail page loads, AI workflow works
