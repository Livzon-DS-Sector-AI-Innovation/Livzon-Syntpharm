# 46.11 — Verify all exhaustive-deps warnings are fixed

**What to build:** Run final verification to ensure all exhaustive-deps warnings have been resolved across the entire codebase, and update the parent ticket status.

**Blocked by:** 46.1, 46.2, 46.3, 46.4, 46.5, 46.6, 46.7, 46.8, 46.9, 46.10

**Status:** ready-for-agent

- [ ] `pnpm lint` shows 0 exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] Parent ticket 46 marked as done
- [ ] All sub-tickets marked as done
