# 01: Add authentication to all equipment API endpoints

**What to build:** All equipment API endpoints (except GET /template) require authentication, returning 401 for unauthenticated requests

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] All equipment API endpoints require authentication except GET /template
- [x] Unauthenticated requests return 401 status code
- [x] Authentication uses existing CurrentUser dependency injection pattern
- [ ] Integration tests verify 401 responses for unauthenticated requests
- [x] No breaking changes to authenticated request handling
