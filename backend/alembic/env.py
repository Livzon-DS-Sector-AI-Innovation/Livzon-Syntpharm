import os
from collections.abc import MutableMapping
from importlib import import_module
from logging.config import fileConfig
from typing import Literal

from alembic import context
from app.core.config import get_settings
from app.shared.base_model import Base
from app.shared.module_registry import BUSINESS_MODULES, BUSINESS_SCHEMAS

# Import platform and module models so Alembic can detect them.
import_module("app.platform.audit.models")
import_module("app.platform.identity.models")
import_module("app.core.llm.config")
import_module("app.modules.registration.dossier_writer.models")
import_module("app.modules.quality.ai.models")
import_module("app.modules.quality.ai.config_model")
for module in BUSINESS_MODULES:
import_module("app.modules.production.product.sync_operation_log_model")
    import_module(f"app.modules.{module.code}.models")

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

PROJECT_SCHEMAS = frozenset(("identity", "audit", "core", "permission", "dossier_writer", *BUSINESS_SCHEMAS))

# Get target schema from environment variable (for single-module migration generation)
TARGET_SCHEMA = os.environ.get("ALEMBIC_TARGET_SCHEMA")


def include_object(object, name, type_, reflected, compare_to):
    """Limit autogenerate to specific schema.
    
    If ALEMBIC_TARGET_SCHEMA is set, only include objects in that schema.
    """
    if not TARGET_SCHEMA:
        return True
    
    if type_ == "table":
        return object.schema == TARGET_SCHEMA
    elif type_ in ("column", "index", "unique_constraint"):
        return object.table.schema == TARGET_SCHEMA
    elif type_ == "foreign_key_constraint":
        # For foreign keys, check the parent table's schema
        return object.parent.schema == TARGET_SCHEMA
    
    return True


def include_name(
    name: str | None,
    type_: Literal[
        "schema",
        "table",
        "column",
        "index",
        "unique_constraint",
        "foreign_key_constraint",
    ],
    parent_names: MutableMapping[
        Literal["schema_name", "table_name", "schema_qualified_table_name"],
        str | None,
    ],
) -> bool:
    """Limit autogenerate to schemas owned by this application.
    
    If ALEMBIC_TARGET_SCHEMA is set, only include that specific schema.
    """
    if type_ == "schema":
        if TARGET_SCHEMA:
            return name == TARGET_SCHEMA
        return name in PROJECT_SCHEMAS
    if type_ == "table":
        schema_name = parent_names.get("schema_name")
        if TARGET_SCHEMA:
            return schema_name == TARGET_SCHEMA
        return schema_name in PROJECT_SCHEMAS
    if type_ in ("column", "index", "unique_constraint", "foreign_key_constraint"):
        schema_name = parent_names.get("schema_name")
        if TARGET_SCHEMA:
            return schema_name == TARGET_SCHEMA
        return schema_name in PROJECT_SCHEMAS
    return True


def process_revision_directives(context, revision, directives):
    """Auto-generate CREATE SCHEMA statements for new schemas.

    When autogenerate detects new tables in a schema that doesn't exist yet,
    this hook prepends CREATE SCHEMA IF NOT EXISTS statements to the migration.
    """
    if not directives:
        return

    migration_script = directives[0]
    upgrade_ops = migration_script.upgrade_ops_list

    # Collect all schemas that need to be created
    schemas_to_create = set()

    for op_list in upgrade_ops:
        for op in op_list.ops:
            # Check for create_table operations
            if hasattr(op, "table_name") and hasattr(op, "schema"):
                if op.schema and op.schema not in ("public", "pg_catalog"):
                    schemas_to_create.add(op.schema)

    # If we found new schemas, prepend CREATE SCHEMA statements
    if schemas_to_create:
        from alembic.operations import ops

        create_schema_ops = []

        for schema in sorted(schemas_to_create):
            # Check if CREATE SCHEMA already exists in the migration
            has_create_schema = False
            for op_list in upgrade_ops:
                for op in op_list.ops:
                    if hasattr(op, "sql") and "CREATE SCHEMA" in str(op.sql).upper():
                        if schema in str(op.sql):
                            has_create_schema = True
                            break

            if not has_create_schema:
                # Create a raw SQL operation for CREATE SCHEMA
                sql = f"CREATE SCHEMA IF NOT EXISTS {schema}"
                create_schema_op = ops.ExecuteSQLOp(sql)
                create_schema_ops.append(create_schema_op)

        # Prepend CREATE SCHEMA operations to the first upgrade ops list
        if create_schema_ops and upgrade_ops:
            existing_ops = list(upgrade_ops[0].ops)
            upgrade_ops[0].ops = create_schema_ops + existing_ops


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        process_revision_directives=process_revision_directives,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
        compare_type=True,
        compare_server_default=False,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from urllib.parse import quote_plus, urlparse

    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    # Parse URL to separate host and database
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "")

    # Extract components
    parsed = urlparse(f"postgresql://{db_url}")

    # Extract database name from path
    db_name = parsed.path.lstrip("/") or "postgres"

    # Build connection URL with db name for pg8000
    sync_url = f"postgresql+pg8000://{quote_plus(parsed.username)}:{quote_plus(parsed.password)}@{parsed.hostname}:{parsed.port or 5432}/{db_name}"

    engine = create_engine(
        sync_url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

    with engine.connect() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version (version_num varchar(255) NOT NULL PRIMARY KEY)"
            )
        )
        connection.commit()

        context.configure(
            connection=connection,
            process_revision_directives=process_revision_directives,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            include_object=include_object,
            compare_type=True,
            compare_server_default=False,
        )
        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
