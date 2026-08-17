---
title: "Fix React hooks in src/components/"
status: done
labels:
  - done
  - frontend
  - lint
  - react-hooks
created: 2026-08-17
completed: 2026-08-17
blocked_by: ["02-remove-unused-components"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 05 — Fix React hooks in src/components/

## What to build

Fix legitimate React hooks warnings in `src/components/`. Skip false positives and defer complex cases.

## Acceptance criteria

- [x] Fix all 9 `react-hooks/static-components` warnings
- [x] Fix all 2 `react-hooks/purity` warnings
- [x] Fix legitimate `react-hooks/exhaustive-deps` warnings (partial)
- [x] Skip 12 `react-hooks/immutability` warnings (false positives - Ant Design Form API)
- [x] Defer 146 `react-hooks/set-state-in-effect` warnings (real but high refactoring cost)
- [x] Defer remaining `react-hooks/exhaustive-deps` warnings (real but complex cases)

## Notes

**Completed:**
- Moved components defined inside other components to module scope (static-components)
- Removed Date.now() from render, replaced with useState initializer (purity)
- Added missing dependencies to useEffect/useCallback where safe (exhaustive-deps)

**Skipped (False Positives):**
- immutability warnings: Ant Design Form API calls (form.resetFields, form.setFieldsValue)

**Deferred (Real warnings, high cost):**
- set-state-in-effect warnings: Require refactoring data fetching patterns
- Complex exhaustive-deps: Cases where adding deps would cause infinite loops or require significant refactoring
