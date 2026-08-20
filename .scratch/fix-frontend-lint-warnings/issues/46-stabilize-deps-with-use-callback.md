# 46 — Stabilize deps with useCallback (exhaustive-deps)

**What to build:** Wrap inline functions in useCallback to stabilize them as dependencies. This prevents effects from running too often.

**Blocked by:** Ticket 45 (deps added)

**Status:** ready-for-agent

- [ ] Inline functions used as deps wrapped in useCallback
- [ ] useCallback dependencies properly specified
- [ ] Effects run only when actual data changes
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/exhaustive-deps warnings)
