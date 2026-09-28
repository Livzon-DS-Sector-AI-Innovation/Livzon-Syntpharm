# 10 — Safety contractors: response models + frontend types

**What to build:** Frontend can use generated types for contractor CRUD, work records, and training APIs. Backend contractor endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created: `ContractorApiResponse`, `ContractorListApiResponse`, `ContractorWorkRecordApiResponse`, `ContractorWorkRecordListApiResponse`
- [x] All contractor endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes contractor response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend contractor API calls updated to use generated types (replace `safeApiFetch<unknown>` with concrete types)
- [x] TypeScript compilation passes
- [x] Runtime API responses match generated types (spot-check 2-3 contractor endpoints)

## Summary

Completed ticket 10 of API type compliance fix:

1. **Backend response wrappers**: Added 4 API response wrapper schemas in `schemas/contractors.py`:
   - `ContractorApiResponse` for single contractor responses
   - `ContractorListApiResponse` for contractor list responses
   - `ContractorWorkRecordApiResponse` for single work record responses
   - `ContractorWorkRecordListApiResponse` for work record list responses
   - Made `data` field optional to support delete operations

2. **API endpoint updates**: Updated all 13 contractor endpoints to use specific response models instead of generic `ApiResponse`

3. **OpenAPI spec**: Exported updated spec with contractor response schemas

4. **Frontend types**: Regenerated TypeScript types from OpenAPI spec

5. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types for contractor endpoints

6. **TypeScript compilation**: Passes with 0 errors

**Commit**: 1b357620

**Key insight**: Made `data` field optional in response wrapper schemas to support delete operations that return `data=None`. This pattern is consistent with the energy module's approach and provides better type safety.
