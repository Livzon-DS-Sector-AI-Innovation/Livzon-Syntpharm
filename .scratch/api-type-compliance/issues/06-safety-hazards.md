# 06 — Safety hazards: response models + frontend types

**What to build:** Frontend can use generated types for hazard identification, rectification, and monitoring APIs. Backend hazard endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** partial

- [x] Response wrapper schemas created: `HazardApiResponse`, `HazardListApiResponse`, `HazardStatsApiResponse`, `DepartmentLeaderApiResponse`, `DepartmentSafetyOfficerApiResponse`, `HazardIdentificationApiResponse`, `HazardIdentificationListApiResponse`, `HazardIdentificationBatchApiResponse`, `RegulationStagesApiResponse`, `OhHazardMonitorApiResponse`, `OhHazardMonitorListApiResponse`
- [x] All hazard endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes hazard response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend hazard API calls updated to use generated types (in `lib/api/server/safety.ts`)
- [ ] TypeScript compilation passes (12 errors remain in actions file)
- [ ] Runtime API responses match generated types (spot-check 2-3 hazard endpoints)

## Summary

Completed backend and API layer changes for ticket 06:

1. **Backend response wrappers**: Added 11 API response wrapper schemas for hazard endpoints
2. **API endpoint updates**: Updated all hazard API endpoints to use specific response models
3. **OpenAPI spec**: Exported updated spec with hazard response schemas
4. **Frontend types**: Regenerated TypeScript types from OpenAPI spec
5. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types for hazard endpoints

**Commit**: 462e3ec0

## Remaining Work

The actions file (`src/actions/safety/index.ts`) still uses the generic `ApiResponse<T>` type (391 references). This needs to be updated to use the specific response types from the generated schema. This is a larger refactor that should be done in a separate ticket.

**TypeScript errors**: 12 errors remain in the actions file due to type mismatches between `ApiResponse<T>` and the new response types.
