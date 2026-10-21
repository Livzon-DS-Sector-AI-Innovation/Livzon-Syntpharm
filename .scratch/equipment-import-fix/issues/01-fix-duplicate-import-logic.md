# 01 — Fix batch import duplicate handling (Update instead of Skip)

**What to build:** the end-to-end behaviour this ticket makes work, from the user's perspective — not a layer-by-layer implementation list.
As an equipment administrator, I want the batch import process to update existing records when asset numbers match, so that I can synchronize the latest department and location information from Excel without losing data due to "duplicate" skips.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [x] Modify `batch_import.py` to call `update_equipment` when `asset_no` already exists.
- [x] Update `equipment-import-v3-spec-final.md` with the new implementation decision.
- [ ] Add integration test in `test_batch_import.py` to verify update logic for duplicates.
- [ ] Verify that the "18 missing records" issue is resolved in the next full import run.
