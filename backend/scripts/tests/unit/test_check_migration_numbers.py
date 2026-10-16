"""Tests for migration numbering uniqueness and referential integrity validation."""

from pathlib import Path

from scripts.ci.check_migration_numbers import validate_migration_numbers


def _write_migration(
    directory: Path,
    filename: str,
    revision: str,
    down_revision: str | None = None,
    parents: tuple[str, ...] | None = None,
) -> None:
    if parents is not None:
        down_line = f"down_revision: tuple[str, ...] = {parents!r}\n"
    elif down_revision is None:
        down_line = "down_revision: str | None = None\n"
    else:
        down_line = f"down_revision: str | None = {down_revision!r}\n"
    (directory / filename).write_text(f"revision: str = {revision!r}\n{down_line}")


class TestMigrationNumbers:
    """Test the validate_migration_numbers function."""

    def test_unique_numbers_ok(self, tmp_path: Path) -> None:
        """Distinct NNNN prefixes with a resolving chain are valid."""
        _write_migration(tmp_path, "0001_baseline.py", "0001_baseline", None)
        _write_migration(tmp_path, "0002_next.py", "0002_next", "0001_baseline")

        assert validate_migration_numbers(str(tmp_path)) == []

    def test_tuple_down_revision_ok(self, tmp_path: Path) -> None:
        """A merge migration listing several parents is valid."""
        _write_migration(tmp_path, "0001_baseline.py", "0001_baseline", None)
        _write_migration(tmp_path, "0002_a.py", "0002_a", "0001_baseline")
        _write_migration(tmp_path, "0003_merge.py", "0003_merge", parents=("0002_a", "0001_baseline"))

        assert validate_migration_numbers(str(tmp_path)) == []

    def test_duplicate_prefix_fails(self, tmp_path: Path) -> None:
        """Two files sharing an NNNN prefix are a violation."""
        _write_migration(tmp_path, "0001_baseline.py", "0001_baseline", None)
        _write_migration(tmp_path, "0001_other.py", "0001_other", "0001_baseline")

        errors = validate_migration_numbers(str(tmp_path))

        assert any("duplicate NNNN prefix '0001'" in error for error in errors)

    def test_dangling_down_revision_fails(self, tmp_path: Path) -> None:
        """A down_revision that matches no migration's revision is a violation."""
        _write_migration(tmp_path, "0001_baseline.py", "0001_baseline", "0999_missing")

        errors = validate_migration_numbers(str(tmp_path))

        assert any("0999_missing" in error and "does not match any migration" in error for error in errors)

    def test_filename_revision_prefix_mismatch_fails(self, tmp_path: Path) -> None:
        """Filename and revision prefixes must agree."""
        _write_migration(tmp_path, "0001_baseline.py", "0002_baseline", None)

        errors = validate_migration_numbers(str(tmp_path))

        assert any("filename prefix '0001' does not match revision prefix '0002'" in error for error in errors)

    def test_missing_revision_fails(self, tmp_path: Path) -> None:
        """A file without a revision assignment is a violation."""
        (tmp_path / "0001_baseline.py").write_text("# no revision here\n")

        errors = validate_migration_numbers(str(tmp_path))

        assert any("could not find a `revision` assignment" in error for error in errors)
