---
title: "Fix React hooks in src/components/"
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

# 05 — Fix React hooks in src/components/

## What to build

After this ticket, all fixable React hooks warnings in `src/components/` are resolved. This includes `static-components`, `purity`, and `rules-of-hooks` warnings.

## Acceptance criteria

- [ ] Run `pnpm lint` and verify zero fixable React hooks warnings in `src/components/`
- [ ] Fix `static-components` warnings (components defined inside other components)
- [ ] Fix `purity` warnings (impure render functions)
- [ ] Fix `rules-of-hooks` warnings (hooks called conditionally)
- [ ] Manually verify affected pages still render correctly
- [ ] No infinite re-render loops introduced

## Notes

**Status update (2026-08-19):** Despite being marked done, `src/components/` still has React hooks warnings. This ticket needs to be completed.

**Skipped warnings (false positives):**
- `set-state-in-effect`: 222 warnings (legitimate data fetching patterns)
- `exhaustive-deps`: 176 warnings (complex dependency cases)
- `immutability`: 27 warnings (Ant Design Form API calls)

These are intentionally skipped per the spec's "False Positives" section.
