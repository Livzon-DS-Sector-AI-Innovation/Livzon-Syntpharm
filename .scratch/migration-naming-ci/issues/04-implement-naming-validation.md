# 04 — Implement naming validation in CI

**What to build:** Add a validation function to the migration scope checker that enforces the NNNN naming convention for both filenames and revision IDs, with clear error messages that reference AGENTS.md.

**Blocked by:** None — can start immediately (but requires 01-03 to be complete for CI to pass)

**Status:** ready-for-agent

- [ ] Add `validate_naming_convention(file_path: str) -> tuple[bool, str]` function to `check_migration_scope.py`
- [ ] Extract filename without `.py` extension
- [ ] Extract revision ID from file content (parse `revision: str = '...'` or `revision = '...'`)
- [ ] Validate both against regex pattern `^\d{4}_[a-zA-Z0-9_]+$`
- [ ] Generate clear error message showing invalid filename/revision, expected pattern, and AGENTS.md reference
- [ ] Integrate validation into the migration file loop in `main()`
- [ ] Collect all violations before reporting
- [ ] Exit with code 1 if any violations found, code 0 if all pass
- [ ] Test with valid patterns: `0001_baseline`, `0055_add_sync_operation_log`
- [ ] Test with invalid patterns: `3cb28d1e1ac7`, `d89b9d01b93a`, `abc123`
- [ ] Test edge cases: uppercase letters, multiple underscores
