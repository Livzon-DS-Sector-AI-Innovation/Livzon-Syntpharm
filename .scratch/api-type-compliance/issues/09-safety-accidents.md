# 09 — Safety accidents: response models + frontend types

**What to build:** Frontend can use generated types for accident CRUD, investigation, and resolution APIs. Backend accident endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created: `AccidentApiResponse`, `AccidentListApiResponse`
- [x] All accident endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes accident response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend accident API calls updated to use generated types (replace `safeApiFetch<unknown>` with concrete types)
- [x] TypeScript compilation passes
- [x] Runtime API responses match generated types (spot-check 2-3 accident endpoints)

## Summary

Completed ticket 09 of API type compliance fix:

1. **Backend response wrappers**: Added 2 API response wrapper schemas in `schemas/accidents.py`:
   - `AccidentApiResponse` for single accident responses
   - `AccidentListApiResponse` for accident list responses
   - Made `data` field optional to support delete operations

2. **API endpoint updates**: Updated all 10 accident endpoints to use specific response models instead of generic `ApiResponse`

3. **Bug fixes**: Fixed checks delete endpoint which was trying to validate non-existent `item` variable

4. **OpenAPI spec**: Exported updated spec with accident response schemas

5. **Frontend types**: Regenerated TypeScript types from OpenAPI spec

6. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types for accident endpoints

7. **TypeScript compilation**: Passes with 0 errors

**Commit**: 8f5bc5c6

**Key insight**: Made `data` field optional in response wrapper schemas to support delete operations that return `data=None`. This pattern is consistent with the energy module's approach.
