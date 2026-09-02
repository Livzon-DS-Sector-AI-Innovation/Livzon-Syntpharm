# 02 — Rename energy product conversion migration

**What to build:** Rename the energy product conversion migration from hash-prefixed naming to sequential NNNN naming while preserving the migration logic and maintaining the dependency chain.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Determine correct sequential number (check existing migrations)
- [ ] Rename file from `29a5a96069e8_add_energy_product_conversion_table.py` to `NNNN_add_energy_product_conversion_table.py`
- [ ] Update `revision` variable inside the file to match new filename
- [ ] Update `down_revision` references in any child migrations
- [ ] Verify migration chain is valid with `alembic heads`
- [ ] Verify migration can be applied with `alembic upgrade head` (on test DB)
