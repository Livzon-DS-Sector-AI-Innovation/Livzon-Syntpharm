# 45.10 — Verify exhaustive-deps fixes and document remaining warnings

**What to build:** Verify that the exhaustive-deps fixes from tickets 45.1-45.9 are working, and document the remaining warnings that will be addressed in ticket 46.

**Blocked by:** 45.1, 45.2, 45.3, 45.4, 45.5, 45.6, 45.7, 45.8, 45.9

**Status:** done

- [x] Fixed exhaustive-deps warnings in equipment, hr, quality-core, quality-components, research-core, research-workflow, safety, registration-procurement, and remaining modules
- [x] `tsc --noEmit` passes with 0 errors
- [x] All sub-tickets 45.1-45.9 marked as done
- [x] Documented remaining 31 exhaustive-deps warnings for ticket 46

**Notes:**
- 31 exhaustive-deps warnings remain across 23 files
- These are in: quality deviation (4 files), quality instrument (1 file), registration ledger (1 file), energy DeviceDrawer (1 file), hr training (2 files), production (3 files), research (1 file), safety hazard (3 files), safety special ops (2 files), safety workflow/regulation (5 files)
- Common patterns: missing useCallback wrappers, missing dependencies in useEffect/useCallback arrays
- These warnings don't cause runtime errors but should be fixed for code quality
- Ticket 46 will address these remaining warnings
