# ADR-005: Bring the 11 legacy tables onto the shared BaseModel

## Status
Accepted

## Context

`AGENTS.md` requires every business model to inherit `BaseModel` from
`app/shared/base_model.py`. Eleven tables do not. Their models declare a private
declarative base instead:

| File | Base used | Tables |
|---|---|---|
| `quality/qms/static_data/models.py` | its own `class BaseModel(DeclarativeBase)` | 7 |
| `quality/qms/deviation_automation_models.py` | `sqlalchemy.orm.declarative_base()` | 3 |
| `quality/qms/reagent_reminder_config.py` | imports static_data's private base | 1 |

Because those models never register in `Base.metadata`, Alembic's autogenerate
saw eleven tables present in the database with no matching model, treated them as
orphans, and emitted `drop_table` for each. Migration `0033` is exactly that: its
`upgrade()` drops all eleven and creates none. Nothing dropped that did use the
shared base, and `7 + 3 + 1` accounts for every table lost.

The two conventions differ on five things:

| Concept | Shared `BaseModel` | Legacy tables |
|---|---|---|
| Primary key | `id`, UUID | `id` / `task_id`, bigint or integer |
| Author | `created_by`, UUID | `create_by`, integer |
| Timestamps | `created_at` / `updated_at` | `create_time` / `update_time` |
| Soft delete | `is_deleted`, boolean | `del_flag`, integer |
| Deleted meaning | `false` = live | `0` = live, `1` = deleted |

`AGENTS.md:130` independently names `is_deleted` as the soft-delete column, so the
naming breach is a second, separate violation.

At the time of this decision the tables hold no rows and no foreign key anywhere
references them, so the conversion carries no data risk.

## Decision

Inherit the shared `BaseModel` in all four files. The columns come with it:

- `id` becomes UUID; `dev_task.id` is renamed from `task_id`
- `create_by` / `update_by` become `created_by` / `updated_by` as UUID foreign
  keys to `identity.users.id`, populated from the authenticated user
- `create_time` / `update_time` become `created_at` / `updated_at`
- `del_flag` becomes `is_deleted`

Two supporting changes:

1. **`alembic/env.py`** lists the models' metadata registries in
   `target_metadata`, and is deleted once the models inherit the shared base,
   since then one registry suffices.

2. **`scripts/ci/check_migration_scope.py`** is made module-aware. The rule at
   `AGENTS.md:203` is per *module*, but the script compared raw schema strings,
   so it rejected a migration touching `qms` and `quality` - two schemas of the
   *same* module. It now maps each schema to its owning module and judges that.

One migration creates all eleven tables, because `qms` and `quality` belong to
one module and the rule is per module.

## Considered Options

**Keep the legacy columns and inherit anyway.** Rejected: the columns are the
base class. Inheriting while overriding every field is not inheritance.

**Split into two migrations, one per schema.** Rejected by decision: the rule is
"one module per migration", and `qms` and `quality` are one module. Splitting
would satisfy the checker as it stood, which was the wrong reading.

**Keep `create_by` as an integer without a foreign key.** Rejected: the shared
base types the creator as a UUID foreign key, so this leaves the table
non-compliant, and it preserves a placeholder creator (`create_by: 0`) that was
never a real user.

**Parameterise `BaseModel` so it can express both contracts.** Rejected: it is a
change to a base class every other table depends on, to serve eleven tables that
are the exception.

## Consequences

- `create_by: int` disappears from four `*Create` request models. The client must
  stop sending it; the backend takes the creator from the session. Two frontend
  call sites currently send placeholders (`create_by: 0`, `create_by: 1`) and are
  updated.
- `del_flag` is not exposed by any response model and does not appear in
  `openapi.json`, so renaming it to `is_deleted` has no runtime effect. It is
  declared only in the hand-written `frontend/src/types/static-data.ts`, which
  `AGENTS.md:519` already forbids.
- The tables are recreated rather than altered, which is safe only because they
  are empty. On a database that has data this decision would require a backfill
  migration instead.
- Autogenerate can now see all eleven tables, so the orphan-drop that produced
  `0033` cannot recur.
