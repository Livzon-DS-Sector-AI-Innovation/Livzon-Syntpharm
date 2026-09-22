# 02 — Quality deviation: response models + frontend types

**What to build:** Frontend can use generated types for deviation list, detail, statistics, and AI analysis APIs. Backend deviation endpoints switch from generic `ApiResponse` to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created in `deviation_schemas.py`: `DeviationApiResponse`, `DeviationListApiResponse`, `DeviationStatisticsApiResponse`, `InvestigationApiResponse`, `InvestigationListApiResponse`, `CorrectionApiResponse`, `ClosingApiResponse`, `AIAnalysisApiResponse`
- [x] All deviation endpoints in `deviation_api.py` updated to use specific response models instead of generic `ApiResponse`
- [x] Backend OpenAPI spec exported and includes deviation response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend deviation API calls updated to use generated types
- [x] TypeScript compilation passes
- [x] Runtime API responses match generated types (spot-check 2-3 deviation endpoints)

## Summary

Completed ticket 02 of API type compliance fix:

1. **Backend response wrappers**: Added 8 API response wrapper schemas in `deviation_schemas.py`
2. **API endpoint updates**: Updated all 28 deviation endpoints to use specific response models
3. **OpenAPI spec**: Exported updated spec with deviation response schemas (DeviationApiResponse, DeviationListApiResponse, DeviationStatisticsApiResponse, etc.)
4. **Frontend types**: Regenerated TypeScript types from OpenAPI spec
5. **Verification**: TypeScript compilation passes with no errors

**Commit**: 67a1bc5f

**Note**: The return statements in the API endpoints still use `ApiResponse(data=...)` pattern, but FastAPI validates and serializes responses based on the `response_model` decorator, so the OpenAPI spec correctly reflects the response types. The frontend can now use the generated types for type safety.
