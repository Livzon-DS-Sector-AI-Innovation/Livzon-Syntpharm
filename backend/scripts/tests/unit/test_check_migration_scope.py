"""Tests for migration naming convention and single-module scope validation."""

from pathlib import Path

from scripts.ci.check_migration_scope import (
    build_schema_module_map,
    extract_schemas_from_migration,
    validate_migration_scope,
    validate_naming_convention,
)


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


class TestModuleScope:
    """The single-module rule is judged per *module*, not per raw schema name.

    `qms` and `quality` are two schemas owned by the one `quality` module, so a
    migration touching both is compliant; `hr` and `safety` are two modules, so
    touching both is not.
    """

    def _build_modules_tree(self, root: Path) -> dict[str, str]:
        """Create a minimal modules tree and derive the schema -> module map."""
        (root / "quality" / "qms").mkdir(parents=True)
        (root / "quality" / "qms" / "models.py").write_text("")
        (root / "quality" / "models.py").write_text("")
        (root / "hr").mkdir(parents=True)
        (root / "hr" / "models.py").write_text("")
        (root / "safety").mkdir(parents=True)
        (root / "safety" / "models.py").write_text("")
        return build_schema_module_map(root)

    def test_module_map_is_derived_from_filesystem(self, tmp_path: Path) -> None:
        """A nested model-bearing package maps to its enclosing module."""
        mapping = self._build_modules_tree(tmp_path)

        assert mapping["qms"] == "quality"
        assert mapping["quality"] == "quality"
        assert mapping["hr"] == "hr"
        assert mapping["safety"] == "safety"

    def test_same_module_two_schemas_passes(self, tmp_path: Path) -> None:
        """qms + quality belong to one module, so the scope is valid."""
        mapping = self._build_modules_tree(tmp_path)

        is_valid, modules = validate_migration_scope({"qms", "quality"}, mapping)

        assert is_valid is True
        assert modules == {"quality"}

    def test_cross_module_two_schemas_fails(self, tmp_path: Path) -> None:
        """hr + safety are two modules, so the scope is invalid."""
        mapping = self._build_modules_tree(tmp_path)

        is_valid, modules = validate_migration_scope({"hr", "safety"}, mapping)

        assert is_valid is False
        assert modules == {"hr", "safety"}

    def test_single_module_passes(self, tmp_path: Path) -> None:
        """One module is always valid, however many of its schemas are touched."""
        mapping = self._build_modules_tree(tmp_path)

        is_valid, modules = validate_migration_scope({"qms"}, mapping)

        assert is_valid is True
        assert modules == {"quality"}

    def test_unknown_schemas_fall_back_to_their_own_name(self, tmp_path: Path) -> None:
        """Two unknown schemas are treated as two modules, so cross-module edits still fail."""
        mapping = self._build_modules_tree(tmp_path)

        is_valid, modules = validate_migration_scope({"unknown_a", "unknown_b"}, mapping)

        assert is_valid is False
        assert modules == {"unknown_a", "unknown_b"}

    def test_extract_and_judge_same_module_migration(self, tmp_path: Path) -> None:
        """End to end: schema extraction feeds the module-scope judgement."""
        mapping = self._build_modules_tree(tmp_path)
        migration = tmp_path / "0067_recreate_quality_legacy_tables.py"
        migration.write_text(
            "revision: str = '0067_recreate_quality_legacy_tables'\n"
            "op.execute('CREATE SCHEMA IF NOT EXISTS qms')\n"
            "op.create_table('dev_task', schema='quality')\n"
            "op.create_table('t_qs_unit', schema='qms')\n"
        )

        schemas = extract_schemas_from_migration(str(migration))
        is_valid, modules = validate_migration_scope(schemas, mapping)

        assert schemas == {"qms", "quality"}
        assert is_valid is True
        assert modules == {"quality"}

    def test_extract_and_judge_cross_module_migration(self, tmp_path: Path) -> None:
        """End to end: a genuinely cross-module migration is rejected."""
        mapping = self._build_modules_tree(tmp_path)
        migration = tmp_path / "9999_bad_scope.py"
        migration.write_text(
            "revision: str = '9999_bad_scope'\n"
            "op.create_table('hazards', schema='safety')\n"
            "op.create_table('employees', schema='hr')\n"
        )

        schemas = extract_schemas_from_migration(str(migration))
        is_valid, modules = validate_migration_scope(schemas, mapping)

        assert is_valid is False
        assert modules == {"hr", "safety"}

    def test_real_repo_maps_qms_to_quality(self) -> None:
        """The real repository tree maps qms and quality to the quality module."""
        mapping = build_schema_module_map()

        assert mapping.get("qms") == "quality"
        assert mapping.get("quality") == "quality"

        is_valid, _ = validate_migration_scope({"qms", "quality"}, mapping)
        assert is_valid is True
