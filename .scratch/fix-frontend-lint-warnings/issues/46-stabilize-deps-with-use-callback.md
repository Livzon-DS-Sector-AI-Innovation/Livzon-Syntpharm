# 46 — Stabilize deps with useCallback (exhaustive-deps)

**What to build:** Wrap inline functions in useCallback to stabilize them as dependencies. This prevents effects from running too often.

**Blocked by:** Ticket 45 (deps added)

**Status:** done

- [x] Inline functions used as deps wrapped in useCallback
- [x] useCallback dependencies properly specified
- [x] Effects run only when actual data changes
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react-hooks/exhaustive-deps warnings)

**Notes:**
- All inline functions used as dependencies have been wrapped in useCallback
- All useCallback dependencies are properly specified
- Zero exhaustive-deps warnings remaining in the codebase
- Work completed as part of tickets 45.11-45.20
