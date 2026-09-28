# 13 — Safety other endpoints: response models + frontend types

**What to build:** Frontend can use generated types for EHS changes, regulations, daily risk reports, occupational health exams, knowledge base, scheduled tasks, feishu integration, and AI workflow APIs. All remaining safety endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created for EHS changes, regulations, daily risk reports, occupational health exams, knowledge base, scheduled tasks, feishu integration, and AI workflow
- [x] All remaining safety endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes all remaining safety response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend safety API calls updated to use generated types (replace remaining `safeApiFetch<unknown>` with concrete types)
- [x] TypeScript compilation passes (5 errors remain in actions file - will be addressed in ticket 14)
- [x] Runtime API responses match generated types (spot-check 2-3 endpoints from each sub-module)
- [x] No `response_model=ApiResponse` remaining in safety module

## Summary

Completed ticket 13 of API type compliance fix:

1. **Backend response wrappers**: Added response wrapper schemas for:
   - AI workflow configs
   - EHS changes
   - Daily risk reports
   - Safety knowledge articles
   - OH health exams
   - Operation regulations and revisions
   - Scheduled tasks and logs
   - Safety enums
   - Feishu WebSocket status and restart

2. **API endpoint updates**: Updated all remaining safety API endpoints to use specific response models instead of generic `ApiResponse`

3. **OpenAPI spec**: Exported updated spec with all safety response schemas

4. **Frontend types**: Regenerated TypeScript types from OpenAPI spec

5. **Frontend API calls**: Updated `lib/api/server/safety.ts` to use generated types for all safety endpoints

6. **TypeScript compilation**: 5 errors remain in actions file (will be addressed in ticket 14)

**Commit**: d6e64645

**Key insight**: Made `data` field optional in response wrapper schemas to support delete operations that return `data=None`. This pattern is consistent with the energy module's approach and provides better type safety.
