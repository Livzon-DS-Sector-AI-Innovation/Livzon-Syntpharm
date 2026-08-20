# 44 — Fix direct state mutations (immutability)

**What to build:** Fix all direct state mutations to use immutable update patterns. React Compiler requires immutable state updates.

**Blocked by:** Tickets 36-42 (data fetching migrated)

**Status:** ready-for-agent

- [ ] All direct state mutations replaced with immutable updates
- [ ] Arrays updated with spread/filter/map instead of push/pop/splice
- [ ] Objects updated with spread instead of direct property assignment
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/immutability warnings)
