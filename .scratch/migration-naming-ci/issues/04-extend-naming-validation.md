# Extend check_migration_scope.py with Naming Validation

## Status
ready-for-agent

## Description
Add a new function to validate migration naming conventions in `backend/scripts/ci/check_migration_scope.py`.

## Implementation Details

### New Function: `validate_naming_convention(file_path: str) -> tuple[bool, str]`

**Logic:**
1. Extract filename without `.py` extension
2. Extract revision ID from the file content (parse `revision: str = '...'` or `revision = '...'`)
3. Validate both against regex: `^\d{4}_[a-zA-Z0-9_]+$`
4. Return (is_valid, error_message)

**Error Message Format:**
```
✗ Migration naming violation in {filename}:
  Filename: {actual_filename}
  Revision ID: {actual_revision}
  Expected pattern: NNNN_descriptive_name (4 digits, underscore, alphanumeric)
  See AGENTS.md: 迁移规范 > 命名规范
```

### Integration
- Call `validate_naming_convention()` for each migration file in the loop
- Collect all violations before reporting
- Exit with code 1 if any violations found

## Testing
- Test with valid filenames: `0001_baseline`, `0055_add_sync_operation_log`
- Test with invalid filenames: `3cb28d1e1ac7`, `d89b9d01b93a`, `abc123`
- Test with valid revision IDs that don't match filename (allowed)
- Test edge cases: uppercase letters, multiple underscores

## Acceptance Criteria
- Function correctly identifies valid and invalid naming patterns
- Error messages are clear and reference AGENTS.md
- Script exits with appropriate code (0 for success, 1 for violations)
- No false positives on existing valid migrations
