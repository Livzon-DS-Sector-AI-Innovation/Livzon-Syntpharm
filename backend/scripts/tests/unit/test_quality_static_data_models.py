"""Registration tests for the eleven quality legacy tables.

These tables were dropped by migration 0033 because their models declared private
declarative bases and never reached the shared `Base.metadata`. Autogenerate then
saw the live tables as orphans with no matching model.

These tests assert the consequence of inheriting the shared `BaseModel`: every
table is registered in the shared metadata, carries a UUID primary key and the
five shared audit columns. They need no database — registration only requires the
model modules to be imported.
"""

from __future__ import annotations

import uuid

import pytest

# Importing the quality module's model aggregator registers every model below.
import app.modules.quality.models  # noqa: F401
from app.shared.base_model import Base

# (schema-qualified table name, legacy primary-key column)
LEGACY_TABLES = [
    ("qms.t_qs_storage_condition", "id"),
    ("qms.t_qs_unit", "id"),
    ("qms.t_qs_hplc_reference", "id"),
    ("qms.t_qs_hplc_reference_usage", "id"),
    ("qms.t_qs_chrom_column", "id"),
    ("qms.t_qs_standard", "id"),
    ("qms.t_qs_medium", "id"),
    ("qms.qms_reagent_reminder_config", "id"),
    ("quality.dev_task", "task_id"),
    ("quality.report_template", "id"),
    ("quality.sop_rule", "id"),
]

SHARED_COLUMNS = ["id", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]

# Legacy columns that the shared contract replaces.
FORBIDDEN_COLUMNS = ["create_by", "create_time", "update_by", "update_time", "del_flag", "task_id"]


@pytest.mark.parametrize(("qualified_name", "legacy_pk"), LEGACY_TABLES)
def test_table_registered_with_uuid_primary_key(qualified_name: str, legacy_pk: str) -> None:
    """Each table is in Base.metadata, keyed on a UUID `id`."""
    table = Base.metadata.tables.get(qualified_name)
    assert table is not None, f"{qualified_name} is not registered in Base.metadata"

    pk_columns = list(table.primary_key.columns)
    assert [c.name for c in pk_columns] == ["id"], f"{qualified_name} primary key is {[c.name for c in pk_columns]}"

    id_column = table.columns["id"]
    assert id_column.type.as_generic().python_type is uuid.UUID, f"{qualified_name}.id is not a UUID"


@pytest.mark.parametrize(("qualified_name", "_legacy_pk"), LEGACY_TABLES)
def test_table_has_shared_base_model_columns(qualified_name: str, _legacy_pk: str) -> None:
    """Each table carries the five shared contract columns."""
    table = Base.metadata.tables[qualified_name]
    columns = {column.name for column in table.columns}

    missing = [name for name in SHARED_COLUMNS if name not in columns]
    assert not missing, f"{qualified_name} is missing shared columns: {missing}"


@pytest.mark.parametrize(("qualified_name", "_legacy_pk"), LEGACY_TABLES)
def test_table_has_no_legacy_columns(qualified_name: str, _legacy_pk: str) -> None:
    """The legacy audit and soft-delete columns are gone."""
    table = Base.metadata.tables[qualified_name]
    columns = {column.name for column in table.columns}

    leftover = [name for name in FORBIDDEN_COLUMNS if name in columns]
    assert not leftover, f"{qualified_name} still declares legacy columns: {leftover}"


@pytest.mark.parametrize(("qualified_name", "_legacy_pk"), LEGACY_TABLES)
def test_table_is_in_the_expected_schema(qualified_name: str, _legacy_pk: str) -> None:
    """Each table lives in the schema named in the parameter."""
    table = Base.metadata.tables[qualified_name]
    expected_schema = qualified_name.split(".")[0]
    assert table.schema == expected_schema, f"{qualified_name} is in schema {table.schema}"
