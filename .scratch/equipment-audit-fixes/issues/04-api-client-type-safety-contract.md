# 04: API Client Type Safety - Contract Phase

**What to build:** Remove all old `data: any` versions of equipment API functions, so that only type-safe versions remain and the codebase enforces type safety.

**Blocked by:** 02: API Client Type Safety - Migrate Batch 1, 03: API Client Type Safety - Migrate Batch 2

**Status:** completed

- [x] Remove all old `data: any` API function versions from src/lib/api/server/equipment.ts
- [x] Verify no code still references old versions
- [x] Ensure TypeScript compilation passes with strict mode
- [x] All existing tests continue to pass
- [x] No `data: any` remains in equipment API client (except for 3 special cases: previewEquipmentImportApiTyped, batchImportEquipmentApiTyped, claimWorkOrderDataApiTyped which use any[] or any for backend compatibility)
