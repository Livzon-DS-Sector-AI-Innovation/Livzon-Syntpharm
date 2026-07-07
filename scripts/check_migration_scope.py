#!/usr/bin/env python3
"""CI guard: validate that a migration only touches one module's schema.

Usage:
    python scripts/check_migration_scope.py <migration_file>

This script checks that a migration file only modifies tables within
a single module's schema. If it touches multiple schemas, it fails
with an error message.

Cross-module foreign keys are allowed (referent_schema is ignored).

Exit codes:
    0 - Migration is valid (single schema or no schema changes)
    1 - Migration touches multiple schemas (error)
    2 - Invalid usage or file not found
"""

import re
import sys
from pathlib import Path


# Migrations that are allowed to touch multiple schemas
# These are typically merge migrations or baseline migrations
MULTI_SCHEMA_ALLOWED = {
    "0001_baseline_full_schema.py",  # Initial baseline
    "0006_add_quality_qms_and_sop_ai_modules.py",  # Merge from quality-module-0623
    "0007_add_equipment_department_scoping_and_safety_enhancements.py",  # Merge from feature/safety-module
    "0008_add_training_teams_specialists_candidates_and_prejob_templates.py",  # Merge from xbj/lwz-peixun
}


def extract_schemas_from_migration(file_path: str) -> set[str]:
    """Extract all schema names referenced in a migration file.

    Only considers source_schema and schema parameters (tables being modified).
    Ignores referent_schema (foreign key targets) since cross-module FKs are allowed.
    """
    content = Path(file_path).read_text()

    # Patterns to match schema references
    patterns = [
        r'source_schema=["\'](\w+)["\']',  # source_schema="safety" (FK source)
        r'(?<!referent_)schema=["\'](\w+)["\']',  # schema='safety' but NOT referent_schema
        r"CREATE SCHEMA IF NOT EXISTS (\w+)",  # CREATE SCHEMA IF NOT EXISTS safety
    ]

    schemas = set()
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        schemas.update(matches)

    # Filter out system schemas
    system_schemas = {"public", "pg_catalog", "information_schema"}
    schemas = {s for s in schemas if s not in system_schemas}

    return schemas


def is_baseline_migration(file_path: str) -> bool:
    """Check if this is a baseline/initial migration."""
    filename = Path(file_path).name.lower()
    return "baseline" in filename or "initial" in filename


def is_multi_schema_allowed(file_path: str) -> bool:
    """Check if this migration is allowed to touch multiple schemas."""
    filename = Path(file_path).name
    return filename in MULTI_SCHEMA_ALLOWED


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_migration_scope.py <migration_file>")
        sys.exit(2)

    migration_file = sys.argv[1]

    if not Path(migration_file).exists():
        print(f"Error: File not found: {migration_file}")
        sys.exit(2)

    # Baseline migrations are allowed to touch multiple schemas
    if is_baseline_migration(migration_file):
        print(f"✓ {migration_file}: Baseline migration (multi-schema allowed)")
        sys.exit(0)

    # Check if this migration is explicitly allowed to touch multiple schemas
    if is_multi_schema_allowed(migration_file):
        print(f"✓ {migration_file}: Multi-schema merge migration (allowed)")
        sys.exit(0)

    schemas = extract_schemas_from_migration(migration_file)

    if len(schemas) == 0:
        print(f"✓ {migration_file}: No schema changes detected (OK)")
        sys.exit(0)
    elif len(schemas) == 1:
        schema = list(schemas)[0]
        print(f"✓ {migration_file}: Single schema '{schema}' (OK)")
        sys.exit(0)
    else:
        print(
            f"✗ {migration_file}: Multiple schemas detected: {', '.join(sorted(schemas))}"
        )
        print(
            "\nError: A migration should only touch tables within one module's schema."
        )
        print("If this migration includes changes from other modules, please:")
        print("  1. Discard this migration: rm " + migration_file)
        print("  2. Re-generate with --include-object filtering, or")
        print("  3. Manually edit to remove other modules' changes")
        sys.exit(1)


if __name__ == "__main__":
    main()
