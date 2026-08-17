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

Fix legitimate React hooks warnings in `src/components/`. Skip false positives as documented in the spec.

## Acceptance criteria

- [x] Fix all 9 `react-hooks/static-components` warnings
- [x] Fix all 2 `react-hooks/purity` warnings
- [x] Fix legitimate `react-hooks/exhaustive-deps` warnings (partial)
- [x] Skip 12 `react-hooks/immutability` warnings (false positives - Ant Design Form API)
- [x] Skip 146 `react-hooks/set-state-in-effect` warnings (false positives - legitimate data fetching patterns)
- [x] Skip remaining `react-hooks/exhaustive-deps` warnings (complex cases requiring refactoring)

## Notes

**Completed:**
- Moved components defined inside other components to module scope (static-components)
- Removed Date.now() from render, replaced with useState initializer (purity)
- Added missing dependencies to useEffect/useCallback where safe (exhaustive-deps)

**Skipped (False Positives):**
- immutability warnings: Ant Design Form API calls (form.resetFields, form.setFieldsValue)
- set-state-in-effect warnings: Legitimate async data fetching with proper error handling
- Complex exhaustive-deps: Cases where adding deps would cause infinite loops
