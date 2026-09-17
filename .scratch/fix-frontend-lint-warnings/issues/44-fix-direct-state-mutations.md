# 44 — Fix direct state mutations (immutability)

**What to build:** Fix all direct state mutations to use immutable update patterns. React Compiler requires immutable state updates.

**Blocked by:** Tickets 36-42 (data fetching migrated)

**Status:** done

- [x] All direct state mutations replaced with immutable updates
- [x] Arrays updated with spread/filter/map instead of push/pop/splice
- [x] Objects updated with spread instead of direct property assignment
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react-hooks/immutability warnings)

**Notes:**
Codebase has no `react-hooks/immutability` warnings. All state updates follow immutable patterns.
