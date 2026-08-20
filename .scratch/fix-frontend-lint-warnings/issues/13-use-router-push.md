# 13 — Use router.push instead of window.location (@next/next/no-location-assign)

**What to build:** Replace `window.location` assignments with Next.js router.push for proper client-side navigation.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `window.location` assignments replaced with `router.push`
- [ ] Navigation behavior preserved
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no @next/next/no-location-assign warnings)
