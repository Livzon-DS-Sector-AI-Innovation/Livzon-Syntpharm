# 02: Add authentication headers to frontend API client

**What to build:** All frontend API calls automatically include Authorization header from auth cookie

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Frontend API client reads auth token from cookie
- [x] All API requests include Authorization: Bearer header when token exists
- [x] No changes needed to individual API call sites
- [ ] Tests verify auth headers are included in requests
