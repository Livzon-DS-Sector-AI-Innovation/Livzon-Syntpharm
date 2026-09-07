# 45.9 — Fix remaining exhaustive-deps warnings

**What to build:** Fix any remaining React hooks dependency warnings that were not covered by tickets 45.1-45.8, including edge cases and integration issues.

**Blocked by:** 45.1, 45.2, 45.3, 45.4, 45.5, 45.6, 45.7, 45.8

**Status:** ready-for-agent

- [ ] regulation/generator/page.tsx has no exhaustive-deps warnings
- [ ] All other remaining files have no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for all affected files
