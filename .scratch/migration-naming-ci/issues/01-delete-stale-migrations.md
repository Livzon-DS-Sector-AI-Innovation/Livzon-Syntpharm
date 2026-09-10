# 01 — Delete stale hash-prefixed migrations

**What to build:** Remove 7 obsolete migration files with hash prefixes that are duplicates of correctly-named versions, leaving a clean migration history that follows the NNNN naming convention.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Delete `1f550ec06f66_0038_add_product_sync_config.py`
- [ ] Delete `2eb6d687679e_0042_add_chapter_asset_usages.py`
- [ ] Delete `49684887bf7e_0045_energy_add_workshop_and_steam.py`
- [ ] Delete `6379b65e0052_0041_equipment_add_fields.py`
- [ ] Delete `74a464371488_0044_rename_equipment_no_to_asset_no.py`
- [ ] Delete `fcb768b8df78_0043_fix_production_index_names.py`
- [ ] Delete `d89b9d01b93a_merge_migration_heads.py`
- [ ] Verify no references to deleted files remain in codebase
- [ ] Verify migration chain is still valid with `alembic heads`
