#!/usr/bin/env python3
"""CI guard: migration numbering rules that span the whole versions directory.

Usage:
    python scripts/ci/check_migration_numbers.py [migration_dir]

`check_migration_scope.py` only ever looks at one file, so it cannot see these two
cross-file rules (AGENTS.md: 迁移规范 > 命名规范):

1. Global uniqueness — no two migration files may share the same 4-digit NNNN prefix, and a
   file's filename prefix must match the prefix of its `revision` ID.
2. Referential integrity — every revision listed in `down_revision` must exist.

Exit codes:
    0 - Migration numbering is valid
    1 - Validation failed
    2 - Invalid usage or directory not found
"""

import ast
import re
import sys
from pathlib import Path


DEFAULT_MIGRATIONS_DIR = "alembic/versions"

# Naming convention pattern: NNNN_descriptive_name (NNNN = 4 digits)
NAME_PATTERN = re.compile(r"^\d{4}_[a-zA-Z0-9_]+$")


class Migration:
    """A parsed migration file: its path, revision ID and declared parents."""

    def __init__(self, path: Path, revision: str | None, down_revisions: list[str]) -> None:
        self.path = path
        self.revision = revision
        self.down_revisions = down_revisions

    @property
    def prefix(self) -> str:
        return self.path.stem.split("_", 1)[0]


def _read_assignment(tree: ast.Module, name: str) -> ast.expr | None:
    """Return the value node assigned to `name` at module level (plain or annotated)."""
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                return node.value
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.value
    return None


def _literal_strings(node: ast.expr | None) -> list[str]:
    """Return the string(s) assigned in `node`, handling str, tuple/list and None."""
    if node is None:
        return []
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return []
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (tuple, list)):
        return [item for item in value if isinstance(item, str)]
    return []


def discover_migrations(directory: Path) -> list[Migration]:
    """Parse every migration file in `directory`."""
    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            migrations.append(Migration(path, None, []))
            continue
        revisions = _literal_strings(_read_assignment(tree, "revision"))
        down_revisions = _literal_strings(_read_assignment(tree, "down_revision"))
        migrations.append(Migration(path, revisions[0] if revisions else None, down_revisions))
    return migrations


def validate_migration_numbers(directory: str) -> list[str]:
    """Validate numbering uniqueness and referential integrity.

    Returns:
        list[str]: human-readable violations; empty means the directory is valid.
    """
    migrations = discover_migrations(Path(directory))
    errors: list[str] = []

    by_prefix: dict[str, list[str]] = {}
    known_revisions: set[str] = set()

    for migration in migrations:
        if migration.revision is None:
            errors.append(f"{migration.path.name}: could not find a `revision` assignment")
            continue
        if not NAME_PATTERN.match(migration.revision):
            errors.append(
                f"{migration.path.name}: revision '{migration.revision}' does not match "
                "NNNN_descriptive_name (4 digits, underscore, alphanumeric/underscore)"
            )
            continue
        if migration.revision.split("_", 1)[0] != migration.prefix:
            errors.append(
                f"{migration.path.name}: filename prefix '{migration.prefix}' does not match "
                f"revision prefix '{migration.revision.split('_', 1)[0]}'"
            )
        known_revisions.add(migration.revision)
        by_prefix.setdefault(migration.prefix, []).append(migration.path.name)

    for prefix, filenames in sorted(by_prefix.items()):
        if len(filenames) > 1:
            joined = ", ".join(filenames)
            errors.append(f"duplicate NNNN prefix '{prefix}' shared by: {joined}")

    for migration in migrations:
        for parent in migration.down_revisions:
            if parent not in known_revisions:
                errors.append(
                    f"{migration.path.name}: down_revision '{parent}' does not match any migration's revision"
                )

    return errors


def main() -> None:
    if len(sys.argv) > 2:
        print("Usage: python scripts/ci/check_migration_numbers.py [migration_dir]")
        sys.exit(2)

    directory = sys.argv[1] if len(sys.argv) == 2 else DEFAULT_MIGRATIONS_DIR

    if not Path(directory).is_dir():
        print(f"Error: directory not found: {directory}")
        sys.exit(2)

    errors = validate_migration_numbers(directory)

    if errors:
        print(f"✗ Migration numbering violations in {directory}:")
        for error in errors:
            print(f"  {error}")
        print("\nSee AGENTS.md: 迁移规范 > 命名规范 (NNNN prefixes must be globally unique).")
        sys.exit(1)

    print(f"✓ {directory}: NNNN prefixes are globally unique and all down_revision references resolve")


if __name__ == "__main__":
    main()
