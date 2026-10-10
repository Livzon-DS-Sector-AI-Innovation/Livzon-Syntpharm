#!/usr/bin/env python3
"""CI guard: validate migration naming and single-module schema principle.

Usage:
    python scripts/check_migration_scope.py <migration_file>

This script performs two validations:
1. Naming convention: filename and revision ID must follow NNNN_descriptive_name pattern
2. Scope check: migration should only touch tables within one module

The single-module rule is judged per *module*, not per raw schema name. A
module owns its same-named primary schema and may own more, e.g. the `quality`
module owns both `quality` and `qms`. The schema -> module map is derived from
the filesystem so a new secondary schema needs no change to this script.

Cross-module foreign keys are allowed (referent_schema is ignored).

Exit codes:
    0 - Migration is valid
    1 - Validation failed (naming or scope)
    2 - Invalid usage or file not found
"""

import re
import sys
from pathlib import Path


# Naming convention pattern: NNNN_descriptive_name
# NNNN = 4 digits, followed by underscore, then alphanumeric/underscore
NAMING_PATTERN = re.compile(r"^\d{4}_[a-zA-Z0-9_]+$")


def validate_naming_convention(file_path: str) -> tuple[bool, list[str]]:
    """Validate that migration filename and revision ID follow NNNN naming convention.

    Returns:
        tuple[bool, list[str]]: (is_valid, list_of_errors)
    """
    path = Path(file_path)
    filename = path.stem  # filename without .py extension
    errors = []

    # Validate filename
    if not NAMING_PATTERN.match(filename):
        errors.append(
            f"  Filename: {filename}\n"
            f"  Expected pattern: NNNN_descriptive_name (4 digits, underscore, alphanumeric/underscore)\n"
            f"  See AGENTS.md: 迁移规范 > 命名规范"
        )

    # Extract revision ID from file content
    content = path.read_text()

    # Match revision: str = '...' or revision = '...'
    revision_match = re.search(r"revision(?:\s*:\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", content)

    if not revision_match:
        errors.append(
            "  Could not find revision ID in file\n"
            "  Expected: revision: str = 'NNNN_descriptive_name'\n"
            "  See AGENTS.md: 迁移规范 > 命名规范"
        )
    else:
        revision_id = revision_match.group(1)

        # Validate revision ID
        if not NAMING_PATTERN.match(revision_id):
            errors.append(
                f"  Revision ID: {revision_id}\n"
                f"  Expected pattern: NNNN_descriptive_name (4 digits, underscore, alphanumeric/underscore)\n"
                f"  See AGENTS.md: 迁移规范 > 命名规范"
            )

    return len(errors) == 0, errors


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


def _is_model_package(package: Path) -> bool:
    """Whether a package directory contains model definitions."""
    return (package / "models.py").is_file() or any(package.glob("*_models.py"))


def build_schema_module_map(modules_root: Path | None = None) -> dict[str, str]:
    """Derive the schema -> owning-module map from the filesystem.

    A module owns a schema named after itself (its primary schema). It also
    owns any schema named after a model-bearing package nested inside it, e.g.
    the `quality` module owns `qms` because `app/modules/quality/qms` contains
    model definitions.

    This over-approximates: a nested model-bearing package that never appears
    as a table's schema still maps its name to the enclosing module. That is
    safe because such a name cannot occur as a schema, so a wrong entry can
    only make the check more permissive for a name that cannot happen.
    """
    if modules_root is None:
        modules_root = Path(__file__).resolve().parents[2] / "app" / "modules"

    mapping: dict[str, str] = {}
    if not modules_root.is_dir():
        return mapping

    module_dirs = [d for d in sorted(modules_root.iterdir()) if d.is_dir() and not d.name.startswith(("_", "."))]

    # Pass 1: a module's primary schema is its own name.
    for module_dir in module_dirs:
        mapping.setdefault(module_dir.name, module_dir.name)

    # Pass 2: a nested model-bearing package belongs to its enclosing module.
    for module_dir in module_dirs:
        for package in sorted(module_dir.rglob("*")):
            if not package.is_dir() or package.name.startswith(("_", ".")):
                continue
            if _is_model_package(package):
                mapping.setdefault(package.name, module_dir.name)

    return mapping


def map_schemas_to_modules(schemas: set[str], schema_module_map: dict[str, str]) -> set[str]:
    """Collapse schema names to the modules that own them.

    Unknown schemas fall back to treating the schema name as the module, so a
    migration touching two genuinely unrelated unknown schemas still fails.
    """
    return {schema_module_map.get(schema, schema) for schema in schemas}


def validate_migration_scope(
    schemas: set[str], schema_module_map: dict[str, str] | None = None
) -> tuple[bool, set[str]]:
    """Judge the single-module rule for a set of schemas.

    Returns (is_valid, modules). Zero schemas is valid (nothing to judge); one
    module is valid; more than one module is a violation.
    """
    if schema_module_map is None:
        schema_module_map = build_schema_module_map()

    modules = map_schemas_to_modules(schemas, schema_module_map)
    return len(modules) <= 1, modules


# Architecture-approved cross-module migrations (core/infrastructure changes).
# These are exceptions to the single-module rule per AGENTS.md:
# "跨模块外键、platform/core/shared 级变更可以跨 schema，但必须由架构负责人审批"
ARCHITECTURE_APPROVED_EXCEPTIONS: frozenset[str] = frozenset()


def is_baseline_migration(file_path: str) -> bool:
    """Check if this is a baseline/initial migration or an approved exception."""
    filename = Path(file_path).stem.lower()
    if "baseline" in filename or "initial" in filename:
        return True
    for exception_id in ARCHITECTURE_APPROVED_EXCEPTIONS:
        if exception_id in filename:
            return True
    return False


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_migration_scope.py <migration_file>")
        sys.exit(2)

    migration_file = sys.argv[1]

    if not Path(migration_file).exists():
        print(f"Error: File not found: {migration_file}")
        sys.exit(2)

    # Check 1: Naming convention
    is_valid_naming, naming_errors = validate_naming_convention(migration_file)
    if not is_valid_naming:
        print(f"✗ Migration naming violation in {migration_file}:")
        for error in naming_errors:
            print(error)
        sys.exit(1)

    print(f"✓ {migration_file}: Naming convention valid")

    # Check 2: Scope (single-module principle, judged per module not per schema)
    # Baseline migrations are allowed to touch multiple schemas
    if is_baseline_migration(migration_file):
        print(f"✓ {migration_file}: Baseline migration (multi-schema allowed)")
        sys.exit(0)

    schemas = extract_schemas_from_migration(migration_file)

    if len(schemas) == 0:
        print(f"✓ {migration_file}: No schema changes detected (OK)")
        sys.exit(0)

    schema_module_map = build_schema_module_map()
    is_valid_scope, modules = validate_migration_scope(schemas, schema_module_map)

    if is_valid_scope:
        module = next(iter(modules), "?")
        print(f"✓ {migration_file}: Single module '{module}' (OK)")
        sys.exit(0)

    print(
        f"✗ {migration_file}: Multiple modules detected: "
        f"{', '.join(sorted(modules))} (from schemas: {', '.join(sorted(schemas))})"
    )
    print("\nError: A migration should only touch tables within one module.")
    print("If this migration includes changes from other modules, please:")
    print("  1. Discard this migration: rm " + migration_file)
    print("  2. Re-generate with --include-object filtering, or")
    print("  3. Manually edit to remove other modules' changes")
    sys.exit(1)


if __name__ == "__main__":
    main()
