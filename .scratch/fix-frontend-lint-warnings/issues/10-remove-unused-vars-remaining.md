# 10 — Remove unused vars in remaining directories/

**What to build:** Delete all unused imports and variables in remaining files (types, utils, etc.). No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All unused imports removed from remaining files
- [x] All unused variables removed from remaining files
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (warning count decreases)

## Summary

Fixed 107 unused vars across multiple parts:

**Part 1: stores and types (23 vars)**
- stores/dossier-writer.ts: removed 1 unused import
- stores/quality.ts: removed 2 unused types
- stores/research/route-development.ts: removed 5 unused types
- stores/sop-ai.ts: removed 3 unused types
- types/quality.ts: removed 1 unused import
- types/safety/*.ts: removed 11 unused imports across 6 files

**Part 2: app pages (84 vars)**
- Fixed unused vars across 40+ app page files
- Removed unused imports, prefixed unused catch variables and state setters
- Removed unused interfaces and type definitions

All changes pass typecheck with no errors.
ESLint shows 0 unused vars warnings in src/app/.
