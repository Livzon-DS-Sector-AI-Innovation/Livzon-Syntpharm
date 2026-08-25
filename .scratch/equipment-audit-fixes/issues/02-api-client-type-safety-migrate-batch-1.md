# 02: API Client Type Safety - Migrate Batch 1 (Equipment CRUD)

**What to build:** Migrate all equipment CRUD operations (create, update) to use the new typed API functions, so that equipment creation and updates are type-safe.

**Blocked by:** 01: API Client Type Safety - Expand Phase

**Status:** ready-for-agent

- [ ] Update all equipment create/update API calls to use typed versions
- [ ] Update src/actions/equipment.ts to use typed API functions
- [ ] Update all page components that call equipment actions
- [ ] Ensure TypeScript compilation passes
- [ ] All existing tests continue to pass
