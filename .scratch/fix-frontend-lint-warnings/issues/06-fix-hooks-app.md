---
title: "Fix React hooks in src/app/"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
updated: 2026-08-19
blocked_by: []
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 06 — Fix React hooks in src/app/

## What to build

After this ticket, all fixable React hooks warnings in `src/app/` are resolved. This includes `static-components`, `purity`, and `rules-of-hooks` warnings.

## Acceptance criteria

- [ ] Run `pnpm lint` and verify zero fixable React hooks warnings in `src/app/`
- [ ] Fix `static-components` warnings (components defined inside other components)
- [ ] Fix `purity` warnings (impure render functions)
- [ ] Fix `rules-of-hooks` warnings (hooks called conditionally)
- [ ] Manually verify affected pages still render correctly
- [ ] No infinite re-render loops introduced

## Notes

**Status update (2026-08-19):** Despite being marked done, `src/app/` still has React hooks warnings. This ticket needs to be completed.

**Skipped warnings (false positives):**
- `set-state-in-effect`: Legitimate data fetching patterns
- `exhaustive-deps`: Complex dependency cases
- `immutability`: Ant Design Form API calls

These are intentionally skipped per the spec's "False Positives" section.
