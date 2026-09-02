# 03 — Regenerate merge migration with proper naming

**What to build:** Create a new merge migration that reconciles the migration heads using proper NNNN naming convention, replacing the deleted hash-prefixed merge migration.

**Blocked by:** 01 (Delete stale hash-prefixed migrations), 02 (Rename energy product conversion migration)

**Status:** ready-for-agent

- [ ] Run `alembic merge heads -m "NNNN_merge_migration_heads"` with next available number
- [ ] Verify generated file has filename matching `NNNN_merge_migration_heads.py`
- [ ] Verify revision ID inside file matches filename
- [ ] Verify `down_revision` is a tuple of the two heads being merged
- [ ] Verify `upgrade()` and `downgrade()` functions are empty (no-op)
- [ ] Verify `alembic heads` shows a single head
- [ ] Verify migration can be applied with `alembic upgrade head`
