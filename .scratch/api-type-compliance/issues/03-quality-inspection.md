# 03 — Quality inspection: response models + frontend types

**What to build:** Frontend can use generated types for inspection standard CRUD, approval, and query APIs. Backend inspection endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created: `InspectionStandardApiResponse`, `InspectionStandardListApiResponse`, `ApprovalRecordApiResponse`, `ApprovalRecordListApiResponse`
- [x] All inspection standard endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes inspection response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend inspection API calls updated to use generated types
- [x] TypeScript compilation passes
- [x] Runtime API responses match generated types (spot-check 2-3 inspection endpoints)

## Summary

Completed ticket 03 of API type compliance fix:

1. **Backend response wrappers**: Added 6 API response wrapper schemas in `schemas.py` for inspection standards and approval records
2. **API endpoint updates**: Updated all 13 inspection API endpoints to use specific response models instead of generic `ApiResponse`
3. **OpenAPI spec**: Exported updated spec with inspection response schemas
4. **Frontend types**: Regenerated TypeScript types from OpenAPI spec
5. **Verification**: TypeScript compilation passes with no errors

**Commit**: b30f59f1

**Note**: The frontend can now use generated types for inspection standard APIs. The response models include proper type information for standards, items, and approval records.
