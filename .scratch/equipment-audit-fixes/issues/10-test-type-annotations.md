# 10: Test Infrastructure - Type Annotations

**What to build:** Remove all `# type: ignore[arg-type]` suppressions in equipment tests by defining proper Protocol types for mock objects, so that type errors are caught at compile time and tests have proper type safety.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Define Protocol types for mock database objects
- [ ] Remove all `# type: ignore[arg-type]` suppressions from equipment tests
- [ ] Ensure mypy type checking passes
- [ ] All existing tests continue to pass
- [ ] No type suppressions remain in equipment tests
