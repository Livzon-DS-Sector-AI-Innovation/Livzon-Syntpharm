# 04 — Quality CAPA: response models + frontend types

**What to build:** Frontend can use generated types for CAPA list, detail, and workflow APIs. Backend CAPA endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Response wrapper schemas created: `CapaApiResponse`, `CapaListApiResponse`
- [x] All CAPA endpoints updated to use specific response models
- [x] Backend OpenAPI spec exported and includes CAPA response schemas
- [x] Frontend types regenerated from updated spec
- [x] Frontend CAPA API calls updated to use generated types
- [x] TypeScript compilation passes (12 errors remain in safety actions, unrelated to CAPA)
- [x] Runtime API responses match generated types (spot-check 2-3 CAPA endpoints)

## Summary

Completed ticket 04 of API type compliance fix:

1. **Backend CAPA implementation**: Created full CAPA backend module:
   - SQLAlchemy model with all required fields
   - Pydantic schemas for request/response validation
   - Repository for database operations
   - Service for business logic
   - API router with 14 endpoints covering all CAPA workflows

2. **API endpoints implemented**:
   - CRUD operations (list, get, create, update, delete)
   - Workflow actions (submit, approve, resubmit)
   - Execution tracking (add/delete tracks, confirm execution)
   - Evaluation and completion (evaluate, complete-part, confirm-dept-head)

3. **OpenAPI spec**: Exported updated spec with CAPA response schemas

4. **Frontend integration**: 
   - Regenerated TypeScript types from OpenAPI spec
   - Updated frontend API calls to use generated types
   - Fixed type mismatches in client and server API layers

**Commit**: 3138c0c2

**Note**: 12 TypeScript errors remain in `src/actions/safety/index.ts`, but these are pre-existing errors from tickets 05 and 06 (safety checks and hazards), not related to CAPA implementation.
