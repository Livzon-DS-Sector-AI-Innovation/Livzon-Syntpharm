# 06 — Migrate registration module to canonical React patterns

**What to build:** Eliminate the 1 `set-state-in-effect` warning in the registration module by migrating the AI fill panel to proper React patterns. After this ticket, all registration module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** done

- [x] The 1 `set-state-in-effect` warning in registration module eliminated (1 → 0)
- [x] AI fill panel uses key prop approach for state reset
- [x] `pnpm typecheck` passes with 0 errors
- [x] `pnpm lint` shows 0 `set-state-in-effect` warnings in registration module
- [ ] Manual smoke test confirms no behavioral regression in registration pages

## Summary of Changes

Successfully migrated 2 files in the registration module to canonical React patterns:

1. **AiFillPanel.tsx** - Removed useEffect for state reset, component now remounts via key prop
2. **DossierWriterDetailPageClient.tsx** - Added key prop to AiFillPanel to force remount on chapter change

## Patterns Applied

- **Key prop for remount**: Used key prop on component to force remount when dependency changes, naturally resetting all state
- **Removed unnecessary useEffect**: Eliminated useEffect that was only used to reset state

