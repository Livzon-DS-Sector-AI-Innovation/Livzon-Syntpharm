# 04: API Client Type Safety - Contract Phase

**What to build:** Remove all old `data: any` versions of equipment API functions, so that only type-safe versions remain and the codebase enforces type safety.

**Blocked by:** 02: API Client Type Safety - Migrate Batch 1, 03: API Client Type Safety - Migrate Batch 2

**Status:** ready-for-agent

- [ ] Remove all old `data: any` API function versions from src/lib/api/server/equipment.ts
- [ ] Verify no code still references old versions
- [ ] Ensure TypeScript compilation passes with strict mode
- [ ] All existing tests continue to pass
- [ ] No `data: any` remains in equipment API client
