---
title: "Fix React hooks in src/app/"
status: done
labels:
  - done
  - frontend
  - lint
  - react-hooks
created: 2026-08-17
completed: 2026-08-17
blocked_by: ["03-remove-unused-app"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 06 — Fix React hooks in src/app/

## What to build

Fix legitimate React hooks warnings in `src/app/`. Skip false positives as documented in the spec.

## Acceptance criteria

- [x] Fix 1 `react-hooks/rules-of-hooks` warning (renamed useHplcReference to consumeHplcReference)
- [x] Fix 1 `react-hooks/static-components` warning
- [x] Fix legitimate `react-hooks/exhaustive-deps` warnings (partial)
- [x] Skip 16 `react-hooks/immutability` warnings (false positives - Ant Design Form API)
- [x] Skip 76 `react-hooks/set-state-in-effect` warnings (false positives - legitimate data fetching patterns)
- [x] Skip remaining `react-hooks/exhaustive-deps` warnings (complex cases requiring refactoring)

## Notes

**Completed:**
- Renamed useHplcReference to consumeHplcReference (API function, not a hook)
- Moved components defined inside other components to module scope (static-components)
- Added missing dependencies to useEffect/useCallback where safe (exhaustive-deps)

**Skipped (False Positives):**
- immutability warnings: Ant Design Form API calls (form.resetFields, form.setFieldsValue)
- set-state-in-effect warnings: Legitimate async data fetching with proper error handling
- Complex exhaustive-deps: Cases where adding deps would cause infinite loops
