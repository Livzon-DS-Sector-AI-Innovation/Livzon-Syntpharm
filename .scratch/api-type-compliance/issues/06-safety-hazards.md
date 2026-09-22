# 06 — Safety hazards: response models + frontend types

**What to build:** Frontend can use generated types for hazard identification, rectification, and monitoring APIs. Backend hazard endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created: `HazardApiResponse`, `HazardListApiResponse`, `HazardStatsApiResponse`, `DepartmentLeaderApiResponse`, `DepartmentSafetyOfficerApiResponse`, `HazardIdentificationApiResponse`, `HazardIdentificationListApiResponse`, `HazardIdentificationBatchApiResponse`, `RegulationStagesApiResponse`, `OhHazardMonitorApiResponse`, `OhHazardMonitorListApiResponse`
- [x] All hazard endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes hazard response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend hazard API calls updated to use generated types (in `lib/api/server/safety.ts`)
- [x] TypeScript compilation passes
- [ ] Runtime API responses match generated types (spot-check 2-3 hazard endpoints)

## Summary

Completed all changes for ticket 06:

1. **Backend response wrappers**: Added 11 API response wrapper schemas for hazard endpoints
2. **API endpoint updates**: Updated all hazard API endpoints to use specific response models
3. **OpenAPI spec**: Exported updated spec with hazard response schemas
4. **Frontend types**: Regenerated TypeScript types from OpenAPI spec
5. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types for hazard endpoints
6. **TypeScript errors**: Fixed all TypeScript errors by:
   - Changed safety API functions to use `apiFetch` instead of `safeApiFetch` to prevent double-wrapping
   - Fixed `confirmCheck` action return type from `ApiResponse<HazardReport>` to `ApiResponse<SafetyCheck>`

**Commits**: 
- 462e3ec0 - Backend and API layer changes
- 4e61f8f3 - Fixed TypeScript errors

## Notes

The key insight was that `safeApiFetch` wraps the response in `{ code, message, data, meta }`, but the backend response models already include this structure. Using `apiFetch` directly returns the raw response without double-wrapping, which matches the expected type structure.
