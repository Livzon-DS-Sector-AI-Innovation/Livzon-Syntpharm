# 05 — Safety checks: response models + frontend types

**What to build:** Frontend can use generated types for safety check CRUD, submit, review APIs. Backend check endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** partial

- [x] Response wrapper schemas created: `SafetyCheckApiResponse`, `SafetyCheckListApiResponse`
- [x] All safety check endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes check response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend safety check API calls updated to use generated types (in `lib/api/server/safety.ts`)
- [ ] TypeScript compilation passes (7 errors remain in actions file)
- [ ] Runtime API responses match generated types (spot-check 2-3 check endpoints)

## Summary

Completed backend and API layer changes for ticket 05:

1. **Backend response wrappers**: Added 2 API response wrapper schemas in `schemas/checks.py`
2. **API endpoint updates**: Updated all 8 safety check endpoints to use specific response models
3. **Removed build_response()**: Endpoints now return response models directly instead of using `build_response()`
4. **OpenAPI spec**: Exported updated spec with safety check response schemas
5. **Frontend types**: Regenerated TypeScript types from OpenAPI spec
6. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types

**Commit**: 0164b12f

## Remaining Work

The actions file (`src/actions/safety/index.ts`) still uses the generic `ApiResponse<T>` type (391 references). This needs to be updated to use the specific response types from the generated schema. This is a larger refactor that should be done in a separate ticket.

**TypeScript errors**: 7 errors remain in the actions file due to type mismatches between `ApiResponse<T>` and the new response types.
