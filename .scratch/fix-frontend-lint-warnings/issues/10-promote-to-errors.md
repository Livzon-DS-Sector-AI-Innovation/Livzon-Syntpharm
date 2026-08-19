---
title: "Promote lint rules to errors"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
updated: 2026-08-19
blocked_by:
  - 07-replace-any-components
  - 08-replace-any-app
  - 09-replace-any-remaining
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 10 — Promote lint rules to errors

## What to build

After this ticket, all ESLint rules that were previously warnings are promoted to errors. This ensures CI blocks any future regressions.

## Acceptance criteria

- [ ] Update `eslint.config.mjs` to promote rules from `warn` to `error`:
  - `@typescript-eslint/no-explicit-any`
  - `@typescript-eslint/no-unused-vars`
  - `react-hooks/*` rules (except the false positives documented in the spec)
- [ ] Run `pnpm lint` and verify zero warnings (all issues are now errors)
- [ ] CI pipeline fails if any lint errors are present
- [ ] No runtime behavior changes

## Notes

**Blocked by:** Tickets 07, 08, and 09 must complete first. All `any` types must be replaced before promoting the rule to error.

**False positives to keep as warnings:**
The following rules should remain as warnings (not promoted to errors) per the spec:
- `react-hooks/set-state-in-effect` (222 warnings - legitimate data fetching patterns)
- `react-hooks/exhaustive-deps` (176 warnings - complex dependency cases)
- `react-hooks/immutability` (27 warnings - Ant Design Form API calls)

These are documented as false positives in the spec and require significant refactoring to fix.
