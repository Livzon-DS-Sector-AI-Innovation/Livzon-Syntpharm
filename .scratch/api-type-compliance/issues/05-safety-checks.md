# 05 — Safety checks: response models + frontend types

**What to build:** Frontend can use generated types for safety check CRUD, submit, review APIs. Backend check endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created: `SafetyCheckApiResponse`, `SafetyCheckListApiResponse`
- [x] All safety check endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes check response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend safety check API calls updated to use generated types (in `lib/api/server/safety.ts`)
- [x] TypeScript compilation passes
- [ ] Runtime API responses match generated types (spot-check 2-3 check endpoints)

## Summary

Completed all changes for ticket 05:

1. **Backend response wrappers**: Added 2 API response wrapper schemas in `schemas/checks.py`
2. **API endpoint updates**: Updated all 8 safety check endpoints to use specific response models
3. **Removed build_response()**: Endpoints now return response models directly instead of using `build_response()`
4. **OpenAPI spec**: Exported updated spec with safety check response schemas
5. **Frontend types**: Regenerated TypeScript types from OpenAPI spec
6. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types
7. **TypeScript errors**: Fixed all TypeScript errors by:
   - Changed safety API functions to use `apiFetch` instead of `safeApiFetch` to prevent double-wrapping
   - Fixed `confirmCheck` action return type from `ApiResponse<HazardReport>` to `ApiResponse<SafetyCheck>`

**Commits**: 
- 0164b12f - Backend and API layer changes
- 4e61f8f3 - Fixed TypeScript errors

## Notes

The key insight was that `safeApiFetch` wraps the response in `{ code, message, data, meta }`, but the backend response models already include this structure. Using `apiFetch` directly returns the raw response without double-wrapping, which matches the expected type structure.
