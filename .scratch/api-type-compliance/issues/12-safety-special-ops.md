# 12 — Safety special operations: response models + frontend types

**What to build:** Frontend can use generated types for special operation permits, personnel, and reports APIs. Backend special operation endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created: `SpecialOperationPermitApiResponse`, `SpecialOperationPermitListApiResponse`, `SpecialOperationPersonnelApiResponse`, `SpecialOperationPersonnelListApiResponse`, `SpecialOperationReportApiResponse`, `SpecialOperationReportListApiResponse`, `SpecialOperationLedgerStatsApiResponse`
- [x] All special operation endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes special operation response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend special operation API calls updated to use generated types (replace `safeApiFetch<unknown>` with concrete types)
- [x] TypeScript compilation passes
- [x] Runtime API responses match generated types (spot-check 2-3 special operation endpoints)

## Summary

Completed ticket 12 of API type compliance fix:

1. **Backend response wrappers**: Added 7 API response wrapper schemas:
   - `SpecialOperationPermitApiResponse` for single permit responses
   - `SpecialOperationPermitListApiResponse` for permit list responses
   - `SpecialOperationPersonnelApiResponse` for single personnel responses
   - `SpecialOperationPersonnelListApiResponse` for personnel list responses
   - `SpecialOperationReportApiResponse` for single report responses
   - `SpecialOperationReportListApiResponse` for report list responses
   - `SpecialOperationLedgerStatsApiResponse` for ledger stats responses
   - Made `data` field optional to support delete operations

2. **API endpoint updates**: Updated all special operation endpoints to use specific response models instead of generic `ApiResponse`

3. **OpenAPI spec**: Exported updated spec with special operation response schemas

4. **Frontend types**: Regenerated TypeScript types from OpenAPI spec

5. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types for special operation endpoints

6. **TypeScript compilation**: Passes with 0 errors

**Commit**: 69ade01e

**Key insight**: Made `data` field optional in response wrapper schemas to support delete operations that return `data=None`. This pattern is consistent with the energy module's approach and provides better type safety.
