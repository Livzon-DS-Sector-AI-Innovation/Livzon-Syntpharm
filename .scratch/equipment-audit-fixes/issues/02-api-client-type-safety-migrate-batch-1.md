# 02: API Client Type Safety - Migrate Batch 1 (Equipment CRUD)

**What to build:** Migrate all equipment CRUD operations (create, update) to use the new typed API functions, so that equipment creation and updates are type-safe.

**Blocked by:** 01: API Client Type Safety - Expand Phase

**Status:** completed

- [x] Update all equipment create/update API calls to use typed versions
- [x] Update src/actions/equipment.ts to use typed API functions
- [x] Update all page components that call equipment actions
- [x] Ensure TypeScript compilation passes
- [x] All existing tests continue to pass
