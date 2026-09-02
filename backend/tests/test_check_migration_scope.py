"""Tests for migration naming convention validation."""

from pathlib import Path

from scripts.ci.check_migration_scope import validate_naming_convention


class TestNamingValidation:
    """Test the validate_naming_convention function."""

    def test_valid_naming_simple(self, tmp_path: Path) -> None:
        """Test valid NNNN_descriptive_name pattern."""
        migration = tmp_path / "0001_baseline.py"
        migration.write_text("revision: str = '0001_baseline'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is True
        assert errors == []

    def test_valid_naming_with_numbers(self, tmp_path: Path) -> None:
        """Test valid pattern with numbers in descriptive name."""
        migration = tmp_path / "0055_add_sync_operation_log.py"
        migration.write_text("revision: str = '0055_add_sync_operation_log'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is True
        assert errors == []

    def test_valid_naming_uppercase(self, tmp_path: Path) -> None:
        """Test valid pattern with uppercase letters."""
        migration = tmp_path / "0001_Baseline.py"
        migration.write_text("revision: str = '0001_Baseline'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is True
        assert errors == []

    def test_valid_naming_multiple_underscores(self, tmp_path: Path) -> None:
        """Test valid pattern with multiple underscores."""
        migration = tmp_path / "0001_baseline_full_schema.py"
        migration.write_text("revision: str = '0001_baseline_full_schema'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is True
        assert errors == []

    def test_invalid_filename_hash(self, tmp_path: Path) -> None:
        """Test invalid hash-based filename."""
        migration = tmp_path / "3cb28d1e1ac7_add_foo.py"
        migration.write_text("revision: str = '3cb28d1e1ac7'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is False
        assert len(errors) == 2  # filename + revision ID both invalid
        assert "Filename: 3cb28d1e1ac7_add_foo" in errors[0]

    def test_invalid_revision_hash(self, tmp_path: Path) -> None:
        """Test invalid hash-based revision ID."""
        migration = tmp_path / "0001_add_foo.py"
        migration.write_text("revision: str = 'd89b9d01b93a'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is False
        assert len(errors) == 1  # only revision ID invalid
        assert "Revision ID: d89b9d01b93a" in errors[0]

    def test_invalid_filename_no_digits(self, tmp_path: Path) -> None:
        """Test invalid filename without leading digits."""
        migration = tmp_path / "abc123_test.py"
        migration.write_text("revision: str = 'abc123_test'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is False
        assert "Filename: abc123_test" in errors[0]

    def test_invalid_revision_no_digits(self, tmp_path: Path) -> None:
        """Test invalid revision ID without leading digits."""
        migration = tmp_path / "0001_test.py"
        migration.write_text("revision: str = 'def456'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is False
        assert "Revision ID: def456" in errors[0]

    def test_missing_revision_id(self, tmp_path: Path) -> None:
        """Test migration file without revision ID."""
        migration = tmp_path / "0001_test.py"
        migration.write_text("# no revision here\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is False
        assert "Could not find revision ID" in errors[0]

    def test_revision_without_type_annotation(self, tmp_path: Path) -> None:
        """Test revision ID without type annotation (older Alembic format)."""
        migration = tmp_path / "0001_test.py"
        migration.write_text("revision = '0001_test'\n")

        is_valid, errors = validate_naming_convention(str(migration))

        assert is_valid is True
        assert errors == []
