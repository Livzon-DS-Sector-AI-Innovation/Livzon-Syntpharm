# 11 — Safety trainings: response models + frontend types

**What to build:** Frontend can use generated types for training CRUD and training record APIs. Backend training endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created: `SafetyTrainingApiResponse`, `SafetyTrainingListApiResponse`, `TrainingRecordApiResponse`, `TrainingRecordListApiResponse`
- [x] All training endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes training response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend training API calls updated to use generated types (replace `safeApiFetch<unknown>` with concrete types)
- [x] TypeScript compilation passes
- [x] Runtime API responses match generated types (spot-check 2-3 training endpoints)

## Summary

Completed ticket 11 of API type compliance fix:

1. **Backend response wrappers**: Added 4 API response wrapper schemas in `schemas/trainings.py`:
   - `SafetyTrainingApiResponse` for single training responses
   - `SafetyTrainingListApiResponse` for training list responses
   - `TrainingRecordApiResponse` for single training record responses
   - `TrainingRecordListApiResponse` for training record list responses
   - Made `data` field optional to support delete operations

2. **API endpoint updates**: Updated all 13 training endpoints to use specific response models instead of generic `ApiResponse`

3. **OpenAPI spec**: Exported updated spec with training response schemas

4. **Frontend types**: Regenerated TypeScript types from OpenAPI spec

5. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types for training endpoints

6. **TypeScript compilation**: Passes with 0 errors

**Commit**: 7696cb69

**Key insight**: Made `data` field optional in response wrapper schemas to support delete operations that return `data=None`. This pattern is consistent with the energy module's approach and provides better type safety.
