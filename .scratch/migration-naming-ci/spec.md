# Migration Naming Convention CI Check

## Problem Statement

The AGENTS.md migration rules explicitly forbid Alembic-generated hash IDs (e.g., `3cb28d1e1ac7`) and require sequential numbering (`NNNN_descriptive_name.py`), but the CI pipeline does not enforce this. The current `check_migration_scope.py` only validates the single-module principle.

As a result, 8 stale migration files with hash prefixes exist in the repository, and 1 merge migration uses a hash revision ID. These violations can slip through CI undetected.

## Solution

Extend the existing `check_migration_scope.py` script to validate migration naming conventions. The check will:

1. Validate that both filename and revision ID follow the pattern `^\d{4}_[a-zA-Z0-9_]+$`
2. Run as part of the existing `migration-scope` CI subcommand
3. Provide detailed error messages with AGENTS.md references

Before enabling the check, fix all pre-existing violations:
- Delete 8 stale hash-prefixed migration files (duplicates of correctly-named files)
- Regenerate the merge migration with proper naming

## User Stories

1. As a developer, I want the CI to reject migrations with hash IDs, so that I catch naming violations before merging
2. As a developer, I want clear error messages when naming validation fails, so that I can fix the issue quickly without looking up AGENTS.md
3. As a developer, I want the naming check to run alongside the scope check, so that I have a single CI command for migration validation
4. As a developer, I want all existing naming violations fixed, so that the codebase is consistent and the new check passes
5. As a developer, I want merge migrations to follow the same naming convention, so that there are no special cases or exceptions
6. As a developer, I want the validation regex to allow both uppercase and lowercase letters, so that it matches common naming patterns
7. As a reviewer, I want the CI to automatically catch naming violations, so that I don't have to manually check each migration file

## Implementation Decisions

### Validation Logic
- Check both filename (without `.py` extension) and revision ID
- Use regex pattern: `^\d{4}_[a-zA-Z0-9_]+$`
- Allow uppercase and lowercase letters in the descriptive name
- Reject any hash-based identifiers (12-character hex strings)

### Error Messages
- Display the invalid filename or revision ID
- Show the expected pattern
- Reference the AGENTS.md section on migration naming conventions
- Provide actionable guidance (e.g., "Rename to NNNN_descriptive_name.py")

### Script Structure
- Extend `backend/scripts/ci/check_migration_scope.py` with a new function `validate_naming_convention()`
- The function extracts the revision ID from the migration file and validates both filename and revision ID
- Integrate into the existing `run_migration_scope()` function in `ci.sh`

### Pre-existing Violations
- Delete 8 stale hash-prefixed files:
  - `1f550ec06f66_0038_add_product_sync_config.py`
  - `29a5a96069e8_add_energy_product_conversion_table.py`
  - `2eb6d687679e_0042_add_chapter_asset_usages.py`
  - `49684887bf7e_0045_energy_add_workshop_and_steam.py`
  - `6379b65e0052_0041_equipment_add_fields.py`
  - `74a464371488_0044_rename_equipment_no_to_asset_no.py`
  - `fcb768b8df78_0043_fix_production_index_names.py`
  - (Note: `29a5a96069e8` is referenced by the merge migration, so it may need special handling)
- Regenerate merge migration `d89b9d01b93a_merge_migration_heads.py`:
  - Delete the existing file
  - Run `alembic merge heads -m "0056_merge_migration_heads"` to create a new one with proper naming
  - The new migration will have revision ID `0056_merge_migration_heads`

### Merge Migration Handling
- No exception for merge migrations — they must follow the same naming convention
- The merge migration is a no-op (empty `upgrade()`/`downgrade()`), so regenerating it is safe
- The new merge migration will be numbered `0056` since `0055` is the current head

## Testing Decisions

### What Makes a Good Test
- Test the validation function in isolation with various filename/revision ID combinations
- Test both valid and invalid patterns
- Test edge cases (uppercase, lowercase, numbers, underscores)
- Test that the CI script correctly identifies violations

### Test Coverage
- Valid patterns: `0001_baseline`, `0055_add_sync_operation_log`, `0056_merge_migration_heads`
- Invalid patterns: `3cb28d1e1ac7`, `d89b9d01b93a`, `abc123`, `0001`
- Edge cases: `0001_Baseline` (uppercase), `0001_baseline_full_schema` (multiple underscores)

### Prior Art
- The existing `check_migration_scope.py` script provides a pattern for validation functions
- The script uses regex patterns to extract schema names — similar approach for naming validation

## Out of Scope

- Modifying the single-module principle check (already implemented)
- Changing the Alembic configuration or migration generation process
- Adding automatic renaming or fixing tools (developers must fix manually)
- Enforcing naming conventions on historical migrations that are already applied (only new migrations)

## Further Notes

### Stale Files Investigation
The 8 hash-prefixed files appear to be stale duplicates from earlier migration attempts. The correctly-named versions (e.g., `0038_add_product_sync_config.py`) already exist in the repository. These stale files should be safe to delete.

### Merge Migration Regeneration
The merge migration `d89b9d01b93a` reconciles two branches:
- `0055_add_sync_operation_log`
- `29a5a96069e8` (which itself is a hash-prefixed file)

After deleting the stale `29a5a96069e8` file, the merge migration may need to be regenerated to point to the correct parent. Verify the migration chain before regenerating.

### CI Integration
The naming check will run as part of `backend/scripts/ci/ci.sh migration-scope`, which is already called in the CI pipeline. No changes to the CI workflow configuration are needed.
