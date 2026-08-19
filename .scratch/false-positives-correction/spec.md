---
title: "Correction: False Positives Classification"
status: done
labels:
  - done
  - documentation
created: 2026-08-17
---

# Correction: False Positives Classification

## Previous Error

Previously documented 426 warnings as "false positives":
- 27 immutability
- 222 set-state-in-effect  
- 177 exhaustive-deps

## Correction

**Only immutability warnings (27) are true false positives.**

The other 399 warnings are **real issues** but were deferred due to high fix cost:

### `react-hooks/set-state-in-effect` (222 warnings) - REAL, DEFERRED
These are legitimate warnings about setState calls inside useEffect. While the current code patterns are generally safe (async operations with error handling), they technically violate React best practices. Fixing them would require significant refactoring of data fetching patterns across the codebase.

**Status**: Real warnings, deferred due to refactoring cost

### `react-hooks/exhaustive-deps` (177 warnings) - REAL, DEFERRED  
These are legitimate warnings about missing dependencies in useEffect/useCallback. After fixing the straightforward cases, 177 remain. These are complex cases where:
- Adding dependencies could cause infinite loops
- Dependencies are intentionally omitted for performance
- Code uses refs or other patterns that complicate the analysis

**Status**: Real warnings, deferred due to complexity

### `react-hooks/immutability` (27 warnings) - FALSE POSITIVES
These are triggered by legitimate Ant Design Form API calls (form.resetFields, form.setFieldsValue). The linter doesn't recognize these as safe operations.

**Status**: True false positives, skipped

## Updated Summary

- **True false positives**: 27 (immutability only)
- **Real warnings, deferred**: 399 (222 set-state-in-effect + 177 exhaustive-deps)
- **Total skipped**: 426
- **Reason for deferral**: High refactoring cost, not false positives
